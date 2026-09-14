from typing import Any, Literal

from pydantic import BaseModel, Field


class TermuxAgentCapabilitiesResponse(BaseModel):
    sensors: list[str]
    apis: list[str]


class TermuxSensorRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TermuxApiRequest(BaseModel):
    name: Literal["battery", "wifi", "location", "camera", "audio"]


class TermuxAgentDataResponse(BaseModel):
    source: str
    payload: Any
