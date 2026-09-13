from fastapi import APIRouter, Depends, Query, Request

from backend.app.core.auth import require_admin
from backend.app.schemas.system import AuditLogResponse, DashboardResponse, SystemInfoResponse

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(require_admin)])


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(request: Request) -> DashboardResponse:
    devices = request.app.state.device_service.list()
    return DashboardResponse(
        total_devices=len(devices),
        connected_devices=sum(device.connection_status == "CONNECTED" for device in devices),
        rooted_devices=sum(device.root_available is True for device in devices),
        devices_with_errors=sum(device.connection_status == "ERROR" for device in devices),
        recent_activity=request.app.state.audit_service.list(8),
    )


@router.get("/logs", response_model=list[AuditLogResponse])
async def logs(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> list[AuditLogResponse]:
    return request.app.state.audit_service.list(limit)


@router.get("/info", response_model=SystemInfoResponse)
async def info(request: Request) -> SystemInfoResponse:
    settings = request.app.state.settings
    return SystemInfoResponse(
        version=request.app.version,
        authentication_enabled=bool(settings.admin_token),
        adb_path=settings.adb_path,
        adb_server_port=settings.adb_server_port,
        adb_timeout=settings.adb_timeout,
        linux_deploy_cli=settings.linux_deploy_cli,
        database_backend=settings.database_url.split(":", maxsplit=1)[0],
    )
