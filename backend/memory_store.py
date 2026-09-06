# ENGINE: PlatformEngine
"""
PRISM Long-Term Memory Store — persisted consent-gated memory.

Stores per-channel key-value memories with optional expiration in the
SQLite `memories` table. Accessed via MemoryManager in memory_manager.py.

Operations:
  store(channel, key, value, expires_hours)   → upsert a memory
  retrieve(channel, key)                      → get value or None
  delete(channel, key)                        → remove one
  delete_all(channel)                         → remove all for channel
  list_keys(channel)                          → [keys only, for privacy]
  list_recent(channel, limit)                 → [(key, value, created_at)]
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

LTM_TABLE = "memories"


class LongTermMemory:
    """
    Persistent long-term memory backed by the same SQLite database as
    the CaseRepository (database.py).

    Each row: id, channel, key, value_json, created_at, expires_at
    - channel: Agora session channel (one user's conversation thread)
    - key:   memory key (e.g. "preferred_language", "user_name")
    - value: JSON-serialized value
    """

    def __init__(self):
        self._ensure_table()

    # ── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _engine():
        from database import get_engine
        return get_engine()

    def _ensure_table(self) -> None:
        """Create the memories table if it doesn't exist."""
        engine = self._engine()
        if engine is None:
            logger.warning("[LongTermMemory] No database engine — LTM disabled")
            return
        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                session.exec(text(f"""
                    CREATE TABLE IF NOT EXISTS {LTM_TABLE} (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel     TEXT    NOT NULL,
                        key         TEXT    NOT NULL,
                        value_json  TEXT    NOT NULL,
                        created_at  TEXT    NOT NULL,
                        expires_at  TEXT,
                        UNIQUE(channel, key)
                    )
                """))
                session.commit()
        except Exception as e:
            logger.warning(f"[LongTermMemory] Table ensure failed: {e}")

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()

    # ── Public API ──────────────────────────────────────────────────────

    def store(
        self,
        channel: str,
        key: str,
        value: Any,
        expires_hours: Optional[int] = None,
    ) -> None:
        """
        Upsert a long-term memory. If expires_hours is set, the memory is
        considered stale after that many hours (retrieve will return None
        and it will be pruned on next store/delete call).
        """
        engine = self._engine()
        if engine is None:
            return

        expires_at = None
        if expires_hours is not None:
            expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()

        try:
            value_json = json.dumps(value, ensure_ascii=False)
            from sqlmodel import Session, text
            with Session(engine) as session:
                session.exec(text(f"""
                    INSERT OR REPLACE INTO {LTM_TABLE}
                    (channel, key, value_json, created_at, expires_at)
                    VALUES (:channel, :key, :value_json, :created_at, :expires_at)
                """), {
                    "channel": channel,
                    "key": key,
                    "value_json": value_json,
                    "created_at": self._now(),
                    "expires_at": expires_at,
                })
                session.commit()
        except Exception as e:
            logger.warning(f"[LongTermMemory] store failed: {e}")

    def retrieve(self, channel: str, key: str) -> Optional[Any]:
        """
        Return the value for (channel, key), or None if missing / expired.
        Expired rows are deleted as a side effect.
        """
        engine = self._engine()
        if engine is None:
            return None

        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                row = session.exec(text(f"""
                    SELECT value_json, expires_at FROM {LTM_TABLE}
                    WHERE channel = :channel AND key = :key
                """), {"channel": channel, "key": key}).first()

            if row is None:
                return None

            value_json, expires_at = row

            # Expired? Delete and return None
            if expires_at:
                try:
                    expiry = datetime.fromisoformat(expires_at)
                    if datetime.utcnow() > expiry:
                        self.delete(channel, key)
                        return None
                except ValueError:
                    pass

            return json.loads(value_json)
        except Exception as e:
            logger.warning(f"[LongTermMemory] retrieve failed: {e}")
            return None

    def delete(self, channel: str, key: str) -> bool:
        """Delete a single memory row. Returns True if something was removed."""
        engine = self._engine()
        if engine is None:
            return False

        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                result = session.exec(text(f"""
                    DELETE FROM {LTM_TABLE}
                    WHERE channel = :channel AND key = :key
                """), {"channel": channel, "key": key})
                session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.warning(f"[LongTermMemory] delete failed: {e}")
            return False

    def delete_all(self, channel: str) -> int:
        """Remove all memories for a channel. Returns the count deleted."""
        engine = self._engine()
        if engine is None:
            return 0

        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                # Count before delete (SQLite doesn't easily return deleted count)
                count_row = session.exec(text(f"""
                    SELECT COUNT(*) FROM {LTM_TABLE} WHERE channel = :channel
                """), {"channel": channel}).first()
                count = count_row[0] if count_row else 0

                session.exec(text(f"""
                    DELETE FROM {LTM_TABLE} WHERE channel = :channel
                """), {"channel": channel})
                session.commit()
                return count
        except Exception as e:
            logger.warning(f"[LongTermMemory] delete_all failed: {e}")
            return 0

    def list_keys(self, channel: str) -> List[str]:
        """
        Return memory keys only (not values) for the given channel.
        Used by the privacy-safe GET /memory/{channel} endpoint.
        """
        engine = self._engine()
        if engine is None:
            return []

        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                rows = session.exec(text(f"""
                    SELECT key, expires_at FROM {LTM_TABLE}
                    WHERE channel = :channel
                    ORDER BY created_at DESC
                """), {"channel": channel}).fetchall()

            keys: List[str] = []
            now = datetime.utcnow()
            for key, expires_at in rows:
                if expires_at:
                    try:
                        if datetime.fromisoformat(expires_at) < now:
                            continue
                    except ValueError:
                        pass
                keys.append(key)
            return keys
        except Exception as e:
            logger.warning(f"[LongTermMemory] list_keys failed: {e}")
            return []

    def list_recent(
        self, channel: str, limit: int = 5
    ) -> List[Tuple[str, Any, str]]:
        """
        Return the most recent non-expired memories as:
        [(key, value, created_at), ...]
        """
        engine = self._engine()
        if engine is None:
            return []

        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                rows = session.exec(text(f"""
                    SELECT key, value_json, created_at, expires_at FROM {LTM_TABLE}
                    WHERE channel = :channel
                    ORDER BY created_at DESC
                    LIMIT :limit
                """), {"channel": channel, "limit": limit * 2}).fetchall()

            results: List[Tuple[str, Any, str]] = []
            now = datetime.utcnow()
            for key, value_json, created_at, expires_at in rows:
                if expires_at:
                    try:
                        if datetime.fromisoformat(expires_at) < now:
                            continue
                    except ValueError:
                        pass
                try:
                    value = json.loads(value_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                results.append((key, value, created_at))
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.warning(f"[LongTermMemory] list_recent failed: {e}")
            return []

    def prune_expired(self) -> int:
        """Remove all expired memories from the DB. Returns number of rows pruned."""
        engine = self._engine()
        if engine is None:
            return 0

        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                result = session.exec(text(f"""
                    DELETE FROM {LTM_TABLE}
                    WHERE expires_at IS NOT NULL AND expires_at < :now
                """), {"now": self._now()})
                session.commit()
                return getattr(result, "rowcount", 0) or 0
        except Exception as e:
            logger.warning(f"[LongTermMemory] prune_expired failed: {e}")
            return 0
