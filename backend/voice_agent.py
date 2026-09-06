# ENGINE: IntelligenceEngine + CoreOrchestrator
"""
PRISM Voice Agent — Intelligence Engine Core

The live conversation brain for PRISM. Processes each user turn through:

    User turn
        → LLM (with tools) — proposes action + language
        → DETERMINISTIC POLICY GATE (policy.py) — approves / rejects / modifies
        → Tool execution (tools.py)
        → Verification
        → Response

This module is the IntelligenceEngine in PRISM's canonical 7-engine architecture.
The LLM handles language and action proposals. The policy engine handles decisions.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List

from context import get_or_create_case, CaseState, escalated_cases
from tools import check_transaction as db_check_transaction, create_escalation_ticket
from llm_service import prism_llm_call
from policy import evaluate_escalation, PolicyDecision

# ═══════════════════════════════════════════════════════════════════════════
# PRISM CANONICAL ARCHITECTURE — 7 Engines
# ═══════════════════════════════════════════════════════════════════════════
#
#  ┌─────────────────┐
#  │   PRISM CORE    │  ← CoreOrchestrator (this module + main.py)
#  └────────┬────────┘
#           │
#  ┌────────┼────────────────────────────────────────┐
#  ▼        ▼                                         ▼
#
# VOICE ENGINE          INTELLIGENCE ENGINE       ACTION ENGINE
# vad_service.py        voice_agent.py           tools.py
# asr_service.py        context.py               tool_registry.py (→ ticket 13)
# audio_pipeline.py     intent_engine.py (→13)   adapters/ (→ ticket 54)
# (→ ticket 4)          missing_info.py (→11)
#                       planning.py (→12)
#
#           │
#           ▼
#
# POLICY ENGINE          HUMAN SUPPORT ENGINE    PLATFORM ENGINE
# policy.py              main.py /cases          main.py /auth
# decision.py            context.py escalations  database (→ ticket 30)
# confidence.py                                  audit_log (→ ticket 32)
#
# ═══════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

PRISM_VOICE_ASSISTANT_SYSTEM_PROMPT = """You are PRISM, an ultra-fluid, empathetic human-like voice assistant (like Siri or Alexa) for customer support, payments, and order issues.

CONVERSATIONAL RULES (ACT LIKE A WARM, HELPFUL HUMAN ASSISTANT):
1. GREETINGS & SMALL TALK:
   - If the user says "hi", "hello", or greets you: Reply warmly like a real assistant (e.g. "Hello! How can I help you today?").
   - If the user asks "how are you?": Reply naturally (e.g. "I'm doing great, thank you! How can I assist you today?").
   - Match the user's energy, tone, and language (English, Hindi, Hinglish).

2. HANDLING PAYMENT & ISSUES:
   - If the user says "payment has been deducted" or mentions a problem: Acknowledge with empathy first (e.g. "I understand your payment was deducted. I will definitely help you resolve this! Could you please tell me your Transaction ID or order number?").
   - If the user gives a Transaction ID (e.g. TX48291, TX00001): Call `check_transaction` immediately to look up details.
   - If payment was deducted but the order was not confirmed, or anything looks unsafe to resolve alone: propose `escalate_to_human`. A deterministic policy will validate the proposal and confirm the handoff.

3. CONCISE & HUMAN VOICE:
   - Speak naturally in short, friendly sentences (1 to 3 sentences max).
   - Never sound robotic, technical, or scripted.
   - Never invent transaction details or make up numbers.
