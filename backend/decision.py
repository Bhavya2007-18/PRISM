"""
PRISM Decision Engine — pure deterministic logic, no LLM.

The LLM handles language. This module handles decisions.
"""
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState


class Action(str, Enum):
    ASK = "ASK"
    CONFIRM = "CONFIRM"
    TOOL_CALL = "TOOL_CALL"
    RESOLVE = "RESOLVE"
    ESCALATE = "ESCALATE"


def decide(case: "CaseState") -> tuple[Action, str]:
    """
    Deterministically decide the next action based on case state.
    Returns (Action, reason_string).

    Priority order:
    1. Explicit escalation triggers (override everything)
    2. Missing critical information → ASK
    3. Tool call needed → TOOL_CALL
    4. Post-tool uncertainty → ESCALATE
    5. Resolved → RESOLVE
    """

    # ── Escalation triggers (multi-condition) ──────────────────────────
    if case.user_requested_human:
        return Action.ESCALATE, "Customer explicitly requested human assistance"

    if case.has_contradiction:
        return Action.ESCALATE, "Contradictory information detected in conversation"

    if case.tool_failed:
        return Action.ESCALATE, "Unable to verify transaction via external service"

    # ── Missing critical info ──────────────────────────────────────────
    if case.intent is None:
        return Action.ASK, "missing_intent"

    if case.transaction_id is None:
        return Action.ASK, "missing_transaction_id"

    # ── Tool call needed ───────────────────────────────────────────────
    if case.transaction_id and case.payment_status is None:
        return Action.TOOL_CALL, "check_transaction"

    # ── Post-tool assessment ───────────────────────────────────────────
    if case.payment_status is not None and case.duplicate_charge == "UNKNOWN":
        return Action.ESCALATE, "Cannot verify duplicate charge status — insufficient confidence"

    # ── Resolved ──────────────────────────────────────────────────────
    if case.payment_status and case.order_status and case.duplicate_charge != "UNKNOWN":
        return Action.RESOLVE, "All critical information verified"

    # ── Fallback ───────────────────────────────────────────────────────
    return Action.ASK, "missing_details"
