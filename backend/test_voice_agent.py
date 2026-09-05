import asyncio
import os
import sys

# Ensure backend imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_agent import run_agent_turn
from context import get_or_create_case


async def test():
    print("Testing PRISM voice agent turn (LLM + deterministic policy gate)...")
    channel = "test-voice-channel"
    case = get_or_create_case(channel)

    # Simulating user input with transaction ID TX48291 (the canonical
    # "money taken, order not confirmed" case that should escalate).
    messages = [
        {"role": "user", "content": "Mera transaction TX48291 check karo please, paise kat gaye hai."}
    ]

    result = await run_agent_turn(channel, messages)
    print("Result content:", result.get("content"))
    print("Tool executed:", result.get("tool_executed"))
    print("Policy decision:", result.get("policy_decision"))
    print("Escalated:", result.get("escalated"))
    print("Case state transaction_id:", case.transaction_id)
    print("Case state payment_status:", case.payment_status)
    print("Case state order_status:", case.order_status)
    print("Case state duplicate_charge:", case.duplicate_charge)
    print("Case state verified:", case.verified)


if __name__ == "__main__":
    asyncio.run(test())
