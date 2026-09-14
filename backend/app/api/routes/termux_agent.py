import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.core.auth import require_admin
from backend.app.schemas.termux_agent import (
    TermuxAgentCapabilitiesResponse,
    TermuxAgentDataResponse,
    TermuxApiRequest,
    TermuxSensorRequest,
)
from backend.app.services.devices import DeviceNotFoundError
from backend.app.services.termux_agent import TermuxAgentError, TermuxAgentService

router = APIRouter(prefix="/api/termux-agent", tags=["termux-agent"], dependencies=[Depends(require_admin)])


def service(request: Request) -> TermuxAgentService:
    return request.app.state.termux_agent_service


@router.get("/{device_id}/capabilities", response_model=TermuxAgentCapabilitiesResponse)
async def capabilities(device_id: str, request: Request) -> TermuxAgentCapabilitiesResponse:
    try:
        return await asyncio.to_thread(service(request).capabilities, device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Android device was not found.") from exc
    except TermuxAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{device_id}/sensor", response_model=TermuxAgentDataResponse)
async def read_sensor(device_id: str, payload: TermuxSensorRequest, request: Request) -> TermuxAgentDataResponse:
    try:
        data = await asyncio.to_thread(service(request).read_sensor, device_id, payload.name)
        return TermuxAgentDataResponse(source=payload.name, payload=data)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Android device was not found.") from exc
    except TermuxAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{device_id}/api", response_model=TermuxAgentDataResponse)
async def read_api(device_id: str, payload: TermuxApiRequest, request: Request) -> TermuxAgentDataResponse:
    try:
        data = await asyncio.to_thread(service(request).read_api, device_id, payload.name)
        return TermuxAgentDataResponse(source=payload.name, payload=data)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Android device was not found.") from exc
    except TermuxAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
