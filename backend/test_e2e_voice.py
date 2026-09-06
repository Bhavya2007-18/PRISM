"""
PRISM End-to-End Voice Pipeline Tests

Tests the complete voice pipeline without requiring real Agora credentials.
All external services (Agora, LLM, Whisper) are mocked.

Run with: pytest backend/test_e2e_voice.py -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_case():
    """Fresh CaseState for each test."""
    from context import CaseState
    return CaseState(case_id="TEST-0001", channel="test-channel")


@pytest.fixture
def mock_llm_response():
    """Mock a successful LLM response."""
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "I can help with that. What is your transaction ID?",
                "tool_calls": None,
            },
            "finish_reason": "stop",
        }]
    }


@pytest.fixture
def mock_llm_tool_response():
    """Mock LLM response that calls check_transaction tool."""
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "function": {
                        "name": "check_transaction",
                        "arguments": '{"transaction_id": "TX48291"}',
                    }
                }],
            },
            "finish_reason": "tool_calls",
        }]
    }


# ── Test 1: Full pipeline — intent extraction to response ─────────────────

@pytest.mark.asyncio
async def test_full_pipeline_payment_issue(mock_case, mock_llm_response):
    """
    Test: User reports payment issue → intent extracted → LLM replies → response generated.
    """
    mock_case.last_user_text = "Mera payment kat gaya but order confirm nahi hua"

    with patch("voice_agent.prism_llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response
        
        from voice_agent import run_agent_turn
        messages = [{"role": "user", "content": mock_case.last_user_text}]
        result = await run_agent_turn("test-channel", messages)

    assert result["content"] is not None
    assert len(result["content"]) > 0
    assert result["tool_executed"] is None


# ── Test 2: Tool execution path ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_execution_check_transaction(mock_case, mock_llm_tool_response, mock_llm_response):
    """
    Test: LLM proposes check_transaction → tool runs → follow-up LLM call → response.
    """
    with patch("voice_agent.prism_llm_call", new_callable=AsyncMock) as mock_llm:
        # First call returns tool_calls, second returns the final reply
        mock_llm.side_effect = [mock_llm_tool_response, mock_llm_response]
        
        from voice_agent import run_agent_turn
        messages = [
            {"role": "user", "content": "Mera payment kat gaya"},
            {"role": "user", "content": "Transaction ID TX48291 hai"},
        ]
        result = await run_agent_turn("test-channel", messages)

    assert result["tool_executed"] == "check_transaction"
    assert result["content"] is not None


# ── Test 3: Escalation path — low confidence ─────────────────────────────

@pytest.mark.asyncio
async def test_escalation_path_low_confidence():
    """
    Test: After check_transaction with duplicate_charge=UNKNOWN → policy escalates.
    """
    from context import CaseState
    from policy import evaluate_escalation

    case = CaseState(case_id="TEST-0002", channel="test-ch-2")
    case.intent = "payment_issue"
    case.transaction_id = "TX48291"
    case.payment_status = "SUCCESS"
    case.order_status = "NOT_CONFIRMED"
    case.duplicate_charge = "UNKNOWN"  # triggers escalation
    case.verified = ["transaction_id", "payment_status", "order_status"]

    decision = evaluate_escalation(case, llm_proposed=True, proposed_reason="duplicate charge unknown")

    assert decision.decision == "ESCALATE"
    assert decision.approved is True


# ── Test 4: Interruption path ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_interruption_handling():
    """
    Test: barge_in_active=True → interruption logged → state reset to LISTENING.
    """
    from context import CaseState, cases
    case = CaseState(case_id="TEST-0003", channel="test-ch-3")
    case.barge_in_active = True
    case.interruption_count = 0
    # Register in global cases so run_agent_turn uses the same object
    cases["test-ch-3"] = case

    with patch("voice_agent.prism_llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {
            "choices": [{"message": {"content": "How can I help?", "tool_calls": None}}]
        }
        from voice_agent import run_agent_turn
        result = await run_agent_turn("test-ch-3", [{"role": "user", "content": "hai"}])

    # After interruption handling, barge_in_active should be cleared
    assert case.barge_in_active is False
    assert case.interruption_count == 1


# ── Test 5: Recovery path — tool failure → escalation ────────────────────

def test_tool_failure_recovery():
    """
    Test: Tool fails twice → ErrorRecoveryEngine returns should_escalate=True.
    """
    from context import CaseState
    from error_recovery import ErrorRecoveryEngine, FailureType
    
    case = CaseState(case_id="TEST-0004", channel="test-ch-4")
    engine = ErrorRecoveryEngine()

    # First attempt — retry message
    result1 = engine.recover(FailureType.TOOL, case, attempt=1)
    assert result1.should_escalate is False
    assert len(result1.reply) > 0

    # Second attempt — escalate
    result2 = engine.recover(FailureType.TOOL, case, attempt=2)
    assert result2.should_escalate is True
    assert case.tool_failed is True


# ── Test 6: Decision engine — all branches ───────────────────────────────

def test_decision_engine_branches():
    """
    Test all 7 decision branches in decision.py.
    """
    from context import CaseState
    from decision import decide, Action

    # 1. user_requested_human → ESCALATE
    c = CaseState(case_id="T1", channel="c1"); c.user_requested_human = True
    assert decide(c)[0] == Action.ESCALATE

    # 2. has_contradiction → ESCALATE
    c = CaseState(case_id="T2", channel="c2"); c.has_contradiction = True
    assert decide(c)[0] == Action.ESCALATE

    # 3. tool_failed → ESCALATE
    c = CaseState(case_id="T3", channel="c3"); c.tool_failed = True
    assert decide(c)[0] == Action.ESCALATE

    # 4. no intent → ASK
    c = CaseState(case_id="T4", channel="c4")
    assert decide(c)[0] == Action.ASK

    # 5. intent but no transaction_id → ASK
    c = CaseState(case_id="T5", channel="c5"); c.intent = "payment_issue"
    assert decide(c)[0] == Action.ASK

    # 6. transaction_id but no payment_status → TOOL_CALL
    c = CaseState(case_id="T6", channel="c6")
    c.intent = "payment_issue"; c.transaction_id = "TX12345"
    assert decide(c)[0] == Action.TOOL_CALL

    # 7. payment_status + duplicate_charge UNKNOWN → ESCALATE
    c = CaseState(case_id="T7", channel="c7")
    c.intent = "payment_issue"; c.transaction_id = "TX12345"
    c.payment_status = "SUCCESS"; c.duplicate_charge = "UNKNOWN"
    assert decide(c)[0] == Action.ESCALATE


# ── Test 7: Confidence thresholds ────────────────────────────────────────

def test_confidence_thresholds():
    """
    Test that confidence engine applies thresholds correctly.
    """
    from context import CaseState
    from confidence import get_confidence_report, RESOLVE_THRESHOLD, ESCALATE_BELOW

    # Fully resolved case
    c = CaseState(case_id="T8", channel="c8")
    c.intent = "payment_issue"
    c.transaction_id = "TX99999"; c.payment_status = "SUCCESS"
    c.order_status = "CONFIRMED"; c.duplicate_charge = "NO"
    c.verified = ["transaction_id", "payment_status", "order_status", "duplicate_charge"]
    
    report = get_confidence_report(c)
    assert report.overall_label == "CONFIDENT"
    assert report.display_score >= int(RESOLVE_THRESHOLD * 100)

    # Unresolved case with unknown duplicate
    c2 = CaseState(case_id="T9", channel="c9")
    c2.intent = "payment_issue"; c2.transaction_id = "TX48291"
    c2.payment_status = "SUCCESS"; c2.order_status = "NOT_CONFIRMED"
    c2.duplicate_charge = "UNKNOWN"
    c2.verified = ["transaction_id", "payment_status", "order_status"]
    
    report2 = get_confidence_report(c2)
    assert report2.display_score < int(RESOLVE_THRESHOLD * 100)
