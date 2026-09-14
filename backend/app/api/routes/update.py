import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.core.auth import require_admin
from backend.app.schemas.update import UpdateApplyResponse, UpdateStatusResponse
from backend.app.services.updater import UpdaterError, UpdaterService

router = APIRouter(prefix="/api/update", tags=["update"], dependencies=[Depends(require_admin)])


def service(request: Request) -> UpdaterService:
    return request.app.state.updater_service


@router.get("/status", response_model=UpdateStatusResponse)
async def status(request: Request) -> UpdateStatusResponse:
    result = await asyncio.to_thread(service(request).status, request.app.version)
    return UpdateStatusResponse(**result.__dict__)


@router.post("/apply", response_model=UpdateApplyResponse, status_code=202)
async def apply_update(request: Request) -> UpdateApplyResponse:
    try:
        await asyncio.to_thread(service(request).apply)
    except UpdaterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return UpdateApplyResponse(
        accepted=True,
        message="Update started. The interface will reconnect after the container restarts.",
    )
