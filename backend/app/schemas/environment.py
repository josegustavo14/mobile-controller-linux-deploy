from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SAFE_NAME = r"^[A-Za-z0-9._-]+$"


class EnvironmentStatus(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class EnvironmentCreate(BaseModel):
    device_id: str
    name: str = Field(min_length=1, max_length=120)
    profile: str = Field(default="default", min_length=1, max_length=120, pattern=SAFE_NAME)
    default_user: str = Field(default="root", min_length=1, max_length=80, pattern=SAFE_NAME)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class EnvironmentResponse(BaseModel):
    id: str
    device_id: str
    name: str
    profile: str
    default_user: str
    status: EnvironmentStatus
    last_output: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class EnvironmentActionResponse(BaseModel):
    environment: EnvironmentResponse
    output: str


class ServiceInfo(BaseModel):
    name: str
    running: bool | None
    raw: str


class ServiceListResponse(BaseModel):
    services: list[ServiceInfo]
    output: str


class ServiceActionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=SAFE_NAME)
    action: Literal["start", "stop", "restart", "status"]


class TerminalRequest(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    user: str | None = Field(default=None, min_length=1, max_length=80, pattern=SAFE_NAME)

    @field_validator("command")
    @classmethod
    def strip_command(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class CommandResponse(BaseModel):
    output: str
