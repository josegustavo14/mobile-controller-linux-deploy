from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.core.auth import require_admin
from backend.app.schemas.environment import (
    CommandResponse,
    EnvironmentActionResponse,
    EnvironmentCreate,
    EnvironmentResponse,
    ServiceActionRequest,
    ServiceListResponse,
    TerminalRequest,
)
from backend.app.services.adb import ADBError
from backend.app.services.devices import DeviceNotFoundError
from backend.app.services.linux_deploy import (
    DuplicateEnvironmentError,
    EnvironmentNotFoundError,
    LinuxDeployService,
)

router = APIRouter(
    prefix="/api/environments",
    tags=["environments"],
    dependencies=[Depends(require_admin)],
)


def service(request: Request) -> LinuxDeployService:
    return request.app.state.linux_deploy_service


def environment_missing(environment_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Environment {environment_id} was not found.")


def operation_failed(exc: ADBError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


@router.get("", response_model=list[EnvironmentResponse])
async def list_environments(request: Request, device_id: str | None = None) -> list[EnvironmentResponse]:
    try:
        return service(request).list(device_id)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Device {device_id} was not found.") from exc


@router.post("", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(payload: EnvironmentCreate, request: Request) -> EnvironmentResponse:
    try:
        return await service(request).create(payload)
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Device {payload.device_id} was not found.") from exc
    except DuplicateEnvironmentError as exc:
        raise HTTPException(status_code=409, detail="This Linux Deploy profile is already registered.") from exc
    except ADBError as exc:
        raise operation_failed(exc) from exc


@router.delete("/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(environment_id: str, request: Request) -> None:
    try:
        service(request).delete(environment_id)
    except EnvironmentNotFoundError as exc:
        raise environment_missing(environment_id) from exc


@router.post("/{environment_id}/refresh", response_model=EnvironmentResponse)
async def refresh_environment(environment_id: str, request: Request) -> EnvironmentResponse:
    try:
        return await service(request).refresh(environment_id)
    except EnvironmentNotFoundError as exc:
        raise environment_missing(environment_id) from exc
    except ADBError as exc:
        raise operation_failed(exc) from exc


@router.post("/{environment_id}/start", response_model=EnvironmentActionResponse)
async def start_environment(environment_id: str, request: Request) -> EnvironmentActionResponse:
    try:
        environment, output = await service(request).control(environment_id, "start")
        return EnvironmentActionResponse(environment=environment, output=output)
    except EnvironmentNotFoundError as exc:
        raise environment_missing(environment_id) from exc
    except ADBError as exc:
        raise operation_failed(exc) from exc


@router.post("/{environment_id}/stop", response_model=EnvironmentActionResponse)
async def stop_environment(environment_id: str, request: Request) -> EnvironmentActionResponse:
    try:
        environment, output = await service(request).control(environment_id, "stop")
        return EnvironmentActionResponse(environment=environment, output=output)
    except EnvironmentNotFoundError as exc:
        raise environment_missing(environment_id) from exc
    except ADBError as exc:
        raise operation_failed(exc) from exc


@router.get("/{environment_id}/services", response_model=ServiceListResponse)
async def list_services(environment_id: str, request: Request) -> ServiceListResponse:
    try:
        services, output = await service(request).services(environment_id)
        return ServiceListResponse(services=services, output=output)
    except EnvironmentNotFoundError as exc:
        raise environment_missing(environment_id) from exc
    except ADBError as exc:
        raise operation_failed(exc) from exc


@router.post("/{environment_id}/services", response_model=CommandResponse)
async def control_service(
    environment_id: str,
    payload: ServiceActionRequest,
    request: Request,
) -> CommandResponse:
    try:
        output = await service(request).control_service(environment_id, payload)
        return CommandResponse(output=output)
    except EnvironmentNotFoundError as exc:
        raise environment_missing(environment_id) from exc
    except ADBError as exc:
        raise operation_failed(exc) from exc


@router.post("/{environment_id}/terminal", response_model=CommandResponse)
async def terminal(
    environment_id: str,
    payload: TerminalRequest,
    request: Request,
) -> CommandResponse:
    try:
        output = await service(request).terminal(environment_id, payload.command, payload.user)
        return CommandResponse(output=output)
    except EnvironmentNotFoundError as exc:
        raise environment_missing(environment_id) from exc
    except ADBError as exc:
        raise operation_failed(exc) from exc
