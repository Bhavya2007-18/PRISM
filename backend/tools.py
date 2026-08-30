"""
PRISM Tools — mock external APIs and tool schemas.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState


# ── OpenAI function schema ────────────────────────────────────────────

CHECK_TRANSACTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_transaction",
        "description": (
            "Look up a payment transaction by its transaction ID. "
            "Returns the transaction amount, payment status, and order confirmation status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "The transaction ID to look up, e.g. TX48291"
                }
            },
            "required": ["transaction_id"]
        }
    }
}

ALL_TOOLS = [CHECK_TRANSACTION_SCHEMA]


# ── Mock transaction database ─────────────────────────────────────────

MOCK_TRANSACTIONS = {
    "TX48291": {
        "transaction_id": "TX48291",
        "amount": 1499,
        "status": "SUCCESS",
        "order_status": "NOT_CONFIRMED",
        "timestamp": "2026-08-30T10:23:41Z",
        "merchant": "ShopEasy India"
    },
    "TX00001": {
        "transaction_id": "TX00001",
        "amount": 599,
        "status": "FAILED",
        "order_status": "NOT_CONFIRMED",
        "timestamp": "2026-08-30T09:10:00Z",
        "merchant": "QuickMart"
    },
    "TX99999": {
        "transaction_id": "TX99999",
        "amount": 2999,
        "status": "SUCCESS",
        "order_status": "CONFIRMED",
        "timestamp": "2026-08-30T08:55:00Z",
        "merchant": "TechBazaar"
    },
}


def check_transaction(transaction_id: str) -> dict:
    """Mock transaction lookup. Returns transaction details or error."""
    tx = MOCK_TRANSACTIONS.get(transaction_id.strip().upper())
    if tx:
        return {"success": True, **tx}
    return {
        "success": False,
        "error": "transaction_not_found",
        "message": f"No transaction found with ID {transaction_id}"
    }


def create_escalation_ticket(case: "CaseState", reason: str) -> dict:
    """Create a support ticket for human agent escalation.

    Returned keys are **fixed and guaranteed** — the same shape regardless
    of intent/state. Used by the frontend Agent dashboard.
    """
    from confidence import get_confidence_report
    report = get_confidence_report(case)

    ticket_id = case.case_id
    intent = case.intent or "general_issue"
    issue = _describe_issue(case)
    issue_summary = _generate_summary(case)

    language = case.language or ["English"]
    if not isinstance(language, list):
        language = [str(language)]
    language = [lang for lang in language if lang] or ["English"]

    verified_list = list(case.verified) if isinstance(case.verified, list) else []
    unverified_list = list(case.unverified) if isinstance(case.unverified, list) else []
    if case.duplicate_charge == "UNKNOWN" and "duplicate_charge" not in unverified_list:
        unverified_list.append("duplicate_charge")

    # Honest display values — None → None in the JSON, never "Unknown" strings
    # that would silently make the UI confidently wrong.
    ticket = {
        # ── Identity ─────────────────────────────────────────────────
        "ticket_id": ticket_id,
        "case_id": ticket_id,
        "created_at": datetime.utcnow().isoformat(),
        "status": "ESCALATED",
        "taken_over": False,
        # ── Semantic (for cards / intel) ─────────────────────────────
        "intent": intent,
        "issue": issue,
        "issue_summary": issue_summary,
        "reason_for_escalation": reason,
        "language": language,
        # ── Concrete / verified fields ───────────────────────────────
        "transaction_id": case.transaction_id,
        "amount": case.amount,
        "payment_status": case.payment_status,
        "order_status": case.order_status,
        "duplicate_charge": case.duplicate_charge,
        # ── Confidence ───────────────────────────────────────────────
        "confidence_fields": {k: v.value for k, v in report.fields.items()},
        "confidence_display": report.display_score,
        "confidence_label": report.overall_label,
        # ── Lists ────────────────────────────────────────────────────
        "verified": verified_list,
        "unverified": unverified_list,
        # ── For the dashboard summary card ───────────────────────────
        "summary": issue_summary,
        # ── Conversation (useful for "take over" context) ────────────
        "conversation_history": case.conversation_history,
    }

    return ticket


def _describe_issue(case: "CaseState") -> str:
    intent = case.intent or "general_issue"
    if intent == "payment_issue":
        if case.payment_status == "SUCCESS" and case.order_status == "NOT_CONFIRMED":
            return "Payment deducted but order not confirmed"
        if case.payment_status == "SUCCESS" and case.duplicate_charge == "UNKNOWN":
            return "Payment succeeded — possible duplicate charge"
        if case.payment_status == "FAILED":
            return "Payment failed"
        if case.payment_status == "SUCCESS" and case.order_status in (None, "UNKNOWN"):
            return "Payment deducted, order status unclear"
        return "Payment issue"
    if intent == "refund_request":
        return "Customer requesting a refund"
    if intent == "delivery_issue":
        return "Delivery delay or non-delivery"
    if intent == "general_issue":
        return "Customer required general support"
    return intent.replace("_", " ").strip().title()


def _generate_summary(case: "CaseState") -> str:
    parts = []
    intent = case.intent or "general_issue"
    if intent == "payment_issue":
        parts.append("Customer reports a payment issue.")
    elif intent == "refund_request":
        parts.append("Customer is requesting a refund.")
    elif intent == "delivery_issue":
        parts.append("Customer reports a delivery issue.")
    else:
        parts.append("Customer raised a general support issue.")

    if case.transaction_id:
        bits = [f"Transaction {case.transaction_id}"]
        if case.amount is not None:
            try:
                bits.append(f"of \u20b9{int(float(case.amount))}")
            except (TypeError, ValueError):
                pass
        if case.payment_status:
            bits.append(f"→ status: {case.payment_status}.")
        parts.append(" ".join(bits))
    if case.order_status == "NOT_CONFIRMED":
        parts.append("Order has not been confirmed.")
    elif case.order_status:
        parts.append(f"Order status: {case.order_status}.")
    if case.duplicate_charge == "UNKNOWN":
        parts.append("Duplicate charge status could not be determined with confidence.")
    elif case.duplicate_charge == "YES":
        parts.append("System indicates a possible duplicate charge.")

    summary = " ".join(p for p in parts if p)
    return summary or "Customer support case requiring human review."
