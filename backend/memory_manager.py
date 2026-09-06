# ENGINE: IntelligenceEngine
"""
PRISM Memory Manager — Short-term + Long-term memory orchestration.

MemoryManager provides a unified interface for:
  - remember(case, key, value, source)       → short-term (session) memory
  - recall(case, key)                         → retrieve from short-term
  - remember_long_term(case, key, value)      → persisted (if consent=True)
  - recall_long_term(case, key)               → retrieve from DB
  - forget(case, key)                         → remove short-term
  - forget_all(case, long_term=False)         → wipe memory
  - get_relevant_context(case, query)         → ranked retrieval for LLM context

Short-term memory: lives on CaseState.short_term_memory, cleared on session end.
Long-term memory:  lives in memory_store.LongTermMemory → DB, requires consent.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from context import CaseState

logger = logging.getLogger(__name__)

# Max number of short-term memory entries kept in LLM context
MAX_SHORT_TERM_CONTEXT_ENTRIES = 8
# Max number of long-term memory entries kept in LLM context
MAX_LONG_TERM_CONTEXT_ENTRIES = 3


class MemoryManager:
    """
    Unified memory interface for PRISM.

    Combines session-scoped short-term memory with optional persisted
    long-term memory. Handles consent, ranking, and LLM context assembly.
    """

    def __init__(self):
        self._ltm = None  # Lazy-loaded LongTermMemory

    # ── Short-term memory (session-scoped) ──────────────────────────────

    def remember(self, case: "CaseState", key: str, value: Any, source: str = "agent") -> None:
        """
        Store a value in short-term (session) memory.

        Args:
            case:     The current CaseState
            key:      Memory key (e.g. "preferred_language", "user_name")
            value:    Any JSON-serializable value
            source:   "user" | "agent" | "tool" — where the memory came from
        """
        case.short_term_memory[key] = {
            "value": value,
            "source": source,
            "created_at": datetime.utcnow().isoformat(),
        }
        logger.debug(f"[Memory] remember short-term: {key}={value}")

    def recall(self, case: "CaseState", key: str) -> Optional[Any]:
        """
        Retrieve a specific key from short-term memory.

        Returns the stored value or None if the key doesn't exist.
        """
        entry = case.short_term_memory.get(key)
        if entry is None:
            return None
        return entry.get("value")

    def forget(self, case: "CaseState", key: str) -> bool:
        """Remove a key from short-term memory. Returns True if removed."""
        if key in case.short_term_memory:
            del case.short_term_memory[key]
            return True
        return False

    def clear_short_term(self, case: "CaseState") -> None:
        """Wipe all short-term memory for this case/session."""
        case.short_term_memory.clear()

    # ── Long-term memory (persisted, consent-gated) ─────────────────────

    def _get_ltm(self):
        """Lazy-load LongTermMemory to avoid DB costs when unused."""
        if self._ltm is None:
            try:
                from memory_store import LongTermMemory
                self._ltm = LongTermMemory()
            except Exception as e:
                logger.warning(f"[Memory] LongTermMemory unavailable: {e}")
                self._ltm = False
        if self._ltm is False:
            return None
        return self._ltm

    def remember_long_term(
        self, case: "CaseState", key: str, value: Any, expires_hours: Optional[int] = None
    ) -> bool:
        """
        Persist to long-term memory. Requires memory_consent == True.

        Returns True if successfully stored, False if consent missing or LTM unavailable.
        """
        if not getattr(case, "memory_consent", False):
            logger.debug(f"[Memory] remember_long_term skipped — no consent for {key}")
            return False

        ltm = self._get_ltm()
        if ltm is None:
            return False

        try:
            ltm.store(
                channel=case.channel,
                key=key,
                value=value,
                expires_hours=expires_hours,
            )
            logger.debug(f"[Memory] remember long-term: {key}={value}")
            return True
        except Exception as e:
            logger.warning(f"[Memory] remember_long_term failed: {e}")
            return False

    def recall_long_term(self, case: "CaseState", key: str) -> Optional[Any]:
        """Retrieve a specific key from long-term memory for this channel."""
        ltm = self._get_ltm()
        if ltm is None:
            return None
        return ltm.retrieve(case.channel, key)

    def forget_long_term(self, case: "CaseState", key: str) -> bool:
        """Remove a specific long-term memory key for this channel."""
        ltm = self._get_ltm()
        if ltm is None:
            return False
        return ltm.delete(case.channel, key)

    def forget_all_long_term(self, case: "CaseState") -> int:
        """Remove ALL long-term memories for this channel. Returns count deleted."""
        ltm = self._get_ltm()
        if ltm is None:
            return 0
        return ltm.delete_all(case.channel)

    def list_long_term_keys(self, case: "CaseState") -> List[str]:
        """Return only the keys (not values) of long-term memories for privacy."""
        ltm = self._get_ltm()
        if ltm is None:
            return []
        return ltm.list_keys(case.channel)

    # ── Memory retrieval for LLM context ────────────────────────────────

    def get_relevant_context(
        self, case: "CaseState", query: Optional[str] = None
    ) -> List[str]:
        """
        Return a ranked list of memory context strings for the LLM prompt.

        Combines:
          - Short-term memory (most recent first, up to MAX_SHORT_TERM_CONTEXT_ENTRIES)
          - Long-term memory (if consent, recency-ranked, up to MAX_LONG_TERM_CONTEXT_ENTRIES)

        Each entry is formatted as a readable string suitable for inclusion
        in the system prompt / context block.
        """
        entries: List[str] = []

        # 1. Short-term memory — take the most recently added entries
        stm = case.short_term_memory
        if stm:
            stm_items = list(stm.items())
            # Sort by created_at desc (most recent first)
            stm_items.sort(
                key=lambda kv: kv[1].get("created_at", ""),
                reverse=True,
            )
            for key, entry in stm_items[:MAX_SHORT_TERM_CONTEXT_ENTRIES]:
                value = entry.get("value")
                source = entry.get("source", "unknown")
                entries.append(f"[Short-term memory | {source}] {key}: {value}")

        # 2. Long-term memory — require consent
        if getattr(case, "memory_consent", False):
            ltm = self._get_ltm()
            if ltm is not None:
                try:
                    ltm_entries = ltm.list_recent(
                        case.channel, limit=MAX_LONG_TERM_CONTEXT_ENTRIES
                    )
                    for key, value, created_at in ltm_entries:
                        entries.append(f"[Long-term memory] {key}: {value}")
                except Exception as e:
                    logger.warning(f"[Memory] LTM retrieval failed: {e}")

        return entries

    # ── Convenience: remember extracted user facts ──────────────────────

    def maybe_remember_user_facts(self, case: "CaseState", extracted: Dict[str, Any]) -> None:
        """
        Convenience method: after intent/entity extraction, persist noteworthy
        facts to short-term memory, and (with consent) long-term too.

        Called from voice_agent after the LLM extraction step.
        """
        noteworthy_keys = [
            "user_name",
            "preferred_language",
            "customer_email",
            "customer_phone",
            "frequent_issue",
        ]
        for k in noteworthy_keys:
            v = extracted.get(k)
            if v:
                self.remember(case, k, v, source="user")
                # Also try long-term if consent is present
                if k in ("preferred_language", "user_name"):
                    self.remember_long_term(case, k, v, expires_hours=720)  # 30 days


# Module-level singleton
_memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """Return the shared MemoryManager singleton."""
    return _memory_manager
