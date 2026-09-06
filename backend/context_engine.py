# ENGINE: IntelligenceEngine
"""
PRISM Context Engine — conversation context assembly.

ContextManager is the single authority for building the LLM context dict.
It replaces the inline context assembly in voice_agent.py and enforces:

- Sliding window: last 12 conversation turns (configurable)
- Context order: SystemPrompt → CaseContext → ConversationWindow → ToolResults → PolicyState
- Token budget awareness via context_tokens_estimate()
"""
from typing import TYPE_CHECKING, List, Dict, Any, Optional

if TYPE_CHECKING:
    from context import CaseState

# Maximum number of conversation turns to include in LLM context.
# A "turn" is one user+assistant pair. Keeping last 12 prevents unbounded growth.
CONVERSATION_WINDOW = 12


class ContextManager:
    """
    Assembles the full LLM message context for a given turn.
    
    Usage:
        ctx = ContextManager()
        messages = ctx.build_context(system_prompt, case, extra_messages)
    """

    def __init__(self, window_size: int = CONVERSATION_WINDOW):
        self.window_size = window_size

    def build_context(
        self,
        system_prompt: str,
        case: "CaseState",
        incoming_messages: List[Dict],
        policy_state: Optional[str] = None,
        retrieved_knowledge: Optional[List[str]] = None,
        last_user_text: Optional[str] = None,
    ) -> List[Dict]:
        """
        Build the full message list to send to the LLM.
        
        Order:
          1. System: PRISM Voice Assistant system prompt
          2. System: Current case context (safe summary)
          3. System: Memory context (short-term + long-term if consent)
          4. System: Retrieved knowledge (if RAG enabled and available)
          5. System: Policy directive (if provided)
          6. Conversation: sliding window of last N turns (user + assistant only)
        
        Returns list of message dicts in OpenAI chat format.
        """
        messages: List[Dict] = []

        # 1. Main system prompt
        messages.append({"role": "system", "content": system_prompt})

        # 2. Case context
        messages.append({
            "role": "system",
            "content": f"CURRENT CASE CONTEXT: {case.to_prompt_summary()}",
        })

        # 3. Memory context — short-term + long-term
        try:
            from memory_manager import get_memory_manager
            mm = get_memory_manager()
            memory_entries = mm.get_relevant_context(case, query=last_user_text)
            if memory_entries:
                memory_text = "\n".join(memory_entries)
                messages.append({
                    "role": "system",
                    "content": f"RELEVANT MEMORY:\n{memory_text}",
                })
        except Exception as e:
            # Memory failures should never break the context pipeline
            import logging as _log
            _log.getLogger(__name__).warning(f"[ContextEngine] Memory context failed: {e}")

        # 4. Retrieved knowledge (RAG — optional)
        if retrieved_knowledge:
            knowledge_text = "\n\n".join(retrieved_knowledge[:2])  # max 2 chunks
            messages.append({
                "role": "system",
                "content": f"RELEVANT KNOWLEDGE BASE:\n{knowledge_text}",
            })

        # 5. Policy directive (optional — added post-tool)
        if policy_state:
            messages.append({"role": "system", "content": policy_state})

        # 6. Sliding window of conversation turns
        conversation = self._get_conversation_window(incoming_messages)
        messages.extend(conversation)

        return messages

    def _get_conversation_window(self, incoming_messages: List[Dict]) -> List[Dict]:
        """
        Return the last N turns from incoming_messages, excluding system messages.
        A "turn" = one message. We take the last (window_size * 2) messages to
        capture the last N user+assistant pairs.
        """
        # Filter to only user and assistant messages
        turns = [
            m for m in incoming_messages
            if m.get("role") in ("user", "assistant")
        ]
        # Keep only the last window_size * 2 messages (N user + N assistant)
        max_messages = self.window_size * 2
        if len(turns) > max_messages:
            turns = turns[-max_messages:]
        return turns

    def context_tokens_estimate(self, messages: List[Dict]) -> int:
        """
        Rough token count estimate for the message list.
        Uses ~4 chars per token as a conservative heuristic.
        """
        total_chars = sum(len(m.get("content", "") or "") for m in messages)
        return total_chars // 4

    def build_followup_context(
        self,
        base_messages: List[Dict],
        tool_calls: List[Dict],
        tool_results: List[Dict],
        policy_directive: str,
    ) -> List[Dict]:
        """
        Build the follow-up context after tool execution.
        Used for the second LLM call (post-tool response generation).
        """
        return (
            base_messages
            + [{"role": "assistant", "tool_calls": tool_calls, "content": None}]
            + tool_results
            + [{"role": "system", "content": policy_directive}]
        )
