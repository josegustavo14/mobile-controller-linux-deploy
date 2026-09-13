from backend.app.core.database import Database
from backend.app.models.audit_log import AuditLog
from backend.app.repositories.audit_logs import AuditLogRepository


class AuditService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.repository = AuditLogRepository()

    def record(self, action: str, message: str, device_id: str | None = None, level: str = "INFO") -> AuditLog:
        with self.database.session() as session:
            return self.repository.add(
                session,
                AuditLog(action=action, message=message, device_id=device_id, level=level),
            )

    def list(self, limit: int = 100) -> list[AuditLog]:
        with self.database.session() as session:
            return self.repository.list(session, limit)
