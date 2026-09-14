from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    action: str
    level: str
    device_id: str | None
    message: str
    created_at: datetime
    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    total_devices: int
    connected_devices: int
    rooted_devices: int
    devices_with_errors: int
    recent_activity: list[AuditLogResponse]


class SystemInfoResponse(BaseModel):
    version: str
    authentication_enabled: bool
    adb_path: str
    adb_server_port: int
    adb_timeout: float
    scrcpy_path: str
    scrcpy_viewer_port: int
    termux_agent_configured: bool
    termux_agent_port: int
    linux_deploy_cli: str
    database_backend: str
