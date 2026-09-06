# ENGINE: PlatformEngine
"""
PRISM Database — SQLite persistence layer.

Tables:
  - cases           — CaseState snapshot for persistence
  - escalations     — Escalated case records
  - sessions        — Session audit trail
  - tool_executions — Tool call audit log
  - audit_logs      — General audit trail

The in-memory dicts (context.cases, context.escalated_cases) remain the
primary runtime store for performance. The database is synced on key events:
  - case escalation
  - session end
  - takeover

This means the in-memory store is always the source of truth during a session,
and the database is the persistence layer for restarts and analytics.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DATABASE_URL", "prism.db")

_engine = None
_initialized = False


def get_engine():
    """Get or create the SQLite engine."""
    global _engine
    if _engine is None:
        try:
            from sqlmodel import create_engine
            sqlite_url = f"sqlite:///{DB_PATH}"
            _engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})
        except ImportError:
            logger.warning("[Database] sqlmodel not installed — persistence disabled")
    return _engine


def init_db():
    """Create all tables if they don't exist."""
    global _initialized
    if _initialized:
        return
    engine = get_engine()
    if engine is None:
        return
    try:
        from sqlmodel import SQLModel, text
        SQLModel.metadata.create_all(engine)
        _initialized = True
        logger.info(f"[Database] Initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"[Database] Init failed: {e}")


def get_db_health() -> dict:
    """Return database health status."""
    engine = get_engine()
    if engine is None:
        return {"status": "unavailable", "error": "sqlmodel not installed"}
    try:
        from sqlmodel import Session, text
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        return {"status": "ok", "path": DB_PATH}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)[:100]}


class CaseRepository:
    """
    Persistence operations for CaseState objects.
    The in-memory context.cases dict is the primary store.
    This class syncs important state to SQLite for durability.
    """

    def save_escalation(self, case_data: dict) -> None:
        """Persist an escalation record to the database."""
        engine = get_engine()
        if engine is None:
            return
        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                session.exec(text("""
                    INSERT OR REPLACE INTO escalations
                    (case_id, channel, data, created_at)
                    VALUES (:case_id, :channel, :data, :created_at)
                """), {
                    "case_id": case_data.get("case_id", ""),
                    "channel": case_data.get("channel", ""),
                    "data": json.dumps(case_data),
                    "created_at": datetime.utcnow().isoformat(),
                })
                session.commit()
        except Exception as e:
            logger.warning(f"[CaseRepository] save_escalation failed: {e}")

    def load_escalations(self) -> List[dict]:
        """Load all escalation records from the database."""
        engine = get_engine()
        if engine is None:
            return []
        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                result = session.exec(text("SELECT data FROM escalations ORDER BY created_at DESC"))
                return [json.loads(row[0]) for row in result.fetchall()]
        except Exception as e:
            logger.warning(f"[CaseRepository] load_escalations failed: {e}")
            return []

    def save_session(self, channel: str, case_id: str, status: str) -> None:
        """Persist a session record."""
        engine = get_engine()
        if engine is None:
            return
        try:
            from sqlmodel import Session, text
            with Session(engine) as session:
                session.exec(text("""
                    INSERT OR REPLACE INTO sessions
                    (channel, case_id, status, updated_at)
                    VALUES (:channel, :case_id, :status, :updated_at)
                """), {
                    "channel": channel,
                    "case_id": case_id,
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat(),
                })
                session.commit()
        except Exception as e:
            logger.warning(f"[CaseRepository] save_session failed: {e}")


def _create_tables_sql():
    """Raw SQL to create tables — used as fallback if SQLModel models not set up."""
    engine = get_engine()
    if engine is None:
        return
    try:
        from sqlmodel import Session, text
        with Session(engine) as session:
            session.exec(text("""
                CREATE TABLE IF NOT EXISTS escalations (
                    case_id TEXT PRIMARY KEY,
                    channel TEXT,
                    data TEXT,
                    created_at TEXT
                )
            """))
            session.exec(text("""
                CREATE TABLE IF NOT EXISTS sessions (
                    channel TEXT PRIMARY KEY,
                    case_id TEXT,
                    status TEXT,
                    updated_at TEXT
                )
            """))
            session.exec(text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    channel TEXT,
                    case_id TEXT,
                    user_role TEXT,
                    details TEXT,
                    outcome TEXT
                )
            """))
            session.exec(text("""
                CREATE TABLE IF NOT EXISTS tool_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    tool_name TEXT,
                    channel TEXT,
                    case_id TEXT,
                    args_hash TEXT,
                    result_status TEXT,
                    latency_ms INTEGER,
                    verified INTEGER
                )
            """))
            session.commit()
            logger.info("[Database] Tables ready")
    except Exception as e:
        logger.error(f"[Database] Table creation failed: {e}")


# Module-level singleton
_repo = CaseRepository()


def get_case_repository() -> CaseRepository:
    return _repo
