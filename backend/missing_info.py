# ENGINE: IntelligenceEngine
"""
PRISM Missing Information Engine

Determines what critical information is still needed to resolve a case.
Replaces inline missing-info detection in decision.py.
Provides bilingual question templates (English + Hindi).
"""
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState


@dataclass
class MissingField:
    field_name: str
    priority: int           # 1 = highest
    question_en: str        # English question template
    question_hi: str        # Hindi question template


# Ordered list of fields that must be known before resolution
REQUIRED_FIELDS: List[MissingField] = [
    MissingField(
        field_name="intent",
        priority=1,
        question_en="Could you please describe the issue you're facing?",
        question_hi="Kya aap mujhe apni samasya bata sakte hain?",
    ),
    MissingField(
        field_name="transaction_id",
        priority=2,
        question_en="Could you please share the Transaction ID or order number?",
        question_hi="Kya aap apna Transaction ID ya order number share kar sakte hain?",
    ),
]


class MissingInfoEngine:
    """
    Determines which critical fields are missing for case resolution.
    Returns prioritised missing fields with bilingual question templates.
    """

    def get_missing_fields(self, case: "CaseState") -> List[MissingField]:
        """
        Return list of missing fields sorted by priority (1 = most urgent).
        Only returns fields that are genuinely absent from the case.
        """
        missing: List[MissingField] = []

        for field in REQUIRED_FIELDS:
            value = getattr(case, field.field_name, None)
            if not value:
                missing.append(field)

        # Sort by priority ascending (1 first)
        return sorted(missing, key=lambda f: f.priority)

    def get_next_question(self, case: "CaseState", language: str = "en") -> Optional[str]:
        """
        Return the next question to ask, in the appropriate language.
        Returns None if no information is missing.
        """
        missing = self.get_missing_fields(case)
        if not missing:
            return None

        field = missing[0]  # highest priority
        if language in ("hi", "hi-IN", "hi-en"):
            return field.question_hi
        return field.question_en

    def has_missing_critical_info(self, case: "CaseState") -> bool:
        """True if any critical field is missing."""
        return len(self.get_missing_fields(case)) > 0
