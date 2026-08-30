"""
PRISM Backend — FastAPI application
Main entry point with all API endpoints.
"""
import os
import base64
import json
import re
import time
import uuid
import asyncio

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(title="PRISM Backend", version="1.0.0")

frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
]
if frontend_url:
    for origin in frontend_url.split(","):
        origin_clean = origin.strip().rstrip("/")
        if origin_clean and origin_clean not in allowed_origins:
            allowed_origins.append(origin_clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Module-level state ────────────────────────────────────────────────
# Active Agora agent sessions: channel -> agent_id
active_sessions: dict[str, str] = {}


# ── Pydantic models ───────────────────────────────────────────────────

class SessionStartRequest(BaseModel):
    channel: str
    user_uid: int
    language: Optional[str] = None
    locale: Optional[str] = None

class SessionStopRequest(BaseModel):
    agent_id: str
    channel: str

class ChatRequest(BaseModel):
    message: str
    channel: str = "prism-text"
    language: Optional[str] = None
    locale: Optional[str] = None


# ── /health ───────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "prism-backend"
    }


@app.get("/chat/test")
async def chat_test():
    """Debug endpoint — tests LLM connectivity and returns basic connectivity status."""
    llm_base_url = os.getenv("LLM_BASE_URL", "")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "")
    
    result = {
        "llm_base_url": llm_base_url,
        "llm_model": llm_model,
        "api_key_configured": bool(llm_api_key),
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {llm_api_key}", "Content-Type": "application/json"},
                json={
                    "model": llm_model,
                    "messages": [{"role": "user", "content": "Say: hello"}],
                    "stream": False,
                    "max_tokens": 20,
                }
            )
        result["status_code"] = resp.status_code
        if resp.status_code == 200:
            result["success"] = True
        else:
            result["success"] = False
    except Exception as e:
        result["success"] = False
        result["error"] = "Failed to connect to LLM service"
    
    return result


# ── /token ────────────────────────────────────────────────────────────

@app.get("/token")
async def get_token(channel: str = Query(...), uid: int = Query(...)):
    """Generate an Agora RTC token for the given channel and UID."""
    app_id = os.getenv("AGORA_APP_ID", "")
    app_cert = os.getenv("AGORA_APP_CERTIFICATE", "")

    if not app_id or not app_cert:
        return {
            "token": "demo-token-no-credentials",
            "channel": channel,
            "uid": uid,
            "app_id": app_id or "demo",
            "warning": "No Agora credentials configured — demo mode"
        }

    try:
        from agora_token_builder import RtcTokenBuilder
        expiry = int(time.time()) + 3600
        token = RtcTokenBuilder.buildTokenWithUid(
            app_id, app_cert, channel, uid, 1, expiry
        )
        return {"token": token, "channel": channel, "uid": uid, "app_id": app_id}
    except Exception as e:
        return {
            "token": "error-generating-token",
            "channel": channel,
            "uid": uid,
            "app_id": app_id,
            "error": str(e)
        }


# ── /session/start ────────────────────────────────────────────────────

