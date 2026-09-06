# ENGINE: PolicyEngine
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

import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from context import CaseState


@dataclass
class PolicyDecision:
    decision: str                 # "ESCALATE" | "CONTINUE"
    approved: bool                # True when an escalation is authorized
    reason: str                   # human-readable rationale
    llm_proposed: bool            # did the LLM propose escalation this turn?
    checks: dict = field(default_factory=dict)   # transparency: the individual gate checks
    approved_actions: list = field(default_factory=list)   # NEW
    denied_actions: list = field(default_factory=list)     # NEW
    modification_reason: str = ""                           # NEW

    def get_policy_summary(self) -> dict:
        """Safe representation for frontend (no internal details)."""
        return {
            "decision": self.decision,
            "approved": self.approved,
            "reason": self.reason,
        }


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

    # New rule: user explicitly requested human → ALWAYS escalate
    # (This duplicates the decide() check but makes the policy gate authoritative)
    if case.user_requested_human and not case.escalated:
        logger.info(f"[PRISM][PolicyEngine][AUDIT] ESCALATE: user_requested_human=True channel={case.channel}")
        return PolicyDecision(
            decision="ESCALATE",
            approved=True,
            reason="Customer explicitly requested human assistance",
            llm_proposed=llm_proposed,
            checks=checks,
            approved_actions=["escalate_to_human"],
        )

    if action == Action.ESCALATE:
        logger.info(
            f"[PRISM][PolicyEngine][AUDIT] ESCALATE approved llm_proposed={llm_proposed} "
            f"reason={det_reason[:80]} channel={case.channel}"
        )
        return PolicyDecision(
            decision="ESCALATE",
            approved=True,
            reason=det_reason,
            llm_proposed=llm_proposed,
            checks=checks,
            approved_actions=["escalate_to_human"],
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

    logger.info(
        f"[PRISM][PolicyEngine][AUDIT] decision={action.value} "
        f"llm_proposed={llm_proposed} confidence={checks.get('confidence_score')} "
        f"channel={case.channel}"
    )

    denied = ["escalate_to_human"] if llm_proposed else []
    return PolicyDecision(
        decision="CONTINUE",
        approved=False,
        reason=reason,
        llm_proposed=llm_proposed,
        checks=checks,
        denied_actions=denied,
        modification_reason=reason if llm_proposed else "",
    )
