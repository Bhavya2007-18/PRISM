"""
PRISM State — the single shared operational-state contract.

These are the states the frontend ThinkingPanel renders and the backend derives.
The JavaScript mirror lives in `frontend/src/config/prismState.js` and MUST be
kept in sync with this file (identical names, identical order). Together they are
the one shared PrismState definition referenced by PRD §12 / tech-stack §27.

`derive_voice_state()` is the ONLY place a CaseState is turned into a PrismState,
so the /state, /active-state and /debug endpoints never duplicate the logic.
"""
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState


class PrismState(str, Enum):
    IDLE             = "IDLE"             # no active session
    CONNECTING       = "CONNECTING"       # joining the Agora channel
    LISTENING        = "LISTENING"        # session live, awaiting speech
    UNDERSTANDING    = "UNDERSTANDING"    # user spoke, parsing intent
    THINKING         = "THINKING"         # reasoning / choosing next action
    PLANNING         = "PLANNING"         # Planner building a plan
    ACTING           = "ACTING"           # running a tool (e.g. check_transaction)
    VERIFYING        = "VERIFYING"        # VerificationEngine checking result
    SPEAKING         = "SPEAKING"         # delivering a resolution
    ESCALATING       = "ESCALATING"       # handing off to a human
    HUMAN_CONNECTED  = "HUMAN_CONNECTED"  # human agent has taken over
    RESOLVED         = "RESOLVED"         # conversation successfully completed
    FAILED           = "FAILED"           # unrecoverable error state
    ENDED            = "ENDED"            # session explicitly ended


# Canonical ordered list — mirror of frontend/src/config/prismState.js
PRISM_STATES = [
    "IDLE", "CONNECTING", "LISTENING", "UNDERSTANDING", "THINKING",
    "PLANNING", "ACTING", "VERIFYING", "SPEAKING", "ESCALATING",
    "HUMAN_CONNECTED", "RESOLVED", "FAILED", "ENDED",
]


def derive_voice_state(case: "CaseState") -> str:
    """Single source of truth for mapping a CaseState -> PrismState value."""
    if case.taken_over:
        return PrismState.HUMAN_CONNECTED.value
    if getattr(case, 'session_ended', False):
        return PrismState.ENDED.value
    if getattr(case, 'failed', False):
        return PrismState.FAILED.value
    if getattr(case, 'resolved', False):
        return PrismState.RESOLVED.value
    if case.escalated:
        return PrismState.ESCALATING.value
    if case.payment_status and case.duplicate_charge == "UNKNOWN":
        return PrismState.ESCALATING.value
    # VERIFYING: tool just ran, verification in progress
    if getattr(case, 'verifying', False):
        return PrismState.VERIFYING.value
    # ACTING: tool call in progress
    if case.transaction_id and not case.payment_status:
        return PrismState.ACTING.value
    # PLANNING: plan is being built
    if getattr(case, 'planning', False):
        return PrismState.PLANNING.value
    if case.intent:
        return PrismState.THINKING.value
    if case.last_user_text:
        return PrismState.UNDERSTANDING.value
    return PrismState.LISTENING.value
