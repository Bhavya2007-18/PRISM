# ENGINE: IntelligenceEngine
"""
PRISM Planner — LLM planning layer.

Generates a structured plan from intent + case state.
The plan is stored on CaseState.current_plan and exposed (safely) to the frontend
via _build_ai_state() as a high-level plan_summary.

IMPORTANT: Plan steps are high-level action names only.
Never expose chain-of-thought, internal reasoning, or LLM prompts.
"""
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState


@dataclass
class Plan:
    goal: str
    steps: List[str]
    current_step: int = 0
    status: str = "in_progress"  # in_progress / completed / failed

    @property
    def current_step_name(self) -> Optional[str]:
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    @property
    def is_complete(self) -> bool:
        return self.status == "completed" or self.current_step >= len(self.steps)

    def advance(self) -> None:
        """Move to the next step."""
        self.current_step += 1
        if self.current_step >= len(self.steps):
            self.status = "completed"

    def truncate_to_current(self) -> None:
        """On interruption — keep only completed steps."""
        self.steps = self.steps[:self.current_step]

    def to_safe_summary(self) -> dict:
        """Safe representation for frontend (no internal details)."""
        return {
            "goal": self.goal,
            "current_step": self.current_step_name,
            "total_steps": len(self.steps),
            "progress": self.current_step,
            "status": self.status,
        }


# Intent → plan template mapping
_PLAN_TEMPLATES = {
    "payment_issue": Plan(
        goal="resolve_payment_issue",
        steps=["identify_transaction", "check_transaction", "verify_result", "determine_resolution"],
    ),
    "refund_request": Plan(
        goal="process_refund_request",
        steps=["verify_eligibility", "check_transaction", "verify_result", "process_refund"],
    ),
    "delivery_issue": Plan(
        goal="resolve_delivery_issue",
        steps=["get_order_details", "check_tracking", "determine_resolution"],
    ),
    "order_status": Plan(
        goal="provide_order_status",
        steps=["get_order_details", "check_status", "provide_update"],
    ),
    "account_issue": Plan(
        goal="resolve_account_issue",
        steps=["verify_identity", "check_account_status", "determine_resolution"],
    ),
    "general_inquiry": Plan(
        goal="answer_inquiry",
        steps=["understand_question", "search_knowledge", "provide_answer"],
    ),
}


class Planner:
    """
    Generates a structured plan based on intent and case state.
    """

    def generate_plan(self, case: "CaseState") -> Optional[Plan]:
        """
        Generate a plan for the given case. Returns None if no plan applicable.
        Uses intent to select the appropriate template.
        """
        intent = case.intent or "general_inquiry"
        template = _PLAN_TEMPLATES.get(intent, _PLAN_TEMPLATES["general_inquiry"])

        # Return a fresh copy of the plan (not the shared template)
        return Plan(
            goal=template.goal,
            steps=list(template.steps),
            current_step=0,
            status="in_progress",
        )

    def ensure_plan(self, case: "CaseState") -> Optional[Plan]:
        """
        Return the existing plan on the case, or generate a new one.
        Sets case.planning = True while plan is being generated.
        """
        existing = getattr(case, "current_plan", None)
        if existing and not existing.is_complete:
            return existing

        if case.intent:
            plan = self.generate_plan(case)
            case.current_plan = plan
            return plan

        return None
