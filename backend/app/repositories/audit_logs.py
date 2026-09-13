from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog


class AuditLogRepository:
    def list(self, session: Session, limit: int = 100) -> list[AuditLog]:
        statement = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        return list(session.scalars(statement))

    def add(self, session: Session, entry: AuditLog) -> AuditLog:
        session.add(entry)
        session.flush()
        return entry
