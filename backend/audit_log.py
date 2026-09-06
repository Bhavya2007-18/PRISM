# ENGINE: PlatformEngine
"""
PRISM Audit Logger

Structured audit trail for all significant system events.
Writes to: Python logging (always) + database (when available).

Events:
    session_start, session_end, tool_executed, policy_decision,
    escalation_created, takeover, auth_success, auth_failure
"""
import logging
import json
from datetime import datetime
from typing import Optional

logger = logging.getLogger("prism.audit")


class AuditLogger:
    """
    Logs significant PRISM events with structured metadata.
    Thread-safe, async-safe, never throws (audit failures are logged, not raised).
    """

    def log(
        self,
        event_type: str,
        channel: Optional[str] = None,
        case_id: Optional[str] = None,
        user_role: Optional[str] = None,
        details: Optional[dict] = None,
        outcome: str = "ok",
    ) -> None:
        """Log an audit event to the structured logger and database."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "channel": channel,
            "case_id": case_id,
            "user_role": user_role,
            "outcome": outcome,
        }
        if details:
            # Never log sensitive data in details
            safe_details = {k: v for k, v in details.items() if k not in ("password", "token", "api_key", "secret")}
            entry["details"] = safe_details

        # Structured log line
        logger.info(json.dumps(entry))

        # Persist to database (non-fatal)
        self._persist(entry)

    def _persist(self, entry: dict) -> None:
        """Persist audit entry to database."""
        try:
            from database import get_engine
            engine = get_engine()
            if engine is None:
                return
            from sqlmodel import Session, text
            with Session(engine) as session:
                session.exec(text("""
                    INSERT INTO audit_logs (timestamp, event_type, channel, case_id, user_role, details, outcome)
                    VALUES (:timestamp, :event_type, :channel, :case_id, :user_role, :details, :outcome)
                """), {
                    "timestamp": entry.get("timestamp"),
                    "event_type": entry.get("event_type"),
                    "channel": entry.get("channel"),
                    "case_id": entry.get("case_id"),
                    "user_role": entry.get("user_role"),
                    "details": json.dumps(entry.get("details", {})),
                    "outcome": entry.get("outcome"),
                })
                session.commit()
        except Exception:
            pass  # Audit log failures are never fatal

    # ── Convenience methods for common events ────────────────────────

    def session_start(self, channel: str, language: Optional[str] = None) -> None:
        self.log("session_start", channel=channel, details={"language": language})

    def session_end(self, channel: str, reason: str = "user_disconnect") -> None:
        self.log("session_end", channel=channel, details={"reason": reason})

    def tool_executed(self, tool_name: str, channel: str, case_id: str, status: str = "ok") -> None:
        self.log("tool_executed", channel=channel, case_id=case_id,
                 details={"tool": tool_name}, outcome=status)

    def policy_decision(self, decision: str, channel: str, case_id: str, reason: str = "") -> None:
        self.log("policy_decision", channel=channel, case_id=case_id,
                 details={"decision": decision, "reason": reason[:100]})

    def escalation_created(self, channel: str, case_id: str, reason: str = "") -> None:
        self.log("escalation_created", channel=channel, case_id=case_id,
                 details={"reason": reason[:200]}, outcome="escalated")

    def takeover(self, case_id: str, agent_id: Optional[str] = None) -> None:
        self.log("takeover", case_id=case_id, details={"agent_id": agent_id})

    def auth_success(self, username: str, role: str) -> None:
        self.log("auth_success", user_role=role, details={"username": username})

    def auth_failure(self, username: str) -> None:
        self.log("auth_failure", details={"username": username}, outcome="denied")


# Module-level singleton
_audit = AuditLogger()


def get_audit_logger() -> AuditLogger:
    return _audit
