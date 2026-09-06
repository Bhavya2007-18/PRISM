# ENGINE: VoiceEngine
"""
PRISM Error Recovery Engine

Handles failure recovery for all voice pipeline components.
Every failure gets a recovery path — no silent errors.

Recovery paths:
    STT_FAILURE     → ask user to repeat
    LLM_FAILURE     → fallback response (no LLM needed)
    TOOL_FAILURE    → retry once → alternative → escalate
    TTS_FAILURE     → text fallback (not applicable in Agora mode)
    AGORA_FAILURE   → reconnect state
    UNKNOWN         → safe reset to LISTENING
"""
import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    STT     = "STT_FAILURE"
    LLM     = "LLM_FAILURE"
    TOOL    = "TOOL_FAILURE"
    TTS     = "TTS_FAILURE"
    AGORA   = "AGORA_FAILURE"
    UNKNOWN = "UNKNOWN"


class RecoveryResult:
    def __init__(self, reply: str, should_escalate: bool = False, reset_state: bool = False):
        self.reply = reply
        self.should_escalate = should_escalate
        self.reset_state = reset_state


class ErrorRecoveryEngine:
    """
    Centralises all failure recovery logic for the PRISM voice pipeline.
    """

    def recover(self, failure_type: FailureType, case: "CaseState", attempt: int = 1) -> RecoveryResult:
        """
        Return a recovery action for the given failure type.
        
        Args:
            failure_type: Type of failure that occurred
            case: Current case state
            attempt: Retry attempt number (1 = first failure)
        """
        logger.warning(f"[PRISM][ErrorRecovery] {failure_type} on attempt {attempt} for channel={case.channel}")

        if failure_type == FailureType.STT:
            return self._recover_stt(case, attempt)
        elif failure_type == FailureType.LLM:
            return self._recover_llm(case, attempt)
        elif failure_type == FailureType.TOOL:
            return self._recover_tool(case, attempt)
        elif failure_type == FailureType.TTS:
            return self._recover_tts(case)
        elif failure_type == FailureType.AGORA:
            return self._recover_agora(case)
        else:
            return self._recover_unknown(case)

    def _recover_stt(self, case: "CaseState", attempt: int) -> RecoveryResult:
        """STT failed — ask user to repeat."""
        langs = getattr(case, 'language', [])
        uses_hindi = any(l in ('hi', 'hi-IN', 'hi-en') for l in langs)
        if uses_hindi:
            reply = "Maafi chahta hoon, mujhe aapki baat samajh nahi aayi. Kya aap dobara bol sakte hain?"
        else:
            reply = "I'm sorry, I didn't catch that. Could you please repeat?"
        return RecoveryResult(reply=reply)

    def _recover_llm(self, case: "CaseState", attempt: int) -> RecoveryResult:
        """LLM failed — use deterministic fallback reply."""
        from voice_agent import _generate_human_fallback_reply
        reply = _generate_human_fallback_reply(case.last_user_text or "", case)
        return RecoveryResult(reply=reply)

    def _recover_tool(self, case: "CaseState", attempt: int) -> RecoveryResult:
        """Tool failed — retry once, then escalate."""
        if attempt == 1:
            # First failure — ask to retry
            reply = "I'm checking that for you. Please give me just a moment."
            return RecoveryResult(reply=reply)
        else:
            # Second failure — set tool_failed flag and escalate
            case.tool_failed = True
            langs = getattr(case, 'language', [])
            uses_hindi = any(l in ('hi', 'hi-IN', 'hi-en') for l in langs)
            if uses_hindi:
                reply = "Maafi chahta hoon, abhi verification mein dikkat aa rahi hai. Main aapko specialist se connect kar raha hoon."
            else:
                reply = "I'm sorry, I'm having trouble verifying that right now. Let me connect you with a specialist."
            return RecoveryResult(reply=reply, should_escalate=True)

    def _recover_tts(self, case: "CaseState") -> RecoveryResult:
        """TTS failed — not applicable in Agora mode, log and continue."""
        logger.info("[PRISM][ErrorRecovery] TTS failure — Agora handles TTS, this is a no-op")
        return RecoveryResult(reply="")

    def _recover_agora(self, case: "CaseState") -> RecoveryResult:
        """Agora failure — signal reconnect."""
        case.connection_state = "RECONNECTING"
        return RecoveryResult(reply="", reset_state=True)

    def _recover_unknown(self, case: "CaseState") -> RecoveryResult:
        """Unknown failure — safe reset."""
        return RecoveryResult(
            reply="I encountered an unexpected issue. Let me try again.",
            reset_state=True
        )


# Module-level singleton
_engine = ErrorRecoveryEngine()


def recover(failure_type: FailureType, case: "CaseState", attempt: int = 1) -> RecoveryResult:
    return _engine.recover(failure_type, case, attempt)
