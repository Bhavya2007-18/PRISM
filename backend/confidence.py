"""
PRISM Confidence Engine — label-based, honest, deterministic.
"""
from enum import Enum
from dataclasses import dataclass


class FieldConfidence(str, Enum):
    HIGH = "HIGH"                    # Present AND verified by external tool
    LOW = "LOW"                      # Stated by user, not tool-verified
    CRITICAL_UNKNOWN = "CRITICAL_UNKNOWN"  # Required field, absent or unresolvable


# Display score mapping (used only for UI)
CONFIDENCE_DISPLAY_SCORE = {
    FieldConfidence.HIGH: 0.95,
    FieldConfidence.LOW: 0.55,
    FieldConfidence.CRITICAL_UNKNOWN: 0.41,
}

CONFIDENCE_THRESHOLD = 0.60


@dataclass
class ConfidenceReport:
    fields: dict[str, FieldConfidence]
    display_score: int          # 0–100, for UI only
    overall_label: str          # "CONFIDENT" / "UNCERTAIN" / "INSUFFICIENT"
    blocking_fields: list[str]  # fields that prevent resolution


def get_confidence_report(case) -> ConfidenceReport:
    """
    Deterministic confidence labelling based on case state.
    No LLM involved.
    """
    from context import CaseState

    fields: dict[str, FieldConfidence] = {}

    # Intent
    if case.intent:
        fields["intent"] = FieldConfidence.HIGH
    else:
        fields["intent"] = FieldConfidence.CRITICAL_UNKNOWN

    # Transaction ID
    if case.transaction_id:
        if "transaction_id" in case.verified:
            fields["transaction_id"] = FieldConfidence.HIGH
        else:
            fields["transaction_id"] = FieldConfidence.LOW
    else:
        fields["transaction_id"] = FieldConfidence.CRITICAL_UNKNOWN

    # Amount
    if case.amount is not None:
        if "amount" in case.verified:
            fields["amount"] = FieldConfidence.HIGH
        else:
            fields["amount"] = FieldConfidence.LOW
    else:
        fields["amount"] = FieldConfidence.CRITICAL_UNKNOWN

    # Payment status
    if case.payment_status:
        if "payment_status" in case.verified:
            fields["payment_status"] = FieldConfidence.HIGH
        else:
            fields["payment_status"] = FieldConfidence.LOW
    else:
        fields["payment_status"] = FieldConfidence.CRITICAL_UNKNOWN

    # Duplicate charge — special case
    if case.duplicate_charge == "UNKNOWN":
        fields["duplicate_charge"] = FieldConfidence.CRITICAL_UNKNOWN
    elif case.duplicate_charge in ("YES", "NO") and "duplicate_charge" in case.verified:
        fields["duplicate_charge"] = FieldConfidence.HIGH
    else:
        fields["duplicate_charge"] = FieldConfidence.LOW

    # Compute display score: weighted average
    score_values = [CONFIDENCE_DISPLAY_SCORE[v] for v in fields.values()]
    raw_score = sum(score_values) / len(score_values) if score_values else 0.0

    # Critical unknowns drag score down hard
    critical_count = sum(1 for v in fields.values() if v == FieldConfidence.CRITICAL_UNKNOWN)
    penalty = critical_count * 0.08
    final_score = max(0.0, raw_score - penalty)
    display_score = int(final_score * 100)

    # Overall label
    if final_score >= CONFIDENCE_THRESHOLD:
        overall = "CONFIDENT"
    elif final_score >= 0.40:
        overall = "UNCERTAIN"
    else:
        overall = "INSUFFICIENT"

    blocking = [k for k, v in fields.items() if v == FieldConfidence.CRITICAL_UNKNOWN]

    return ConfidenceReport(
        fields=fields,
        display_score=display_score,
        overall_label=overall,
        blocking_fields=blocking,
    )