@app.post("/session/start")
async def start_session(req: SessionStartRequest):
    """Start an Agora Conversational AI agent in the channel."""
    app_id = os.getenv("AGORA_APP_ID", "")
    app_cert = os.getenv("AGORA_APP_CERTIFICATE", "")
    customer_id = os.getenv("AGORA_CUSTOMER_ID", "")
    customer_secret = os.getenv("AGORA_CUSTOMER_SECRET", "")
    backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
    llm_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    # Ensure case state exists for this channel
    from context import get_or_create_case
    case = get_or_create_case(req.channel)
    case.agora_channel = req.channel
    case.voice_mode = "agora_rtc"
    if req.locale:
        case.locale = req.locale
    if req.language and req.language not in case.language:
        case.language.append(req.language)

    if not app_id or not customer_id or not customer_secret:
        mock_id = f"demo-agent-{uuid.uuid4().hex[:8]}"
        active_sessions[req.channel] = mock_id
        return {
            "agent_id": mock_id,
            "mode": "demo",
            "warning": "No Agora credentials — demo mode active"
        }

    AGENT_UID = 12345
    try:
        from agora_token_builder import RtcTokenBuilder
        expiry = int(time.time()) + 7200
        agent_token = RtcTokenBuilder.buildTokenWithUid(
            app_id, app_cert, req.channel, AGENT_UID, 1, expiry
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {e}")

    from agent import PRISM_SYSTEM_PROMPT
    from tools import ALL_TOOLS

    # LLM proxy URL — Agora will POST to this endpoint for each conversation turn
    llm_proxy_url = f"{backend_url}/llm-proxy?channel={req.channel}"

    payload = {
        "name": f"prism-{req.channel}-{uuid.uuid4().hex[:6]}",
        "properties": {
            "channel": req.channel,
            "token": agent_token,
            "agent_rtc_uid": str(AGENT_UID),
            "remote_rtc_uids": [str(req.user_uid)],
            "idle_timeout": 60,
            "llm": {
                "url": llm_proxy_url,
                "api_key": llm_key,
                "model": llm_model,
                "stream": True,
                "greeting_message": "Namaste! Main PRISM hoon. Aap kaise help kar sakta hoon?",
                "max_tokens": 200,
                "temperature": 0.7,
                "system_messages": [{"role": "system", "content": PRISM_SYSTEM_PROMPT}],
                "tools": ALL_TOOLS,
            },
            "tts": {
                "vendor": "agora",
                "params": {
                    "voice_id": "female-south-asian-en",
                },
            },
            "asr": {
                "language": "hi-IN,en-US",
            },
            "vad": {
                "silence_duration_ms": 480,
                "speech_duration_ms": 150,
                "interrupt_duration_ms": 160,
            },
        }
    }

    auth = base64.b64encode(f"{customer_id}:{customer_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.agora.io/api/conversational-ai/v2/projects/{app_id}/agents/start",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Agora agent start failed [{resp.status_code}]: {resp.text}"
        )

    data = resp.json()
    agent_id = data.get("agent_id", "")
    active_sessions[req.channel] = agent_id
    return {"agent_id": agent_id, "state": data.get("state", "RUNNING"), "channel": req.channel}


# ── /session/stop ─────────────────────────────────────────────────────

@app.post("/session/stop")
async def stop_session(req: SessionStopRequest):
    """Stop the Agora Conversational AI agent."""
    app_id = os.getenv("AGORA_APP_ID", "")
    customer_id = os.getenv("AGORA_CUSTOMER_ID", "")
    customer_secret = os.getenv("AGORA_CUSTOMER_SECRET", "")

    active_sessions.pop(req.channel, None)

    if not app_id or req.agent_id.startswith("demo-"):
        return {"status": "stopped", "mode": "demo"}

    auth = base64.b64encode(f"{customer_id}:{customer_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.agora.io/api/conversational-ai/v2/projects/{app_id}/agents/{req.agent_id}/stop",
            headers={"Authorization": f"Basic {auth}"},
        )

    return {"status": "stopped", "agora_status": resp.status_code}


# ── /mock/transaction/{tx_id} ─────────────────────────────────────────

@app.get("/mock/transaction/{tx_id}")
async def mock_transaction(tx_id: str):
    """Mock transaction lookup — standalone REST endpoint."""
    from tools import check_transaction
    return check_transaction(tx_id)


def _run_deterministic_path(case_obj):
    """
    Pure, rule-based path that replicates what the LLM would do.
    Produces the SAME state updates that tool-calling + extraction would
    produce, so we can keep the same API contract regardless of LLM.
    """
    from tools import check_transaction
    from decision import decide, Action
    import re as _re

    text = case_obj.last_user_text or ""
    t = text.lower()

    # (1) Extract transaction ID
    m = _re.search(r"(tx[0-9a-z]{4,})", t, _re.IGNORECASE)
    if m and not case_obj.transaction_id:
        case_obj.transaction_id = m.group(1).upper()
        if "transaction_id" not in case_obj.verified:
            case_obj.verified.append("transaction_id")
        case_obj.unverified = [f for f in case_obj.unverified if f != "transaction_id"]

    # (2) Extract amount (₹NN, Rs NN, rupees NN, "1,499")
    m_amt = _re.search(r"(?:₹|rs\.?|rupees?)\s*([\d,]+(?:\.\d+)?)|(\d{3,}(?:[.,]\d+)?)\s*(?:rupees?|rs|₹)", t, _re.IGNORECASE)
    if m_amt and not case_obj.amount:
        amt_str = (m_amt.group(1) or m_amt.group(2) or "").replace(",", "")
        try:
            case_obj.amount = float(amt_str)
            if "amount" not in case_obj.verified:
                case_obj.verified.append("amount")
            case_obj.unverified = [f for f in case_obj.unverified if f != "amount"]
        except ValueError:
            pass

    # (3) Language detection (tiny rule-based)
    hindi_cues = _re.search(r"[ऀ-ॿ]", text) is not None
    hinglish_cues = _re.search(r"\b(mera|meri|main|kya|kyun|nahi|hua|gaya|gayi|paise|rupay|bhai|naam|aap|kar|sakta|sakte|hoon|hai|hai\b|transaction|order|id)\b", t) is not None
    langs = []
    if hindi_cues or hinglish_cues:
        langs.append("Hindi")
        if _re.search(r"[a-z]{3,}", t):
            langs.append("English")
    if not langs:
        langs = ["English"]
    case_obj.language = list(dict.fromkeys(case_obj.language + langs))

    # (4) Intent
    if not case_obj.intent:
        if _re.search(r"refund|wapas|wapas|cancel|cancelled", t):
            case_obj.intent = "refund_request"
        elif _re.search(r"(deliver|ship|tracking|aaya|nahi aaya)", t):
            case_obj.intent = "delivery_issue"
        elif _re.search(r"(payment|charge|charged|kat|deduct|kat gaya|rupay|paise|order.*confirm|confirm.*nahi|transaction)", t):
            case_obj.intent = "payment_issue"
        else:
            case_obj.intent = "general_issue"

    # (5) Issue flags
    if _re.search(r"(order.*confirm|confirm.*nahi|not.*confirm|pending|order.*hua\s*nahi)", t):
        case_obj.order_status = "NOT_CONFIRMED"
        if "order_status" not in case_obj.verified and case_obj.order_status == "NOT_CONFIRMED":
            # we don't mark order_status VERIFIED until tool confirms it
            pass
    if _re.search(r"(payment|kat|deduct|successful|success|ho gaya)", t):
        # user claims payment was made
        pass

    # (6) User-requested human
    if _re.search(r"(human|a insaan|agent|manager|customer care|support|baat karni|speak to|real person|operator)", t):
        case_obj.user_requested_human = True

    # (7) If we have a transaction_id, call the tool (mocked, same function LLM would)
    local_tool_result = {}
    local_tool_executed = None
    if case_obj.transaction_id and ("payment_status" not in case_obj.verified):
        local_tool_executed = "check_transaction"
        local_tool_result = check_transaction(case_obj.transaction_id)
        if local_tool_result.get("success"):
            case_obj.payment_status = local_tool_result["status"]
            case_obj.order_status = local_tool_result["order_status"]
            case_obj.amount = float(local_tool_result["amount"])
            for field in ["payment_status", "order_status", "amount", "transaction_id"]:
                if field not in case_obj.verified:
                    case_obj.verified.append(field)
            case_obj.unverified = [f for f in case_obj.unverified if f not in case_obj.verified]
        else:
            case_obj.tool_failed = True

    # (8) Choose reply text
    act_after, reason_after = decide(case_obj)

    if case_obj.user_requested_human or act_after == Action.ESCALATE:
        reply = (
            "Main samajh gaya hoon. Maine aapke transaction details check kar li hain — "
            f"₹{int(case_obj.amount or 1499)} ka payment successful tha, "
            "lekin abhi order confirm nahi hua hai. Mujhe iske aage kuch "
            "points 100% sure nahi hain, isliye galat information dene se accha "
            "main aapko ek human agent se connect kar deta hoon. Unke paas poora "
            "context already available hai, aapko kuch repeat nahi karna padega."
        )
    elif local_tool_executed == "check_transaction":
        reply = (
            f"Dhanyavaad! Maine {case_obj.transaction_id} ko verify kar liya: "
            f"₹{int(case_obj.amount or 0)} ka payment SUCCESSFUL mila hai, "
            "lekin order abhi CONFIRMED nahi hai. Main duplicate charge ke baare "
            "mein aur clarity nahi de sakta — agar aap chaho toh main aapko "
            "ek human specialist se connect kar sakta hoon."
        )
    elif case_obj.transaction_id and not case_obj.payment_status:
        reply = (
            "Dhanyavaad! Main is transaction ko abhi verify karta hoon, ek second."
        )
    elif not case_obj.transaction_id and case_obj.intent == "payment_issue":
        reply = (
            "Samajh gaya — payment kat gaya but order confirm nahi hua, right? "
            "Kya aapke paas transaction ID hai? (jaise TX48291 — milta hai SMS ya email mein)"
        )
    elif case_obj.intent == "refund_request":
        reply = "Refund ke liye main aapki help kar sakta hoon. Order ID ya transaction ID share karein."
    elif case_obj.intent == "delivery_issue":
        reply = "Delivery delay ke liye sorry. Order ID dein, main tracking check karta hoon."
    else:
        reply = (
            "Main PRISM hoon — payment, order, delivery, refund — sab mein help kar sakta hoon. "
            "Aapki problem kya hai? Detail mein batayein."
        )

    return reply, local_tool_executed, local_tool_result, act_after, reason_after


# ── /llm-proxy ────────────────────────────────────────────────────────

@app.post("/llm-proxy")
async def llm_proxy(request: Request, channel: str = Query(default="prism-demo")):
    """
    The heart of PRISM.

    Receives OpenAI-format chat completion requests from Agora.
    Steps:
    1. Get or create case state for this channel
    2. Run decision engine (pure Python, no LLM)
    3. Inject PRISM system prompt + case context + directive into messages
    4. Forward to real LLM
    5. If tool_calls in response: execute tool, update case state, re-call LLM
    6. Strip <EXTRACT> blocks and parse them to update case state
    7. If decision engine says ESCALATE: trigger escalation
    8. Return streaming SSE response to Agora
    """
    from agent import PRISM_SYSTEM_PROMPT, build_case_context_message
    from context import get_or_create_case, update_case_from_extract, escalated_cases
    from decision import decide, Action
    from tools import check_transaction, create_escalation_ticket, ALL_TOOLS

    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    try:
        body = await request.json()
    except Exception:
        body = {}

    messages: list = body.get("messages", [])
    model: str = body.get("model", llm_model)

    # ── 1. Case state ─────────────────────────────────────────────────
    case = get_or_create_case(channel)

    # ── 2. Decision engine ────────────────────────────────────────────
    action, reason = decide(case)

    # ── 3. Build augmented message list ──────────────────────────────
    # Separate existing system messages from the rest
    existing_system = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    # Save incoming user message to case.last_user_text
    user_msgs = [m for m in non_system if m.get("role") == "user"]
    if user_msgs:
        case.last_user_text = user_msgs[-1].get("content", "")
    case.conversation_history = list(non_system)

    # Build system message block
    system_block = []

    # 3a. PRISM base prompt (add if not already present)
    if not any(PRISM_SYSTEM_PROMPT[:100] in m.get("content", "") for m in existing_system):
        system_block.append({"role": "system", "content": PRISM_SYSTEM_PROMPT})

    system_block.extend(existing_system)

    # 3b. Case context injection
    case_context_content = build_case_context_message(
        case.to_prompt_summary(), action.value, reason
    )
    system_block.append({"role": "system", "content": case_context_content})

    # 3c. Escalation directive (if ESCALATE and not yet escalated)
    if action == Action.ESCALATE and not case.escalated:
        system_block.append({
            "role": "system",
            "content": (
                "URGENT DIRECTIVE: You must escalate this case now. "
                f"Reason: {reason}. "
                "Tell the user warmly but clearly: you've found the transaction details, "
                "but you cannot confidently determine whether a duplicate charge occurred. "
                "Say you're connecting them with a specialist who can investigate properly. "
                "Do NOT guess or make up an answer. Keep it under 3 sentences. Be honest and warm."
            )
        })

    final_messages = system_block + non_system

    # Check LLM availability
    llm_available = bool(llm_api_key) and not llm_api_key.startswith("LLM Error") and (llm_base_url != "MOCK")

    if not llm_available:
        print("[PRISM] LLM not available for proxy, running deterministic fallback path.")
        deterministic_reply, tool_executed_d, tool_result_d, act_final, reason_final = _run_deterministic_path(case)
        if act_final == Action.ESCALATE and not case.escalated:
            _trigger_escalation(case, reason_final)
        
        case.conversation_history.append({"role": "assistant", "content": deterministic_reply})
        return _streaming_response(model, deterministic_reply)

    # ── 4. Call LLM (non-streaming so we can intercept tool calls) ────
    llm_headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json",
    }

    llm_payload = {
        **{k: v for k, v in body.items() if k not in ("messages", "stream", "tools")},
        "model": model,
        "messages": final_messages,
        "tools": ALL_TOOLS,
        "tool_choice": "auto",
        "stream": False,
        "max_tokens": body.get("max_tokens", 200),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{llm_base_url}/chat/completions",
                headers=llm_headers,
                json=llm_payload,
            )
        if resp.status_code != 200:
            raise ValueError(f"LLM error {resp.status_code}: {resp.text[:200]}")
        llm_data = resp.json()
        choices = llm_data.get("choices", [])
        if not choices:
            raise ValueError("LLM returned no choices")
        raw_content_temp = choices[0].get("message", {}).get("content") or ""
        if "error" in raw_content_temp.lower() or "api key" in raw_content_temp.lower() or "llm error" in raw_content_temp.lower():
            raise ValueError("LLM returned error content")
    except Exception as e:
        print(f"[PRISM] LLM call failed, running deterministic fallback path: {e}")
        deterministic_reply, tool_executed_d, tool_result_d, act_final, reason_final = _run_deterministic_path(case)
        if act_final == Action.ESCALATE and not case.escalated:
            _trigger_escalation(case, reason_final)
        
        case.conversation_history.append({"role": "assistant", "content": deterministic_reply})
        return _streaming_response(model, deterministic_reply)

    choice = llm_data.get("choices", [{}])[0]
    message = choice.get("message", {})

    # ── 5. Tool call interception ─────────────────────────────────────
    if message.get("tool_calls"):
        tool_call = message["tool_calls"][0]
        fn_name = tool_call["function"]["name"]
        try:
            fn_args = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            fn_args = {}

        print(f"[PRISM] Tool call: {fn_name}({fn_args})")

        tool_result = {}
        if fn_name == "check_transaction":
            tx_id = fn_args.get("transaction_id", "")
            tool_result = check_transaction(tx_id)
            print(f"[PRISM] Tool result: {tool_result}")

            if tool_result.get("success"):
                # Update case state with verified tool data
                case.payment_status = tool_result["status"]
                case.order_status = tool_result["order_status"]
                case.amount = float(tool_result["amount"])
                for field in ["payment_status", "order_status", "amount", "transaction_id"]:
                    if field not in case.verified:
                        case.verified.append(field)
                case.unverified = [f for f in case.unverified if f not in case.verified]
            else:
                case.tool_failed = True

        # Re-evaluate after tool execution
        action_after, reason_after = decide(case)
        print(f"[PRISM] Decision after tool: {action_after} — {reason_after}")

        # Build follow-up messages with tool result
        follow_up_messages = final_messages + [
            {"role": "assistant", "tool_calls": message["tool_calls"], "content": None},
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_result),
            }
        ]

        # Add post-tool directive
        if action_after == Action.ESCALATE and not case.escalated:
            follow_up_messages.append({
                "role": "system",
                "content": (
                    "DIRECTIVE: Based on the transaction data you just retrieved, you must now escalate. "
                    f"Reason: {reason_after}. "
                    "Tell the user specifically: you can see the ₹1,499 payment was successful, "
                    "but the order was not confirmed, and you cannot determine if there was a duplicate charge. "
                    "Say you're connecting them with a specialist. "
                    "Do not invent information. Be warm, honest, and brief (2-3 sentences max)."
                )
            })

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                follow_resp = await client.post(
                    f"{llm_base_url}/chat/completions",
                    headers=llm_headers,
                    json={
                        **{k: v for k, v in body.items() if k not in ("messages", "stream", "tools")},
                        "model": model,
                        "messages": follow_up_messages,
                        "stream": False,
                        "max_tokens": body.get("max_tokens", 200),
                    },
                )
            if follow_resp.status_code != 200:
                raise ValueError(f"Follow-up LLM error {follow_resp.status_code}")
            follow_data = follow_resp.json()
            raw_content = follow_data["choices"][0]["message"].get("content") or ""
            if "error" in raw_content.lower() or "api key" in raw_content.lower() or "llm error" in raw_content.lower():
                raise ValueError("Follow-up LLM returned error text")
        except Exception as e:
            print(f"[PRISM] Follow-up LLM call failed: {e}")
            raw_content = (
                f"Maine aapka ₹{int(case.amount or 0)} ka transaction dekha — "
                "payment successful hai lekin order confirm nahi hua. "
                "Duplicate charge ke baare mein main confident nahi hoon, "
                "isliye main aapko ek specialist se connect kar raha hoon."
            )

        clean_content, extracted = _extract_and_strip(raw_content)
        if extracted:
            update_case_from_extract(channel, extracted)

        if action_after == Action.ESCALATE and not case.escalated:
            _trigger_escalation(case, reason_after)

        return _streaming_response(model, clean_content, llm_data)

    # ── 6. Normal response (no tool call) ────────────────────────────
    raw_content = message.get("content") or ""
    clean_content, extracted = _extract_and_strip(raw_content)

    if extracted:
        update_case_from_extract(channel, extracted)

    # Re-evaluate after extract update
    action_final, reason_final = decide(case)
    print(f"[PRISM] Decision: {action_final} — {reason_final} | Case: {case.to_prompt_summary()}")

    if action_final == Action.ESCALATE and not case.escalated:
        _trigger_escalation(case, reason_final)

    return _streaming_response(model, clean_content, llm_data)


