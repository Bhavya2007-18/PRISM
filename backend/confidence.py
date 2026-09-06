# ENGINE: PolicyEngine (confidence scoring layer)
"""
PRISM Confidence Engine — numeric per-field confidence scoring.

Replaces the three-bucket FieldConfidence system with per-field float scores
(0.0-1.0) and defined resolution thresholds.

Thresholds:
    RESOLVE_THRESHOLD   = 0.85  — AI can resolve autonomously
    CONTINUE_THRESHOLD  = 0.60  — AI should keep gathering information
    ESCALATE_BELOW      = 0.60  — below this, policy may escalate
"""
from dataclasses import dataclass
from typing import Dict

# ── Confidence thresholds ─────────────────────────────────────────────────
RESOLVE_THRESHOLD  = 0.85
CONTINUE_THRESHOLD = 0.60
ESCALATE_BELOW     = 0.60

# ── Per-field weights for overall score ──────────────────────────────────
FIELD_WEIGHTS = {
    "intent":       0.20,
    "transaction":  0.40,
    "resolution":   0.40,
}


@dataclass
class ConfidenceReport:
    fields: Dict[str, float]   # field_name -> 0.0-1.0 score
    display_score: int          # 0-100, for UI only
    overall_label: str          # "CONFIDENT" / "UNCERTAIN" / "INSUFFICIENT"
    blocking_fields: list       # fields with score < 0.3


def _intent_confidence(case) -> float:
    if not case.intent:
        return 0.0
    if "intent" in getattr(case, 'verified', []):
        return 0.95
    return 0.75


def _transaction_confidence(case) -> float:
    if not case.transaction_id:
        return 0.0
    verified = getattr(case, 'verified', [])
    if "payment_status" in verified:
        if case.duplicate_charge == "UNKNOWN":
            return 0.45
        elif case.duplicate_charge == "NO":
            return 0.97
        else:
            return 0.30
    if "transaction_id" in verified:
        return 0.60
    return 0.30


def _resolution_confidence(case) -> float:
    verified = getattr(case, 'verified', [])
    required_fields = ["transaction_id", "payment_status", "order_status"]
    verified_required = sum(1 for f in required_fields if f in verified)
    if not case.payment_status:
        return 0.10
    if case.duplicate_charge == "UNKNOWN" and case.payment_status == "SUCCESS":
        return 0.40
    base = verified_required / len(required_fields)
    if case.order_status == "CONFIRMED":
        base = min(1.0, base + 0.15)
    if getattr(case, 'tool_failed', False):
        base = max(0.0, base - 0.30)
    return base


def get_confidence_report(case) -> ConfidenceReport:
    """Compute numeric per-field confidence report. Fully deterministic, no LLM."""
    intent_score      = _intent_confidence(case)
    transaction_score = _transaction_confidence(case)
    resolution_score  = _resolution_confidence(case)

    overall = (
        intent_score      * FIELD_WEIGHTS["intent"] +
        transaction_score * FIELD_WEIGHTS["transaction"] +
        resolution_score  * FIELD_WEIGHTS["resolution"]
    )
    overall = max(0.0, min(1.0, overall))

    fields: Dict[str, float] = {
        "intent":      intent_score,
        "transaction": transaction_score,
        "resolution":  resolution_score,
    }
    blocking = [f for f, score in fields.items() if score < 0.30]

    if overall >= RESOLVE_THRESHOLD:
        label = "CONFIDENT"
    elif overall >= CONTINUE_THRESHOLD:
        label = "UNCERTAIN"
    else:
        label = "INSUFFICIENT"

    return ConfidenceReport(
        fields=fields,
        display_score=int(overall * 100),
        overall_label=label,
        blocking_fields=blocking,
    )
