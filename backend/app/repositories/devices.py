from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.device import Device


class DeviceRepository:
    def list(self, session: Session) -> list[Device]:
        return list(session.scalars(select(Device).order_by(Device.created_at.desc())))

    def get(self, session: Session, device_id: str) -> Device | None:
        return session.get(Device, device_id)

    def get_by_name(self, session: Session, name: str) -> Device | None:
        return session.scalar(select(Device).where(Device.name == name))

    def get_by_endpoint(self, session: Session, host: str, port: int) -> Device | None:
        return session.scalar(select(Device).where(Device.host == host, Device.port == port))

    def add(self, session: Session, device: Device) -> Device:
        session.add(device)
        session.flush()
        return device

    def delete(self, session: Session, device: Device) -> None:
        session.delete(device)
