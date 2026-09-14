from pydantic import BaseModel


class UpdateStatusResponse(BaseModel):
    current_version: str
    latest_version: str | None
    update_available: bool
    updater_enabled: bool
    message: str


class UpdateApplyResponse(BaseModel):
    accepted: bool
    message: str
