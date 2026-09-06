"""
PRISM Case State — structured in-memory case management.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class CaseState:
    case_id: str
    channel: str
    intent: Optional[str] = None
    transaction_id: Optional[str] = None
    amount: Optional[float] = None
    payment_status: Optional[str] = None      # "SUCCESS" / "FAILED"
    order_status: Optional[str] = None      # "CONFIRMED" / "NOT_CONFIRMED"
    duplicate_charge: str = "UNKNOWN"       # "YES" / "NO" / "UNKNOWN"
    language: list = field(default_factory=list)
    locale: Optional[str] = "en-IN"
    voice_mode: str = "agora_rtc"
    agora_channel: Optional[str] = None
    has_contradiction: bool = False
    tool_failed: bool = False
    user_requested_human: bool = False
    escalated: bool = False
    taken_over: bool = False
    escalation_reason: Optional[str] = None
    escalation_summary: Optional[dict] = None
    verified: list = field(default_factory=list)
    unverified: list = field(default_factory=list)
    conversation_history: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_user_text: Optional[str] = None
    # ── Policy gate + activity tracking ──────────────────────────────────
    escalation_proposed: bool = False           # LLM proposed escalate_to_human this turn
    proposed_escalation_reason: Optional[str] = None
    policy_decision: Optional[str] = None        # "ESCALATE" / "CONTINUE" (last gate result)
    policy_reason: Optional[str] = None
    last_activity_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    # ── Connection state ──────────────────────────────────────────────────
    connection_state: str = "DISCONNECTED"  # CONNECTING/CONNECTED/RECONNECTING/DISCONNECTED
    reconnect_attempts: int = 0
    agora_agent_id: Optional[str] = None   # the running Agora Conversational AI agent_id
    # ── New state flags (used by derive_voice_state) ─────────────────────────
    planning: bool = False       # Planner is building a plan
    verifying: bool = False      # VerificationEngine is checking result
    resolved: bool = False       # conversation successfully resolved
    failed: bool = False         # unrecoverable failure
    session_ended: bool = False  # session explicitly ended
    current_plan: Optional[object] = None   # Plan from planning.py
    verification_status: Optional[dict] = None  # Per-tool verification results from VerificationEngine
    # ── Barge-in / interruption tracking ─────────────────────────────────────
    barge_in_active: bool = False       # True when user speaks during SPEAKING state
    interrupted: bool = False           # True when current AI turn was interrupted
    interruption_count: int = 0         # total interruptions this session
    # ── Transcript tracking ───────────────────────────────────────────────────
    partial_transcript: Optional[str] = None    # live partial text during speech
    transcript_index: int = 0                   # increments on each new entry
    # ── Short-term memory ─────────────────────────────────────────────────────
    short_term_memory: dict = field(default_factory=dict)  # per-session ephemeral memory
    # ── Memory permissions ────────────────────────────────────────────────────
    memory_consent: bool = False                # user consent for long-term memory
    rag_citations: list = field(default_factory=list)   # RAG sources cited this turn

    def to_prompt_summary(self) -> str:
        known = []
        missing = []

        if self.intent:
            known.append(f"intent={self.intent}")
        else:
            missing.append("intent")

        if self.transaction_id:
            known.append(f"transaction_id={self.transaction_id}")
        else:
            missing.append("transaction_id")

        if self.amount:
            known.append(f"amount={self.amount}")
        else:
            missing.append("amount")

        if self.payment_status:
            known.append(f"payment_status={self.payment_status}")

        if self.order_status:
            known.append(f"order_status={self.order_status}")

        if self.duplicate_charge != "UNKNOWN":
            known.append(f"duplicate_charge={self.duplicate_charge}")
        else:
            missing.append("duplicate_charge (UNKNOWN)")

        verified_str = f"Verified by tool: {', '.join(self.verified)}" if self.verified else "Nothing verified by tool yet."
        known_str = f"Known: {', '.join(known)}" if known else "Known: nothing yet"
        missing_str = f"Still missing: {', '.join(missing)}" if missing else "Nothing missing"

        return f"{known_str}. {missing_str}. {verified_str}"


# In-memory store: channel -> CaseState
cases: dict[str, CaseState] = {}
# Escalated cases indexed by case_id
escalated_cases: dict[str, dict] = {}


def get_or_create_case(channel: str) -> CaseState:
    if channel not in cases:
        cases[channel] = CaseState(
            case_id=f"PRISM-{str(uuid.uuid4())[:8].upper()}",
            channel=channel,
        )
    return cases[channel]


def update_case_from_extract(channel: str, extracted: dict) -> None:
    """Merge LLM-extracted fields into case state."""
    case = get_or_create_case(channel)

    if extracted.get("intent") and not case.intent:
        case.intent = extracted["intent"]

    if extracted.get("transaction_id") and not case.transaction_id:
        case.transaction_id = extracted["transaction_id"]
        if "transaction_id" not in case.unverified:
            case.unverified.append("transaction_id")

    if extracted.get("amount") and not case.amount:
        try:
            case.amount = float(extracted["amount"])
            if "amount" not in case.unverified:
                case.unverified.append("amount")
        except (ValueError, TypeError):
            pass

    if extracted.get("language"):
        for lang in extracted["language"]:
            if lang and lang not in case.language:
                case.language.append(lang)

    if extracted.get("user_requested_human"):
        case.user_requested_human = True

    if extracted.get("has_contradiction"):
        case.has_contradiction = True
