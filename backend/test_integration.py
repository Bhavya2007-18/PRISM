"""
PRISM Integration Test — verifies the complete demo flow end-to-end.
Run from: d:\WORK AND STUDY\PRISM\backend
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from context import get_or_create_case, update_case_from_extract, escalated_cases, cases
from confidence import get_confidence_report, FieldConfidence
from decision import decide, Action
from tools import check_transaction, create_escalation_ticket

print("=" * 60)
print("PRISM Integration Test")
print("=" * 60)

# ── Test 1: Fresh case ───────────────────────────────────────────────
print("\n[1] Fresh case — should ask for intent")
case = get_or_create_case("test-channel")
action, reason = decide(case)
assert action == Action.ASK, f"Expected ASK, got {action}"
assert "missing_intent" in reason
print(f"    ✓ {action} ({reason})")

# ── Test 2: Intent extracted ─────────────────────────────────────────
print("\n[2] Intent set — should ask for transaction ID")
update_case_from_extract("test-channel", {
    "intent": "payment_issue",
    "language": ["Hindi", "English"],
    "transaction_id": None,
    "amount": None,
    "user_requested_human": False,
    "has_contradiction": False,
})
action, reason = decide(case)
assert action == Action.ASK, f"Expected ASK, got {action}"
assert "missing_transaction_id" in reason
print(f"    ✓ {action} ({reason})")
print(f"    ✓ Language detected: {case.language}")

# ── Test 3: Transaction ID extracted ────────────────────────────────
print("\n[3] Transaction ID given — should call tool")
update_case_from_extract("test-channel", {
    "intent": None,  # already set, should not overwrite
    "language": [],
    "transaction_id": "TX48291",
    "amount": None,
    "user_requested_human": False,
    "has_contradiction": False,
})
action, reason = decide(case)
assert action == Action.TOOL_CALL, f"Expected TOOL_CALL, got {action}"
assert "check_transaction" in reason
print(f"    ✓ {action} ({reason})")
print(f"    ✓ TX ID: {case.transaction_id}")

# ── Test 4: Tool call execution ──────────────────────────────────────
print("\n[4] Tool call — check_transaction(TX48291)")
result = check_transaction("TX48291")
assert result["success"] is True
assert result["amount"] == 1499
assert result["status"] == "SUCCESS"
assert result["order_status"] == "NOT_CONFIRMED"
print(f"    ✓ Tool returned: amount={result['amount']}, status={result['status']}, order={result['order_status']}")

# ── Test 5: Update case with tool result ─────────────────────────────
print("\n[5] Case state after tool result")
case.payment_status = result["status"]
case.order_status = result["order_status"]
case.amount = float(result["amount"])
for field in ["payment_status", "order_status", "amount", "transaction_id"]:
    if field not in case.verified:
        case.verified.append(field)
case.unverified = [f for f in case.unverified if f not in case.verified]
print(f"    ✓ Verified fields: {case.verified}")
print(f"    ✓ Unverified fields: {case.unverified}")

# ── Test 6: Decision engine — should escalate ────────────────────────
print("\n[6] Post-tool decision — should escalate (duplicate_charge=UNKNOWN)")
action, reason = decide(case)
assert action == Action.ESCALATE, f"Expected ESCALATE, got {action}"
assert "duplicate charge" in reason.lower() or "confidence" in reason.lower()
print(f"    ✓ {action}: {reason}")

# ── Test 7: Confidence report ────────────────────────────────────────
print("\n[7] Confidence report")
report = get_confidence_report(case)
assert report.fields["payment_status"] == FieldConfidence.HIGH
assert report.fields["transaction_id"] == FieldConfidence.HIGH
assert report.fields["amount"] == FieldConfidence.HIGH
assert report.fields["duplicate_charge"] == FieldConfidence.CRITICAL_UNKNOWN
# With 4 HIGH fields and 1 CRITICAL_UNKNOWN, score is ~76 — still escalates
# because duplicate_charge == "UNKNOWN" is an explicit decision-engine trigger
assert "duplicate_charge" in report.blocking_fields, "duplicate_charge should be a blocking field"
print(f"    ✓ payment_status: {report.fields['payment_status'].value}")
print(f"    ✓ duplicate_charge: {report.fields['duplicate_charge'].value}")
print(f"    ✓ Blocking fields: {report.blocking_fields}")
print(f"    ✓ Display score: {report.display_score}% ({report.overall_label})")

# ── Test 8: Escalation ticket ────────────────────────────────────────
print("\n[8] Escalation ticket creation")
ticket = create_escalation_ticket(case, reason)
assert ticket["case_id"] == case.case_id
assert ticket["status"] == "ESCALATED"
assert ticket["transaction_id"] == "TX48291"
assert ticket["amount"] == 1499.0
assert ticket["confidence_display"] > 0  # score is present
assert "duplicate_charge" in ticket["unverified"]
print(f"    ✓ Ticket ID: {ticket['ticket_id']}")
print(f"    ✓ Issue: {ticket['issue']}")
print(f"    ✓ Confidence: {ticket['confidence_display']}%")
print(f"    ✓ Verified: {ticket['verified']}")
print(f"    ✓ Unverified: {ticket['unverified']}")
print(f"    ✓ Summary: {ticket['summary']}")

# ── Test 9: User requests human ──────────────────────────────────────
print("\n[9] User explicitly requests human")
case2 = get_or_create_case("test-channel-2")
case2.intent = "payment_issue"
case2.user_requested_human = True
action2, reason2 = decide(case2)
assert action2 == Action.ESCALATE
assert "explicitly" in reason2.lower()
print(f"    ✓ {action2}: {reason2}")

# ── Test 10: Tool failure escalation ─────────────────────────────────
print("\n[10] Tool failure escalation")
case3 = get_or_create_case("test-channel-3")
case3.intent = "payment_issue"
case3.transaction_id = "TX00000"
case3.tool_failed = True
action3, reason3 = decide(case3)
assert action3 == Action.ESCALATE
assert "verify" in reason3.lower()
print(f"    ✓ {action3}: {reason3}")

# ── Test 11: Mock API endpoint ───────────────────────────────────────
print("\n[11] Mock transaction API")
r1 = check_transaction("TX48291")
r2 = check_transaction("TX00001")
r3 = check_transaction("TXNOTEXIST")
assert r1["success"] and r1["status"] == "SUCCESS"
assert r2["success"] and r2["status"] == "FAILED"
assert not r3["success"] and r3["error"] == "transaction_not_found"
print(f"    ✓ TX48291: {r1['status']} / {r1['order_status']}")
print(f"    ✓ TX00001: {r2['status']}")
print(f"    ✓ TXNOTEXIST: {r3['error']}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
print("\nPRISM MVP is ready.")
print("\nTo run the application:")
print("  Backend:  cd backend && uvicorn main:app --reload --port 8000")
print("  Frontend: cd frontend && npm run dev")
print("  Open:     http://localhost:5173       (Caller)")
print("            http://localhost:5173/agent  (Agent Dashboard)")