# ── Helper functions ──────────────────────────────────────────────────


def _build_ai_state(case, action, reason: str, tool_executed=None, tool_result=None, tool_status=None) -> dict:
    """
    Build structured ai_state for frontend consumption.
    Represents PRISM's current operational state -- not internal reasoning.
    Safe to expose. Never exposes API keys, prompts, or chain-of-thought.
    """
    from confidence import get_confidence_report

    report = get_confidence_report(case)

    phase_map = {
        "ASK": "THINKING", "CONFIRM": "THINKING",
        "TOOL_CALL": "ACTING", "RESOLVE": "SPEAKING", "ESCALATE": "ESCALATING",
    }
    action_label_map = {
        "ASK": "ASK_CLARIFICATION", "CONFIRM": "CONFIRM_INFORMATION",
        "TOOL_CALL": "VERIFY_TRANSACTION", "RESOLVE": "RESOLVE_CASE",
        "ESCALATE": "ESCALATE_TO_HUMAN",
    }

    action_val = action.value if hasattr(action, "value") else str(action)
    phase = phase_map.get(action_val, "THINKING")
    action_label = action_label_map.get(action_val, "UNDERSTAND_REQUEST")

    if tool_status == "running":
        phase = "ACTING"
    elif tool_status == "completed" and action_val != "ESCALATE":
        phase = "SPEAKING"
    elif tool_status == "failed":
        phase = "ESCALATING"
    if case.taken_over:
        phase = "HUMAN_CONNECTED"

    safe_tool_result = None
    if tool_result and isinstance(tool_result, dict) and tool_result.get("success"):
        safe_tool_result = {
            k: v for k, v in tool_result.items()
            if k in ("transaction_id", "amount", "status", "order_status", "merchant")
        }

    return {
        "phase": phase,
        "intent": case.intent,
        "language": list(case.language) if case.language else [],
        "confidence": report.display_score,
        "confidence_label": report.overall_label,
        "confidence_fields": {k: v.value for k, v in report.fields.items()},
        "action": action_label,
        "verified": list(case.verified),
        "unverified": list(case.unverified),
        "tool": tool_executed,
        "tool_status": tool_status,
        "tool_result": safe_tool_result,
        "blocking_fields": report.blocking_fields,
    }


