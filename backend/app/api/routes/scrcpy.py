import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.core.auth import require_admin
from backend.app.schemas.scrcpy import ScrcpyStatusResponse
from backend.app.services.devices import DeviceNotFoundError
from backend.app.services.scrcpy import ScrcpyError, ScrcpyService

router = APIRouter(prefix="/api/scrcpy", tags=["scrcpy"], dependencies=[Depends(require_admin)])


def service(request: Request) -> ScrcpyService:
    return request.app.state.scrcpy_service


@router.get("/status", response_model=ScrcpyStatusResponse)
async def scrcpy_status(request: Request) -> ScrcpyStatusResponse:
    return service(request).status()


@router.post("/{device_id}/start", response_model=ScrcpyStatusResponse)
async def start_scrcpy(device_id: str, request: Request) -> ScrcpyStatusResponse:
    try:
        device = request.app.state.device_service.get(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Android device was not found.") from exc
    if device.connection_status != "CONNECTED" or not device.serial:
        raise HTTPException(status_code=409, detail="Connect the Android device before starting scrcpy.")
    try:
        return await asyncio.to_thread(service(request).start, device.id, device.serial)
    except ScrcpyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stop", response_model=ScrcpyStatusResponse)
async def stop_scrcpy(request: Request) -> ScrcpyStatusResponse:
    return await asyncio.to_thread(service(request).stop)
