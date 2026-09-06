# ENGINE: ActionEngine
"""
PRISM Verification Engine

Verifies tool results before they are used for responses or escalation decisions.
Called after every tool execution:

    Tool runs
        → VerificationEngine.verify_tool_result()
        → Updates case.verification_status
        → Sets case.verifying = False
        → Triggers VERIFYING state while running
"""
import logging
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    tool_name: str
    passed: bool
    issues: list
    verified_fields: list


class VerificationEngine:
    """
    Verifies tool results for correctness and completeness.
    Prevents silent failures from propagating to users.
    """

    VALID_PAYMENT_STATUSES = {"SUCCESS", "FAILED", "PENDING", "REFUNDED"}
    VALID_ORDER_STATUSES   = {"CONFIRMED", "NOT_CONFIRMED", "CANCELLED", "PROCESSING", "SHIPPED"}

    def verify_tool_result(self, tool_name: str, result: dict, case: "CaseState") -> VerificationResult:
        """
        Verify a tool result. Updates case verification_status.
        Returns VerificationResult indicating pass/fail and issues found.
        """
        case.verifying = True
        issues = []
        verified_fields = []

        try:
            if tool_name == "check_transaction":
                result_obj = self._verify_check_transaction(result, case, issues, verified_fields)
            elif tool_name == "get_order":
                result_obj = self._verify_get_order(result, issues, verified_fields)
            elif tool_name == "refund_status":
                result_obj = self._verify_refund_status(result, issues, verified_fields)
            else:
                # Unknown tool — basic success check
                if not result.get("success", True):
                    issues.append(f"Tool {tool_name} returned failure")
                result_obj = VerificationResult(
                    tool_name=tool_name,
                    passed=len(issues) == 0,
                    issues=issues,
                    verified_fields=verified_fields,
                )

            # Update case verification status
            if not hasattr(case, 'verification_status') or not isinstance(getattr(case, 'verification_status', None), dict):
                case.verification_status = {}
            case.verification_status[tool_name] = {
                "passed": result_obj.passed,
                "issues": result_obj.issues,
            }

            if result_obj.passed:
                logger.info(f"[PRISM][VerificationEngine] {tool_name} VERIFIED fields={verified_fields}")
            else:
                logger.warning(f"[PRISM][VerificationEngine] {tool_name} FAILED issues={issues}")

            return result_obj

        finally:
            case.verifying = False

    def _verify_check_transaction(self, result: dict, case: "CaseState", issues: list, verified: list) -> VerificationResult:
        """Verify check_transaction result."""
        if not result.get("success"):
            issues.append("Transaction lookup returned failure")
            return VerificationResult("check_transaction", False, issues, verified)

        # Amount must be a positive number (not None→0.0 silent failure)
        amount = result.get("amount")
        if amount is None:
            issues.append("Amount is None — possible silent failure")
        elif not isinstance(amount, (int, float)) or amount < 0:
            issues.append(f"Invalid amount: {amount}")
        else:
            verified.append("amount")

        # Payment status must be a known value
        status = result.get("status")
        if status not in self.VALID_PAYMENT_STATUSES:
            issues.append(f"Unknown payment status: {status}")
        else:
            verified.append("payment_status")

        # Order status must be a known value
        order_status = result.get("order_status")
        if order_status and order_status not in self.VALID_ORDER_STATUSES:
            issues.append(f"Unknown order status: {order_status}")
        elif order_status:
            verified.append("order_status")

        # Transaction ID must match what was requested
        tx_id = result.get("transaction_id")
        if tx_id and case.transaction_id and tx_id.upper() != case.transaction_id.upper():
            issues.append(f"Transaction ID mismatch: requested {case.transaction_id}, got {tx_id}")
        else:
            verified.append("transaction_id")

        return VerificationResult(
            tool_name="check_transaction",
            passed=len(issues) == 0,
            issues=issues,
            verified_fields=verified,
        )

    def _verify_get_order(self, result: dict, issues: list, verified: list) -> VerificationResult:
        if result.get("success"):
            verified.append("order_status")
        return VerificationResult("get_order", len(issues) == 0, issues, verified)

    def _verify_refund_status(self, result: dict, issues: list, verified: list) -> VerificationResult:
        if result.get("success"):
            verified.append("refund_status")
        return VerificationResult("refund_status", len(issues) == 0, issues, verified)


# Module-level singleton
_engine = VerificationEngine()


def verify_tool_result(tool_name: str, result: dict, case: "CaseState") -> VerificationResult:
    """Convenience function for single-call verification."""
    return _engine.verify_tool_result(tool_name, result, case)
