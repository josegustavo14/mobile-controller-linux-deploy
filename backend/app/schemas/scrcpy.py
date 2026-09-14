from pydantic import BaseModel


class ScrcpyStatusResponse(BaseModel):
    running: bool
    device_id: str | None
    serial: str | None
    viewer_port: int
    password: str | None
    message: str
