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
    """Create a support ticket for human agent escalation."""
    from confidence import get_confidence_report
    report = get_confidence_report(case)

    ticket_id = case.case_id  # reuse the PRISM-XXXX id

    summary = {
        "ticket_id": ticket_id,
        "case_id": ticket_id,
        "created_at": datetime.utcnow().isoformat(),
        "status": "ESCALATED",
        "issue": _describe_issue(case),
        "language": case.language or ["Unknown"],
        "transaction_id": case.transaction_id,
        "amount": case.amount,
        "payment_status": case.payment_status,
        "order_status": case.order_status,
        "duplicate_charge": case.duplicate_charge,
        "verified": case.verified,
        "unverified": case.unverified + (["duplicate_charge"] if case.duplicate_charge == "UNKNOWN" else []),
        "confidence_fields": {k: v.value for k, v in report.fields.items()},
        "confidence_display": report.display_score,
        "confidence_label": report.overall_label,
        "reason_for_escalation": reason,
        "summary": _generate_summary(case),
    }

    return summary


def _describe_issue(case: "CaseState") -> str:
    if case.intent == "payment_issue":
        if case.payment_status == "SUCCESS" and case.order_status == "NOT_CONFIRMED":
            return "Payment deducted but order not confirmed"
        elif case.payment_status == "FAILED":
            return "Payment failed"
    return case.intent or "Unknown issue"


def _generate_summary(case: "CaseState") -> str:
    parts = []
    if case.intent == "payment_issue":
        parts.append("Customer reports a payment issue.")
    if case.transaction_id:
        parts.append(f"Transaction {case.transaction_id}")
        if case.amount:
            parts.append(f"of \u20b9{int(case.amount)}")
        if case.payment_status:
            parts.append(f"shows status: {case.payment_status}.")
    if case.order_status == "NOT_CONFIRMED":
        parts.append("Order has not been confirmed.")
    if case.duplicate_charge == "UNKNOWN":
        parts.append("Duplicate charge status could not be determined.")
    return " ".join(parts) if parts else "Payment support case requiring human review."
