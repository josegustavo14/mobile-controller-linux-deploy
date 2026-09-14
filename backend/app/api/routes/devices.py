from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.app.core.auth import require_admin
from backend.app.schemas.device import (
    ConnectionResponse,
    DeviceActionRequest,
    DeviceCreate,
    DeviceDiagnosticsResponse,
    DeviceResponse,
    DeviceShellRequest,
    DeviceShellResponse,
    DeviceUpdate,
    MessageResponse,
    PackageLaunchRequest,
    PackageListResponse,
    PairRequest,
    TermuxCommandRequest,
)
from backend.app.services.adb import ADBError
from backend.app.services.devices import DeviceNotFoundError, DeviceService, DuplicateDeviceError

router = APIRouter(prefix="/api/devices", tags=["devices"], dependencies=[Depends(require_admin)])


def service(request: Request) -> DeviceService:
    return request.app.state.device_service


def missing(device_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Device {device_id} was not found.")


def duplicate() -> HTTPException:
    return HTTPException(status_code=409, detail="A device with this name or network address already exists.")


@router.get("", response_model=list[DeviceResponse])
async def list_devices(request: Request) -> list[DeviceResponse]:
    return service(request).list()


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(payload: DeviceCreate, request: Request) -> DeviceResponse:
    try:
        return service(request).create(payload)
    except DuplicateDeviceError as exc:
        raise duplicate() from exc


@router.post("/pair", response_model=MessageResponse)
async def pair_device(payload: PairRequest, request: Request) -> MessageResponse:
    try:
        await service(request).pair(payload)
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return MessageResponse(message="Wireless debugging paired. Add the device using its connection port.")


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, request: Request) -> DeviceResponse:
    try:
        return service(request).get(device_id)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: str, payload: DeviceUpdate, request: Request) -> DeviceResponse:
    try:
        return service(request).update(device_id, payload)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except DuplicateDeviceError as exc:
        raise duplicate() from exc


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str, request: Request) -> None:
    try:
        await service(request).delete(device_id)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc


@router.post("/{device_id}/connect", response_model=ConnectionResponse)
async def connect_device(device_id: str, request: Request) -> ConnectionResponse:
    try:
        device = await service(request).connect(device_id)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    message = "Device connected." if device.connection_status == "CONNECTED" else "Device connection failed."
    return ConnectionResponse(device=device, message=message)


@router.post("/{device_id}/disconnect", response_model=ConnectionResponse)
async def disconnect_device(device_id: str, request: Request) -> ConnectionResponse:
    try:
        device = await service(request).disconnect(device_id)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    message = "Device disconnected." if device.connection_status == "DISCONNECTED" else "Device disconnect failed."
    return ConnectionResponse(device=device, message=message)


@router.post("/{device_id}/refresh", response_model=DeviceResponse)
async def refresh_device(device_id: str, request: Request) -> DeviceResponse:
    try:
        return await service(request).refresh(device_id)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc


@router.post("/{device_id}/reboot", response_model=ConnectionResponse)
async def reboot_device(device_id: str, request: Request) -> ConnectionResponse:
    try:
        device = await service(request).reboot(device_id)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConnectionResponse(device=device, message="Reboot requested. Reconnect when Android is online.")


@router.get("/{device_id}/diagnostics", response_model=DeviceDiagnosticsResponse)
async def device_diagnostics(device_id: str, request: Request) -> DeviceDiagnosticsResponse:
    try:
        return await service(request).diagnostics(device_id)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{device_id}/shell", response_model=DeviceShellResponse)
async def device_shell(device_id: str, payload: DeviceShellRequest, request: Request) -> DeviceShellResponse:
    try:
        output = await service(request).shell(device_id, payload.command, payload.root)
        return DeviceShellResponse(output=output, root=payload.root)
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{device_id}/actions", response_model=MessageResponse)
async def device_action(device_id: str, payload: DeviceActionRequest, request: Request) -> MessageResponse:
    try:
        await service(request).quick_action(device_id, payload.action)
        return MessageResponse(message=f"{payload.action.replace('_', ' ').title()} sent to Android.")
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{device_id}/apps", response_model=PackageListResponse)
async def device_apps(device_id: str, request: Request) -> PackageListResponse:
    try:
        return PackageListResponse(packages=await service(request).list_packages(device_id))
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{device_id}/apps/launch", response_model=MessageResponse)
async def launch_app(device_id: str, payload: PackageLaunchRequest, request: Request) -> MessageResponse:
    try:
        await service(request).launch_package(device_id, payload.package)
        return MessageResponse(message=f"Opened {payload.package}.")
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{device_id}/termux/open", response_model=MessageResponse)
async def open_termux(device_id: str, request: Request) -> MessageResponse:
    try:
        await service(request).open_termux(device_id)
        return MessageResponse(message="Termux opened on Android.")
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{device_id}/termux/run", response_model=MessageResponse)
async def run_termux(device_id: str, payload: TermuxCommandRequest, request: Request) -> MessageResponse:
    try:
        await service(request).run_termux(device_id, payload.command)
        return MessageResponse(message="Command started in a visible Termux session.")
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{device_id}/screenshot")
async def device_screenshot(device_id: str, request: Request) -> Response:
    try:
        image = await service(request).screenshot(device_id)
        return Response(content=image, media_type="image/png", headers={"Cache-Control": "no-store"})
    except DeviceNotFoundError as exc:
        raise missing(device_id) from exc
    except ADBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