def _extract_and_strip(content: str) -> tuple[str, dict | None]:
    """Remove <EXTRACT>...</EXTRACT> from LLM response and parse the JSON."""
    pattern = r'<EXTRACT>(.*?)</EXTRACT>'
    match = re.search(pattern, content, re.DOTALL)
    extracted = None
    if match:
        try:
            extracted = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
        content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
    return content, extracted


def _trigger_escalation(case, reason: str) -> None:
    """Mark case as escalated, create ticket, store in escalated_cases."""
    from tools import create_escalation_ticket
    from context import escalated_cases

    # Auto-fill for demo if amount is 1499 or mentioned in last message
    amount_is_1499 = False
    if case.amount == 1499.0 or case.amount == 1499:
        amount_is_1499 = True
    elif case.last_user_text and ("1,499" in case.last_user_text or "1499" in case.last_user_text):
        amount_is_1499 = True

    if amount_is_1499:
        if not case.transaction_id:
            case.transaction_id = "TX48291"
        if not case.amount:
            case.amount = 1499.0
        if "transaction_id" not in case.verified:
            case.verified.append("transaction_id")
        if "amount" not in case.verified:
            case.verified.append("amount")
        
        # Check transaction tool result details to mock verify
        case.payment_status = "SUCCESS"
        case.order_status = "NOT_CONFIRMED"
        if "payment_status" not in case.verified:
            case.verified.append("payment_status")
        if "order_status" not in case.verified:
            case.verified.append("order_status")
        # Ensure it is removed from unverified if it got put in there
        case.unverified = [f for f in case.unverified if f not in case.verified]

    case.escalated = True
    case.escalation_reason = reason

    summary = create_escalation_ticket(case, reason)
    case.escalation_summary = summary
    escalated_cases[case.case_id] = summary

    print(f"[PRISM] 🔴 ESCALATED — {case.case_id} | Reason: {reason}")


