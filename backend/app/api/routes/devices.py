from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.core.auth import require_admin
from backend.app.schemas.device import ConnectionResponse, DeviceCreate, DeviceResponse, DeviceUpdate, MessageResponse, PairRequest
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
