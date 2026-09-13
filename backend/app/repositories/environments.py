from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.environment import Environment


class EnvironmentRepository:
    def list(self, session: Session, device_id: str | None = None) -> list[Environment]:
        statement = select(Environment).order_by(Environment.created_at.desc())
        if device_id:
            statement = statement.where(Environment.device_id == device_id)
        return list(session.scalars(statement))

    def get(self, session: Session, environment_id: str) -> Environment | None:
        return session.get(Environment, environment_id)

    def get_by_profile(self, session: Session, device_id: str, profile: str) -> Environment | None:
        return session.scalar(
            select(Environment).where(
                Environment.device_id == device_id,
                Environment.profile == profile,
            )
        )

    def add(self, session: Session, environment: Environment) -> Environment:
        session.add(environment)
        session.flush()
        return environment

    def delete(self, session: Session, environment: Environment) -> None:
        session.delete(environment)

    def delete_for_device(self, session: Session, device_id: str) -> None:
        for environment in self.list(session, device_id):
            session.delete(environment)
