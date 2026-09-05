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
    IDLE = "IDLE"                        # no active session
    CONNECTING = "CONNECTING"            # joining the Agora channel
    LISTENING = "LISTENING"             # session live, awaiting speech
    UNDERSTANDING = "UNDERSTANDING"     # user spoke, parsing intent
    THINKING = "THINKING"               # reasoning / choosing next action
    ACTING = "ACTING"                   # running a tool (e.g. check_transaction)
    SPEAKING = "SPEAKING"               # delivering a resolution
    ESCALATING = "ESCALATING"           # handing off to a human
    HUMAN_CONNECTED = "HUMAN_CONNECTED"  # human agent has taken over
    ERROR = "ERROR"                     # unrecoverable error


# Canonical ordered list — mirror of frontend/src/config/prismState.js
PRISM_STATES = [s.value for s in PrismState]


def derive_voice_state(case: "CaseState") -> str:
    """Single source of truth for mapping a CaseState -> PrismState value."""
    if case.taken_over:
        return PrismState.HUMAN_CONNECTED.value
    if case.escalated:
        return PrismState.ESCALATING.value
    if case.payment_status and case.duplicate_charge == "UNKNOWN":
        return PrismState.ESCALATING.value
    if case.transaction_id and not case.payment_status:
        return PrismState.ACTING.value
    if case.intent:
        return PrismState.THINKING.value
    if case.last_user_text:
        return PrismState.UNDERSTANDING.value
    return PrismState.LISTENING.value
