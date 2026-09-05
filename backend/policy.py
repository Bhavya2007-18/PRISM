"""
PRISM Deterministic Policy Gate.

PRISM's headline differentiator: the LLM is NOT given unrestricted authority
over escalation. The LLM *proposes* an action (e.g. escalate_to_human); this
deterministic policy *validates* that proposal against the case's verified
facts and confidence before it can take effect:

    LLM proposes escalation  ->  Deterministic policy validates  ->  ESCALATE | CONTINUE

The policy reuses the existing decision engine (decision.py) and confidence
engine (confidence.py) so there is a single source of truth for the question
"is this case genuinely escalation-worthy?". The LLM cannot escalate a case the
policy considers resolvable, and the policy can escalate a case even when the
LLM forgot to (e.g. an unresolved duplicate-charge risk after a tool lookup).
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from decision import decide, Action
from confidence import get_confidence_report

if TYPE_CHECKING:
    from context import CaseState


@dataclass
class PolicyDecision:
    decision: str                 # "ESCALATE" | "CONTINUE"
    approved: bool                # True when an escalation is authorized
    reason: str                   # human-readable rationale
    llm_proposed: bool            # did the LLM propose escalation this turn?
    checks: dict = field(default_factory=dict)   # transparency: the individual gate checks


def _gate_checks(case: "CaseState") -> dict:
    """Snapshot of the signals the gate reasons over (surfaced to logs + UI)."""
    report = get_confidence_report(case)
    action, _ = decide(case)
    return {
        "deterministic_action": action.value,
        "confidence_score": report.display_score,
        "confidence_label": report.overall_label,
        "confidence_sufficient": report.overall_label == "CONFIDENT",
        "blocking_fields": list(report.blocking_fields),
        "user_requested_human": bool(case.user_requested_human),
        "tool_failed": bool(case.tool_failed),
        "has_contradiction": bool(case.has_contradiction),
    }


def evaluate_escalation(case: "CaseState", llm_proposed: bool, proposed_reason: str = "") -> PolicyDecision:
    """
    Validate a (possibly LLM-proposed) escalation against deterministic policy.

    The deterministic decision engine already encodes every escalation trigger:
      - user explicitly requested a human
      - contradictory information
      - verification tool failed
      - post-tool the duplicate-charge status is still UNKNOWN (the canonical
        "money taken, order not confirmed" ambiguity)

    So the gate is simple and auditable:
      * If decide(case) == ESCALATE -> authorize escalation (ESCALATE).
      * Otherwise the case is NOT escalation-eligible. If the LLM proposed
        escalation anyway, the policy OVERRIDES it -> CONTINUE.
    """
    checks = _gate_checks(case)
    action, det_reason = decide(case)

    if action == Action.ESCALATE:
        return PolicyDecision(
            decision="ESCALATE",
            approved=True,
            reason=det_reason,
            llm_proposed=llm_proposed,
            checks=checks,
        )

    if llm_proposed:
        reason = (
            f"LLM proposed escalation ({proposed_reason or 'no reason given'}), but the "
            f"deterministic policy finds the case is not escalation-eligible "
            f"(next action: {action.value}, confidence: {checks['confidence_label']}). "
            f"Continuing to assist."
        )
    else:
        reason = f"No escalation required (next action: {action.value})."

    return PolicyDecision(
        decision="CONTINUE",
        approved=False,
        reason=reason,
        llm_proposed=llm_proposed,
        checks=checks,
    )
