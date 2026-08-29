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
    order_status: Optional[str] = None        # "CONFIRMED" / "NOT_CONFIRMED"
    duplicate_charge: str = "UNKNOWN"         # "YES" / "NO" / "UNKNOWN"
    language: list = field(default_factory=list)
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