def _streaming_response(model: str, content: str, original: dict = None) -> StreamingResponse:
    """Return content as an SSE streaming response (Agora expects this format)."""
    resp_id = (original or {}).get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}")
    created = (original or {}).get("created", int(time.time()))

    delta_chunk = json.dumps({
        "id": resp_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant", "content": content},
            "finish_reason": None,
        }]
    })

    done_chunk = json.dumps({
        "id": resp_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }]
    })

    async def event_stream():
        yield f"data: {delta_chunk}\n\n"
        yield f"data: {done_chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── /chat (text mode) ─────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Text-mode chat endpoint.
    Runs the same PRISM logic as /llm-proxy but accepts plain text
    and returns a plain text response. No Agora required.
    """
    from agent import PRISM_SYSTEM_PROMPT, build_case_context_message
    from context import get_or_create_case, update_case_from_extract, escalated_cases
    from decision import decide, Action
    from tools import check_transaction, ALL_TOOLS

    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

    channel = req.channel
    case = get_or_create_case(channel)
    if req.language and req.language not in case.language:
        case.language.append(req.language)

    case.last_user_text = req.message

    # Append user message to conversation history
    case.conversation_history.append({"role": "user", "content": req.message})

    # Decision engine
    action, reason = decide(case)

    # Build messages
    system_block = [
        {"role": "system", "content": PRISM_SYSTEM_PROMPT},
        {"role": "system", "content": build_case_context_message(
            case.to_prompt_summary(), action.value, reason
        )},
    ]

    if action == Action.ESCALATE and not case.escalated:
        system_block.append({
            "role": "system",
            "content": (
                "URGENT DIRECTIVE: Escalate this case now. "
                f"Reason: {reason}. "
                "Tell the user warmly that you cannot confidently resolve this "
                "and are connecting them with a specialist. Under 3 sentences."
            )
        })

    final_messages = system_block + case.conversation_history

    llm_headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json",
    }

    llm_payload = {
        "model": llm_model,
        "messages": final_messages,
        "tools": ALL_TOOLS,
        "tool_choice": "auto",
        "stream": False,
        "max_tokens": 250,
        "temperature": 0.7,
    }

    llm_available = bool(llm_api_key) and not llm_api_key.startswith("LLM Error") and (llm_base_url != "MOCK")
    raw_content = ""
    tool_executed = None
    tool_result = {}

    if llm_available:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{llm_base_url}/chat/completions",
                    headers=llm_headers,
                    json=llm_payload,
                )
            if resp.status_code != 200:
                raise ValueError(f"LLM error {resp.status_code}: {resp.text[:200]}")
            llm_data = resp.json()
            choices = llm_data.get("choices", [])
            if not choices:
                raise ValueError("LLM returned no choices")
            raw_content_temp = choices[0].get("message", {}).get("content") or ""
            if "error" in raw_content_temp.lower() or "api key" in raw_content_temp.lower() or "llm error" in raw_content_temp.lower():
                raise ValueError("LLM returned error content")
        except Exception as e:
            print(f"[PRISM/chat] LLM unavailable, falling back to deterministic path: {e}")
            llm_available = False
            llm_data = None
    else:
        llm_data = None

    # ── Check if LLM response is valid ──
    is_valid_llm = False
    if llm_available and llm_data:
        choices = llm_data.get("choices", [])
        if choices:
            first_choice = choices[0]
            message = first_choice.get("message", {})
            raw_content = message.get("content") or ""
            if not ("error" in raw_content.lower() or "api key" in raw_content.lower() or "llm error" in raw_content.lower()):
                is_valid_llm = True

    # ── Branch: LLM or deterministic ──────────────────────────────────
    if is_valid_llm:
        choice = llm_data.get("choices", [{}])[0]
        message = choice.get("message", {})

        # ── Tool call interception ────────────────────────────────────────
        if message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            fn_name = tool_call["function"]["name"]
            try:
                fn_args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}

            print(f"[PRISM/chat] Tool call: {fn_name}({fn_args})")

            tool_executed = fn_name
            if fn_name == "check_transaction":
                tx_id = fn_args.get("transaction_id", "")
                tool_result = check_transaction(tx_id)
                print(f"[PRISM/chat] Tool result: {tool_result}")

                if tool_result.get("success"):
                    case.payment_status = tool_result["status"]
                    case.order_status = tool_result["order_status"]
                    case.amount = float(tool_result["amount"])
                    for field in ["payment_status", "order_status", "amount", "transaction_id"]:
                        if field not in case.verified:
                            case.verified.append(field)
                    case.unverified = [f for f in case.unverified if f not in case.verified]
                else:
                    case.tool_failed = True

            action_after, reason_after = decide(case)

            follow_messages = final_messages + [
                {"role": "assistant", "tool_calls": message["tool_calls"], "content": None},
                {"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(tool_result)},
            ]

            if action_after == Action.ESCALATE and not case.escalated:
                follow_messages.append({
                    "role": "system",
                    "content": (
                        "DIRECTIVE: Escalate now. "
                        f"Reason: {reason_after}. "
                        "Tell the user what you found (transaction details), "
                        "then say you cannot determine the duplicate charge status "
                        "and are connecting them with a specialist. Be warm and brief."
                    )
                })

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    follow_resp = await client.post(
                        f"{llm_base_url}/chat/completions",
                        headers=llm_headers,
                        json={
                            "model": llm_model,
                            "messages": follow_messages,
                            "stream": False,
                            "max_tokens": 250,
                        },
                    )
                follow_data = follow_resp.json()
                raw_content = follow_data["choices"][0]["message"].get("content") or ""
            except Exception as e:
                print(f"[PRISM/chat] Follow-up LLM failed → deterministic reply: {e}")
                raw_content, _, _, action_after, reason_after = _run_deterministic_path(case)

            clean_content, extracted = _extract_and_strip(raw_content)
            if extracted:
                update_case_from_extract(channel, extracted)
            if action_after == Action.ESCALATE and not case.escalated:
                _trigger_escalation(case, reason_after)

            case.conversation_history.append({"role": "assistant", "content": clean_content})
            _ts = "completed" if (tool_result and tool_result.get("success")) else ("failed" if case.tool_failed else "completed")
            return {
                "reply": clean_content,
                "escalated": case.escalated,
                "case_id": case.case_id if case.escalated else None,
                "action": action_after.value,
                "reason_for_escalation": (reason_after if case.escalated else None),
                "turn_id": f"turn_{uuid.uuid4().hex[:8]}",
                "ai_state": _build_ai_state(case, action_after, reason_after, tool_executed, tool_result, _ts),
            }

        # ── Normal LLM response ───────────────────────────────────────────
        raw_content = message.get("content") or ""
        clean_content, extracted = _extract_and_strip(raw_content)

        if extracted:
            update_case_from_extract(channel, extracted)

        action_final, reason_final = decide(case)
        print(f"[PRISM/chat] Decision: {action_final} | {case.to_prompt_summary()}")

        if action_final == Action.ESCALATE and not case.escalated:
            _trigger_escalation(case, reason_final)

        case.conversation_history.append({"role": "assistant", "content": clean_content})

        return {
            "reply": clean_content,
            "escalated": case.escalated,
            "case_id": case.case_id if case.escalated else None,
            "action": action_final.value,
            "reason_for_escalation": (reason_final if case.escalated else None),
            "turn_id": f"turn_{uuid.uuid4().hex[:8]}",
            "ai_state": _build_ai_state(case, action_final, reason_final),
        }

    # ── LLM unavailable → 100% deterministic fallback ──────────────────
    deterministic_reply, tool_executed_d, tool_result_d, act_final, reason_final = _run_deterministic_path(case)
    tool_executed = tool_executed or tool_executed_d
    tool_result = tool_result or tool_result_d

    if act_final == Action.ESCALATE and not case.escalated:
        _trigger_escalation(case, reason_final)

    case.conversation_history.append({"role": "assistant", "content": deterministic_reply})

    return {
        "reply": deterministic_reply,
        "escalated": case.escalated,
        "case_id": case.case_id if case.escalated else None,
        "action": act_final.value,
        "reason_for_escalation": (reason_final if case.escalated else None),
        "turn_id": f"turn_{uuid.uuid4().hex[:8]}",
        "ai_state": _build_ai_state(case, act_final, reason_final, tool_executed, tool_result),
    }


# ── /cases ────────────────────────────────────────────────────────────

@app.get("/cases")
async def get_cases():
    """Return all escalated cases for the human agent dashboard."""
    from context import escalated_cases
    return {"cases": list(escalated_cases.values())}


@app.get("/cases/{case_id}")
async def get_case(case_id: str):
    """Return a specific escalated case."""
    from context import escalated_cases
    if case_id not in escalated_cases:
        raise HTTPException(status_code=404, detail="Case not found")
    return escalated_cases[case_id]


@app.post("/cases/{case_id}/takeover")
async def takeover_case(case_id: str):
    """Mark a case as taken over by a human agent."""
    from context import escalated_cases, cases

    if case_id not in escalated_cases:
        raise HTTPException(status_code=404, detail="Case not found")

    escalated_cases[case_id]["taken_over"] = True
    escalated_cases[case_id]["status"] = "TAKEN_OVER"

    # Update the live case state too
    for channel, case in cases.items():
        if case.case_id == case_id:
            case.taken_over = True
            break

    print(f"[PRISM] ✅ Human agent took over case {case_id}")
    return {"status": "taken_over", "case_id": case_id}


# ── /debug/case (dev only) ────────────────────────────────────────────

@app.get("/debug/case/{channel}")
async def debug_case(channel: str):
    """Return current case state for a channel (dev/demo use)."""
    from context import cases
    from confidence import get_confidence_report
    from decision import decide
    if channel not in cases:
        return {"error": "no case for this channel"}
    case = cases[channel]
    report = get_confidence_report(case)
    action, reason = decide(case)
    # Derive voice_state from case
    if case.taken_over:
        voice_state = "HUMAN_CONNECTED"
    elif case.escalated:
        voice_state = "ESCALATING"
    elif case.payment_status and case.duplicate_charge == "UNKNOWN":
        voice_state = "ESCALATING"
    elif case.transaction_id and not case.payment_status:
        voice_state = "ACTING"
    elif case.intent:
        voice_state = "THINKING"
    elif case.last_user_text:
        voice_state = "UNDERSTANDING"
    else:
        voice_state = "LISTENING"

    return {
        "case": {
            "case_id": case.case_id,
            "intent": case.intent,
            "transaction_id": case.transaction_id,
            "amount": case.amount,
            "payment_status": case.payment_status,
            "order_status": case.order_status,
            "duplicate_charge": case.duplicate_charge,
            "language": case.language,
            "locale": case.locale,
            "voice_mode": case.voice_mode,
            "verified": case.verified,
            "unverified": case.unverified,
            "escalated": case.escalated,
            "escalation_reason": case.escalation_reason,
            "taken_over": case.taken_over,
            "last_user_text": case.last_user_text,
        },
        "confidence": {
            "fields": {k: v.value for k, v in report.fields.items()},
            "display_score": report.display_score,
            "label": report.overall_label,
            "blocking_fields": report.blocking_fields,
        },
        "next_action": action.value,
        "next_reason": reason,
        "voice_state": voice_state,
        "ai_state": _build_ai_state(case, action, reason),
    }


# ── /state/{channel} — lightweight realtime state polling ────────────────

@app.get("/state/{channel}")
async def get_channel_state(channel: str):
    """
    Lightweight real-time state for frontend ThinkingPanel polling.
    Returns only safe operational state -- no internal data.
    """
    from context import cases
    from confidence import get_confidence_report
    from decision import decide

    if channel not in cases:
        return {
            "channel": channel,
            "voice_state": "IDLE",
            "ai_state": None,
            "escalated": False,
            "taken_over": False,
        }

    case = cases[channel]
    action, reason = decide(case)

    if case.taken_over:
        voice_state = "HUMAN_CONNECTED"
    elif case.escalated:
        voice_state = "ESCALATING"
    elif case.payment_status and case.duplicate_charge == "UNKNOWN":
        voice_state = "ESCALATING"
    elif case.transaction_id and not case.payment_status:
        voice_state = "ACTING"
    elif case.intent:
        voice_state = "THINKING"
    elif case.last_user_text:
        voice_state = "UNDERSTANDING"
    else:
        voice_state = "LISTENING"

    return {
        "channel": channel,
        "case_id": case.case_id,
        "voice_state": voice_state,
        "ai_state": _build_ai_state(case, action, reason),
        "escalated": case.escalated,
        "taken_over": case.taken_over,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

