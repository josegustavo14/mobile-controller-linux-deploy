from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=5555)
    serial: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connection_status: Mapped[str] = mapped_column(String(20), default="DISCONNECTED")
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    android_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sdk: Mapped[str | None] = mapped_column(String(40), nullable=True)
    hardware: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cpu_abi: Mapped[str | None] = mapped_column(String(80), nullable=True)
    display_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kernel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    root_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
