# ENGINE: IntelligenceEngine
"""
PRISM Response Generator

Post-processes LLM replies before they are sent to the user.
Provides sentence segmentation for TTS streaming.
"""
import re
import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState
    from policy import PolicyDecision

logger = logging.getLogger(__name__)

# Maximum response length in characters before truncation
MAX_RESPONSE_LENGTH = 500

# Languages that need different sentence boundary detection
SENTENCE_END_PATTERN = re.compile(r'(?<=[.!?।])\s+')


class ResponseGenerator:
    """
    Post-processes and validates LLM responses before sending to user.
    """

    def generate_response(self, reply_text: str, case: "CaseState", policy=None) -> str:
        """
        Post-process a raw LLM reply:
        1. Trim whitespace
        2. Enforce length limit
        3. Language match check (warn only)
        4. Return cleaned text
        """
        if not reply_text:
            return self._safe_fallback(case)

        # Trim
        text = reply_text.strip()

        # Length limit
        if len(text) > MAX_RESPONSE_LENGTH:
            # Truncate at last sentence boundary before the limit
            truncated = text[:MAX_RESPONSE_LENGTH]
            last_period = max(
                truncated.rfind("."),
                truncated.rfind("!"),
                truncated.rfind("?"),
            )
            if last_period > MAX_RESPONSE_LENGTH // 2:
                text = truncated[:last_period + 1]
            else:
                text = truncated + "..."

        # Language match check (non-fatal warning)
        self._check_language_match(text, case)

        return text

    def sentence_segment(self, text: str) -> List[str]:
        """
        Split text into sentences for TTS streaming.
        Each sentence can be streamed as a separate audio chunk.
        """
        if not text:
            return []

        # Split on sentence-ending punctuation followed by whitespace
        # Handle both English and Hindi (।)
        parts = SENTENCE_END_PATTERN.split(text)
        sentences = []
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)

        # Ensure punctuation is preserved at sentence end
        result = []
        for s in sentences:
            if s and not s[-1] in '.!?।':
                s = s + '.'
            result.append(s)

        return result if result else [text]

    def _check_language_match(self, text: str, case: "CaseState") -> None:
        """Warn if response language doesn't match the case language."""
        case_langs = getattr(case, 'language', [])
        if not case_langs:
            return

        # Very basic check: if user spoke Hindi but response has no Hindi chars
        has_hindi_user = any(l in ("hi", "hi-IN", "hi-en") for l in case_langs)
        # Hindi Unicode range
        has_hindi_response = bool(re.search(r'[\u0900-\u097F]', text))

        if has_hindi_user and not has_hindi_response:
            # Log warning — don't fail, LLM may intentionally respond in English
            logger.debug(f"[ResponseGenerator] Language hint: user speaks Hindi but response is in English")

    def _safe_fallback(self, case: "CaseState") -> str:
        """Return a safe fallback when reply_text is empty."""
        if getattr(case, 'escalated', False):
            return "I'm connecting you to a specialist who can help further."
        return "I'm here to help. Could you please share more details about your issue?"


# Module-level singleton
_generator = ResponseGenerator()


def generate_response(reply_text: str, case, policy=None) -> str:
    """Convenience function."""
    return _generator.generate_response(reply_text, case, policy)


def sentence_segment(text: str) -> List[str]:
    """Convenience function for sentence segmentation."""
    return _generator.sentence_segment(text)
