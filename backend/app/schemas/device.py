from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

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


class DeviceShellRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)
    root: bool = False

    @field_validator("command")
    @classmethod
    def strip_command(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class DeviceShellResponse(BaseModel):
    output: str
    root: bool


class DeviceActionRequest(BaseModel):
    action: Literal[
        "home",
        "back",
        "recent",
        "lock",
        "wake",
        "volume_up",
        "volume_down",
        "mute",
        "open_settings",
    ]


class PackageLaunchRequest(BaseModel):
    package: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9._]+$")


class TermuxCommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)

    @field_validator("command")
    @classmethod
    def strip_termux_command(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class DeviceDiagnosticsResponse(BaseModel):
    battery_level: int | None
    battery_status: str | None
    charging: bool | None
    temperature_c: float | None
    uptime_seconds: int | None
    screen_state: str | None
    wifi_ipv4: str | None
    tailscale_ipv4: str | None
    termux_installed: bool
    tailscale_installed: bool
    storage: str


class PackageListResponse(BaseModel):
    packages: list[str]
