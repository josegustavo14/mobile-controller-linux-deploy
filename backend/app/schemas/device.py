from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=5555, ge=1, le=65535)

    @field_validator("name", "host")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class DeviceUpdate(DeviceCreate):
    pass


class PairRequest(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    pairing_code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]+$")

    @field_validator("host")
    @classmethod
    def strip_host(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class MessageResponse(BaseModel):
    message: str


class DeviceResponse(BaseModel):
    id: str
    name: str
    host: str
    port: int
    serial: str | None
    connection_status: ConnectionStatus
    manufacturer: str | None
    model: str | None
    android_version: str | None
    sdk: str | None
    hardware: str | None
    cpu_abi: str | None
    display_id: str | None
    kernel: str | None
    root_available: bool | None
    last_error: str | None
    details_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ConnectionResponse(BaseModel):
    device: DeviceResponse
    message: str