"""


def get_tool_schemas(case: CaseState) -> List[Dict[str, Any]]:
    """Return OpenAI-format tool definitions available to the agent."""
    try:
        from tool_registry import registry
        return registry.get_schemas(case)
    except Exception:
        # Fallback to hardcoded schemas if registry unavailable
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_transaction",
                    "description": "Look up a payment transaction by its ID (e.g. TX48291). Returns payment status, order status, amount, and timestamp.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "transaction_id": {
                                "type": "string",
                                "description": "The transaction ID, e.g. TX48291"
                            }
                        },
                        "required": ["transaction_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "escalate_to_human",
                    "description": "Propose escalating the case to a human support specialist when there is an unconfirmed payment, duplicate charge concern, tool failure, or when the customer requests it. A deterministic policy validates every proposal before the handoff actually happens.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Detailed reason for escalating to a human specialist."
                            }
                        },
                        "required": ["reason"]
                    }
                }
            }
        ]


def execute_tool(name: str, args: dict, case: CaseState) -> dict:
    """Execute a tool and update PRISM case state.

    Note: `escalate_to_human` does NOT finalize an escalation here — it only
    records the proposal. The deterministic policy gate (applied after the turn's
    tool calls) decides whether the escalation actually happens.
    """
    if name == "check_transaction":
        tx_id = args.get("transaction_id", "").strip().upper()
        case.transaction_id = tx_id
        if "transaction_id" not in case.verified:
            case.verified.append("transaction_id")

        result = db_check_transaction(tx_id)
        if result.get("success"):
            case.payment_status = result.get("status")
            case.order_status = result.get("order_status")
            case.amount = float(result.get("amount", 0))
            for f in ["payment_status", "order_status", "amount", "transaction_id"]:
                if f not in case.verified:
                    case.verified.append(f)

            # Derive the duplicate-charge posture from the verified facts so the
            # deterministic engine can distinguish a clean transaction from the
            # ambiguous "money taken, order not confirmed" case:
            #   SUCCESS + CONFIRMED  -> no duplicate risk (resolvable)
            #   FAILED               -> no duplicate risk (resolvable)
            #   SUCCESS + NOT_CONFIRMED (or unclear) -> genuinely UNKNOWN -> escalate
            status = result.get("status")
            order = result.get("order_status")
            if status == "SUCCESS" and order == "CONFIRMED":
                case.duplicate_charge = "NO"
            elif status == "FAILED":
                case.duplicate_charge = "NO"
            if case.duplicate_charge != "UNKNOWN" and "duplicate_charge" not in case.verified:
                case.verified.append("duplicate_charge")

            case.unverified = [x for x in case.unverified if x not in case.verified]
            logger.info(f"[PRISM Agent] check_transaction verified: {tx_id} -> {status}/{order}")
        else:
            case.tool_failed = True
            logger.warning(f"[PRISM Agent] check_transaction failed for {tx_id}")
        return result

    elif name == "escalate_to_human":
        reason = args.get("reason", "Customer issue requires specialist review")
        case.escalation_proposed = True
        case.proposed_escalation_reason = reason
        logger.info(f"[PRISM Agent] escalate_to_human PROPOSED by LLM: {reason} (pending policy validation)")
        return {"status": "PENDING_POLICY_VALIDATION", "reason": reason}

    return {"error": f"Unknown tool: {name}"}


def _apply_policy(case: CaseState, policy: PolicyDecision) -> None:
    """Record the policy decision on the case and finalize escalation if approved."""
    case.policy_decision = policy.decision
    case.policy_reason = policy.reason

    if policy.approved and not case.escalated:
        reason = case.proposed_escalation_reason or policy.reason
        case.escalated = True
        case.escalation_reason = reason
        summary = create_escalation_ticket(case, reason)
        case.escalation_summary = summary
        escalated_cases[case.case_id] = summary
        logger.info(f"[PRISM Agent] Escalation APPROVED by policy for {case.case_id}: {reason}")
    elif not policy.approved and policy.llm_proposed:
        logger.info(f"[PRISM Agent] Escalation proposed by LLM but DENIED by policy: {policy.reason}")

    # Proposal consumed
    case.escalation_proposed = False
    case.proposed_escalation_reason = None


def _policy_directive(policy: PolicyDecision) -> str:
    """A system directive that makes the follow-up reply match the policy decision."""
    if policy.decision == "ESCALATE":
        return (
            "POLICY DECISION: ESCALATE. The deterministic policy has authorized handing this "
            f"case to a human specialist. Reason: {policy.reason} "
            "In 1-2 short, warm sentences, tell the customer you are connecting them to a human "
            "specialist and briefly why, and reassure them their full context is preserved so they "
            "won't need to repeat anything. Do not ask new questions. Match the customer's language."
        )
    directive = (
        "POLICY DECISION: CONTINUE. The deterministic policy did NOT authorize escalation this "
        "turn. Do NOT tell the customer you are escalating or transferring them. "
    )
    if policy.llm_proposed:
        directive += (
            "Although you proposed escalation, the case has enough verified information to keep "
            "helping. "
        )
    directive += (
        "Answer helpfully in 1-3 short sentences based on the verified tool results. "
        "Match the customer's language."
    )
    return directive


def _pre_extract(case: CaseState) -> None:
    """Lightweight regex pre-extraction to keep UI confidence/intent in sync."""
    text = case.last_user_text or ""
    if not text:
        return
    m_tx = re.search(r"(tx[0-9a-z]{4,})", text, re.IGNORECASE)
    if m_tx and not case.transaction_id:
        case.transaction_id = m_tx.group(1).upper()
    if re.search(r"\b(human|agent|manager|representative|real person|insaan|insan|customer care|operator)\b", text, re.IGNORECASE):
        case.user_requested_human = True
    if not case.intent:
        if re.search(r"refund|cancel", text, re.IGNORECASE):
            case.intent = "refund_request"
        elif re.search(r"deliver|ship|tracking", text, re.IGNORECASE):
            case.intent = "delivery_issue"
        elif re.search(r"payment|charge|kat|deduct|confirm|order|transaction|paise|money", text, re.IGNORECASE):
            case.intent = "payment_issue"


def _generate_human_fallback_reply(text: str, case: CaseState) -> str:
    """Conversational fallback when the external LLM is offline."""
    t = (text or "").lower().strip()
    if any(k in t for k in ["hi", "hello", "hey", "namaste", "hallo"]):
        return "Hello! I'm PRISM. How can I help you today?"
    if "how are you" in t:
        return "I'm doing great, thank you! How can I assist you with your order or payment today?"
    if any(k in t for k in ["payment", "deducted", "kat gaya", "charge", "paise", "money"]):
        return "I understand your payment was deducted. I will definitely help you resolve this! Could you please share your Transaction ID or order number?"
    if case.transaction_id and case.payment_status:
        return f"Transaction {case.transaction_id} is verified. Payment status is {case.payment_status}."
    return "I'm here to help! Please tell me what issue you are facing or share your Transaction ID."


def _post_tool_fallback(case: CaseState) -> str:
    """Honest fallback reply if the follow-up LLM call fails (no hardcoded amounts)."""
    if case.escalated:
        return ("I've reviewed your case and I'm connecting you with a human specialist who can help "
                "further. Your full context is saved, so you won't need to repeat anything.")
    if case.transaction_id and case.payment_status:
        return f"I've verified transaction {case.transaction_id}: the payment status is {case.payment_status}."
    return "I've looked into that. Could you share a little more so I can help?"


def _record_user_turn(case: CaseState, incoming_messages: List[dict]) -> None:
    """Persist the latest user turn into conversation_history for the live transcript."""
    user_msgs = [m for m in incoming_messages if m.get("role") == "user"]
    if not user_msgs:
        return
    latest = user_msgs[-1].get("content", "")
    case.last_user_text = latest
    if not latest:
        return
    last = case.conversation_history[-1] if case.conversation_history else None
    if not (last and last.get("role") == "user" and last.get("content") == latest):
        case.conversation_history.append({"role": "user", "content": latest})


async def run_agent_turn(channel: str, incoming_messages: List[dict]) -> dict:
    """
    Process one conversation turn: LLM reasoning + tool calling, gated by the
    deterministic escalation policy. Returns {content, tool_executed, escalated,
    policy_decision}.
    """
    from datetime import datetime

    case = get_or_create_case(channel)
    case.last_activity_at = datetime.utcnow().isoformat()

    _record_user_turn(case, incoming_messages)

    # Interruption detection: if user spoke while AI was speaking,
    # mark interrupted and reset speaking state
    if getattr(case, 'barge_in_active', False):
        case.barge_in_active = False
        case.interrupted = True
        case.interruption_count = getattr(case, 'interruption_count', 0) + 1
        # Truncate current plan to completed steps
        current_plan = getattr(case, 'current_plan', None)
        if current_plan and hasattr(current_plan, 'truncate_to_current'):
            current_plan.truncate_to_current()
        logger.info(f"[PRISM Agent] Interruption detected (total: {case.interruption_count})")

    _pre_extract(case)

    # ── Memory: remember noteworthy short-term facts ────────────────────
    try:
        from memory_manager import get_memory_manager
        mm = get_memory_manager()
        last_user_text = case.last_user_text or ""
        # Extract simple user facts heuristically
        extracted_facts: Dict[str, Any] = {}
        name_match = re.search(r"\bmy name is\s+([A-Za-z ]{2,30})", last_user_text, re.IGNORECASE)
        if name_match:
            extracted_facts["user_name"] = name_match.group(1).strip()
        lang_match = re.search(r"\b(hindi|english|hinglish)\b", last_user_text, re.IGNORECASE)
        if lang_match:
            extracted_facts["preferred_language"] = lang_match.group(1).lower()
        if extracted_facts:
            mm.maybe_remember_user_facts(case, extracted_facts)
    except Exception as mem_e:
        logger.warning(f"[PRISM Agent] Memory remember skipped: {mem_e}")

    # ── RAG: search knowledge base if enabled ───────────────────────────
    retrieved_knowledge: Optional[List[str]] = None
    rag_citations: List[Dict[str, Any]] = []
    enable_rag = os.getenv("ENABLE_RAG", "false").lower() == "true"
    if enable_rag and last_user_text:
        try:
            from knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            results = kb.search(last_user_text, top_k=2)
            if results:
                retrieved_knowledge = []
                for text, score, source in results:
                    retrieved_knowledge.append(f"[Source: {source}] {text}")
                    rag_citations.append({"text": text, "source": source, "score": score})
        except Exception as rag_e:
            logger.warning(f"[PRISM Agent] RAG search failed: {rag_e}")

    # Save rag citations for this turn on case (exposed in _build_ai_state)
    case.rag_citations = rag_citations

    # ── Context assembly ────────────────────────────────────────────────
    conversation = [m for m in incoming_messages if m.get("role") != "system"]
    tools = get_tool_schemas(case)

    try:
        from context_engine import ContextManager
        ctx = ContextManager()
        full_messages = ctx.build_context(
            system_prompt=PRISM_VOICE_ASSISTANT_SYSTEM_PROMPT,
            case=case,
            incoming_messages=incoming_messages,
            retrieved_knowledge=retrieved_knowledge,
            last_user_text=case.last_user_text,
        )
    except Exception as ctx_e:
        logger.warning(f"[PRISM Agent] ContextManager fallback: {ctx_e}")
        system_messages = [
            {"role": "system", "content": PRISM_VOICE_ASSISTANT_SYSTEM_PROMPT},
            {"role": "system", "content": f"CURRENT CASE CONTEXT: {case.to_prompt_summary()}"},
        ]
        full_messages = system_messages + conversation

    # ── Primary LLM call ────────────────────────────────────────────────
    try:
        response = await prism_llm_call(
            messages=full_messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=250,
            temperature=0.7,
        )
    except Exception as e:
        logger.error(f"[PRISM Agent] LLM invocation error: {e}")
        from error_recovery import ErrorRecoveryEngine, FailureType
        recovery = ErrorRecoveryEngine().recover(FailureType.LLM, case, attempt=1)
        reply = recovery.reply
        from datetime import datetime
        case.conversation_history.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
        case.transcript_index = len(case.conversation_history)
        return {"content": reply, "tool_executed": None, "escalated": case.escalated,
                "policy_decision": case.policy_decision}

    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    tool_calls = message.get("tool_calls", [])

    # ── Tool path ───────────────────────────────────────────────────────
    if tool_calls:
        tool_executed_name = None
        tool_results_payload = []
        llm_proposed_escalation = False
        proposed_reason = ""

        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = fn.get("name")
            try:
                fn_args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                fn_args = {}
            if fn_name == "escalate_to_human":
                llm_proposed_escalation = True
                proposed_reason = fn_args.get("reason", "")
            tool_executed_name = fn_name
            tool_result = execute_tool(fn_name, fn_args, case)
            tool_results_payload.append({
                "role": "tool",
                "tool_call_id": tc.get("id", "call_1"),
                "content": json.dumps(tool_result),
            })

        # ── DETERMINISTIC POLICY GATE ───────────────────────────────────
        policy = evaluate_escalation(case, llm_proposed=llm_proposed_escalation, proposed_reason=proposed_reason)
        _apply_policy(case, policy)
        directive = _policy_directive(policy)

        follow_up_messages = full_messages + [
            {"role": "assistant", "tool_calls": tool_calls, "content": None}
        ] + tool_results_payload + [{"role": "system", "content": directive}]

        try:
            follow_response = await prism_llm_call(
                messages=follow_up_messages,
                max_tokens=200,
                temperature=0.7,
            )
            reply_text = follow_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"[PRISM Agent] Follow-up LLM invocation error: {e}")
            reply_text = _post_tool_fallback(case)

        case.conversation_history.append({"role": "assistant", "content": reply_text})
        return {
            "content": reply_text,
            "tool_executed": tool_executed_name,
            "escalated": case.escalated,
            "policy_decision": case.policy_decision,
        }

    # ── No-tool path ────────────────────────────────────────────────────
    reply_text = message.get("content", "")
    # Still run the gate so deterministic hard triggers (e.g. an explicit human
    # request the LLM didn't tool-call for) are honored.
    policy = evaluate_escalation(case, llm_proposed=False)
    _apply_policy(case, policy)

    case.conversation_history.append({"role": "assistant", "content": reply_text})
    return {
        "content": reply_text,
        "tool_executed": None,
        "escalated": case.escalated,
        "policy_decision": case.policy_decision,
    }
