from __future__ import annotations

import asyncio
import re
import shlex

from backend.app.core.database import Database
from backend.app.models.device import Device
from backend.app.models.environment import Environment
from backend.app.repositories.environments import EnvironmentRepository
from backend.app.schemas.environment import (
    EnvironmentCreate,
    EnvironmentStatus,
    ServiceActionRequest,
    ServiceInfo,
)
from backend.app.services.adb import ADBClient, ADBError
from backend.app.services.audit import AuditService
from backend.app.services.devices import DeviceNotFoundError, DeviceService


class EnvironmentNotFoundError(LookupError):
    pass


class DuplicateEnvironmentError(ValueError):
    pass


class LinuxDeployUnavailableError(ADBError):
    pass


class LinuxDeployService:
    def __init__(
        self,
        database: Database,
        adb: ADBClient,
        devices: DeviceService,
        audit: AuditService,
        cli_path: str,
    ) -> None:
        self.database = database
        self.adb = adb
        self.devices = devices
        self.audit = audit
        self.cli_path = cli_path
        self.repository = EnvironmentRepository()

    def list(self, device_id: str | None = None) -> list[Environment]:
        if device_id:
            self.devices.get(device_id)
        with self.database.session() as session:
            return self.repository.list(session, device_id)

    async def create(self, payload: EnvironmentCreate) -> Environment:
        device = self._ready_device(payload.device_id)
        await self._ensure_available(device)
        with self.database.session() as session:
            if self.repository.get_by_profile(session, payload.device_id, payload.profile):
                raise DuplicateEnvironmentError(payload.profile)
            environment = self.repository.add(
                session,
                Environment(
                    device_id=payload.device_id,
                    name=payload.name,
                    profile=payload.profile,
                    default_user=payload.default_user,
                ),
            )
        self.audit.record(
            "environment.created",
            f"Added Linux Deploy profile {environment.profile}.",
            environment.device_id,
        )
        return await self.refresh(environment.id)

    async def refresh(self, environment_id: str) -> Environment:
        environment = self.get(environment_id)
        device = self._ready_device(environment.device_id)
        try:
            output = await self._run(device, environment.profile, "status")
            status = self._status_from_output(output)
        except ADBError as exc:
            return self._update_status(environment_id, EnvironmentStatus.ERROR, str(exc))
        return self._update_status(environment_id, status, output)

    async def control(self, environment_id: str, action: str) -> tuple[Environment, str]:
        environment = self.get(environment_id)
        device = self._ready_device(environment.device_id)
        command = ("start", "-m") if action == "start" else ("stop", "-u")
        try:
            output = await self._run(device, environment.profile, *command)
        except ADBError as exc:
            failed = self._update_status(environment_id, EnvironmentStatus.ERROR, str(exc))
            self.audit.record(
                f"environment.{action}_failed",
                f"{action.title()} failed for {environment.name}.",
                environment.device_id,
                "ERROR",
            )
            return failed, str(exc)
        status = EnvironmentStatus.RUNNING if action == "start" else EnvironmentStatus.STOPPED
        updated = self._update_status(environment_id, status, output)
        self.audit.record(
            f"environment.{action}",
            f"{action.title()} completed for {environment.name}.",
            environment.device_id,
        )
        return updated, output

    async def services(self, environment_id: str) -> tuple[list[ServiceInfo], str]:
        environment = self.get(environment_id)
        device = self._ready_device(environment.device_id)
        output = await self._shell(device, environment, "service --status-all 2>&1", "root")
        services: list[ServiceInfo] = []
        for line in output.splitlines():
            match = re.match(r"\s*\[\s*([+?-])\s*]\s+(.+?)\s*$", line)
            if match:
                marker, name = match.groups()
                services.append(ServiceInfo(name=name, running=True if marker == "+" else False if marker == "-" else None, raw=line))
        return services, output

    async def control_service(self, environment_id: str, payload: ServiceActionRequest) -> str:
        environment = self.get(environment_id)
        device = self._ready_device(environment.device_id)
        command = shlex.join(["service", payload.name, payload.action])
        output = await self._shell(device, environment, command, "root")
        self.audit.record(
            f"service.{payload.action}",
            f"Ran {payload.action} for {payload.name} in {environment.name}.",
            environment.device_id,
        )
        return output

    async def terminal(self, environment_id: str, command: str, user: str | None = None) -> str:
        environment = self.get(environment_id)
        device = self._ready_device(environment.device_id)
        output = await self._shell(device, environment, command, user or environment.default_user)
        self.audit.record(
            "terminal.command",
            f"Executed a command in {environment.name} as {user or environment.default_user}.",
            environment.device_id,
        )
        return output

    def get(self, environment_id: str) -> Environment:
        with self.database.session() as session:
            environment = self.repository.get(session, environment_id)
            if environment is None:
                raise EnvironmentNotFoundError(environment_id)
            return environment

    def delete(self, environment_id: str) -> None:
        with self.database.session() as session:
            environment = self.repository.get(session, environment_id)
            if environment is None:
                raise EnvironmentNotFoundError(environment_id)
            device_id = environment.device_id
            name = environment.name
            self.repository.delete(session, environment)
        self.audit.record("environment.deleted", f"Removed environment {name}.", device_id)

    async def _ensure_available(self, device: Device) -> None:
        assert device.serial is not None
        command = f"test -x {shlex.quote(self.cli_path)} && echo available"
        output = await asyncio.to_thread(self.adb.root_shell, device.serial, command)
        if output.strip() != "available":
            raise LinuxDeployUnavailableError(
                f"Linux Deploy CLI was not found at {self.cli_path}. Check Settings → PATH variable in Linux Deploy."
            )

    async def _run(self, device: Device, profile: str, *arguments: str) -> str:
        await self._ensure_available(device)
        assert device.serial is not None
        command = shlex.join([self.cli_path, "-p", profile, *arguments])
        return await asyncio.to_thread(self.adb.root_shell, device.serial, command)

    async def _shell(self, device: Device, environment: Environment, command: str, user: str) -> str:
        await self._ensure_available(device)
        assert device.serial is not None
        remote = shlex.join(
            [self.cli_path, "-p", environment.profile, "shell", "-u", user, command]
        )
        return await asyncio.to_thread(self.adb.root_shell, device.serial, remote)

    def _ready_device(self, device_id: str) -> Device:
        try:
            device = self.devices.get(device_id)
        except DeviceNotFoundError:
            raise
        if device.connection_status != "CONNECTED" or not device.serial:
            raise ADBError("Connect the Android device before managing Linux Deploy.")
        if device.root_available is not True:
            raise ADBError("Linux Deploy management requires confirmed root access.")
        return device

    def _update_status(
        self,
        environment_id: str,
        status: EnvironmentStatus,
        output: str,
    ) -> Environment:
        with self.database.session() as session:
            environment = self.repository.get(session, environment_id)
            if environment is None:
                raise EnvironmentNotFoundError(environment_id)
            environment.status = status.value
            environment.last_output = output[-10000:]
            session.flush()
            return environment

    @staticmethod
    def _status_from_output(output: str) -> EnvironmentStatus:
        normalized = output.lower()
        if any(marker in normalized for marker in ("stopped", "not running", "unmounted")):
            return EnvironmentStatus.STOPPED
        if any(marker in normalized for marker in ("running", "started", "mounted")):
            return EnvironmentStatus.RUNNING
        return EnvironmentStatus.UNKNOWN
