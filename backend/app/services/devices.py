from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from backend.app.core.database import Database
from backend.app.models.device import Device
from backend.app.repositories.devices import DeviceRepository
from backend.app.repositories.environments import EnvironmentRepository
from backend.app.schemas.device import ConnectionStatus, DeviceCreate, DeviceUpdate, PairRequest
from backend.app.services.adb import ADBClient, ADBError
from backend.app.services.android import AndroidDetails, AndroidService
from backend.app.services.audit import AuditService

logger = logging.getLogger(__name__)


class DeviceNotFoundError(LookupError):
    pass


class DuplicateDeviceError(ValueError):
    pass


class DeviceService:
    def __init__(self, database: Database, adb: ADBClient, audit: AuditService) -> None:
        self.database = database
        self.adb = adb
        self.repository = DeviceRepository()
        self.environments = EnvironmentRepository()
        self.android = AndroidService(adb)
        self.audit = audit

    def list(self) -> list[Device]:
        with self.database.session() as session:
            return self.repository.list(session)

    def get(self, device_id: str) -> Device:
        with self.database.session() as session:
            return self._required(session, device_id)

    def create(self, payload: DeviceCreate) -> Device:
        with self.database.session() as session:
            if self.repository.get_by_name(session, payload.name) or self.repository.get_by_endpoint(session, payload.host, payload.port):
                raise DuplicateDeviceError(payload.name)
            device = self.repository.add(session, Device(name=payload.name, host=payload.host, port=payload.port))
        self.audit.record("device.created", f"Added {device.name} at {device.host}:{device.port}.", device.id)
        return device

    def update(self, device_id: str, payload: DeviceUpdate) -> Device:
        with self.database.session() as session:
            device = self._required(session, device_id)
            named = self.repository.get_by_name(session, payload.name)
            endpoint = self.repository.get_by_endpoint(session, payload.host, payload.port)
            if (named and named.id != device_id) or (endpoint and endpoint.id != device_id):
                raise DuplicateDeviceError(payload.name)
            endpoint_changed = device.host != payload.host or device.port != payload.port
            device.name = payload.name
            device.host = payload.host
            device.port = payload.port
            if endpoint_changed:
                device.serial = None
                device.connection_status = ConnectionStatus.DISCONNECTED.value
                device.last_error = None
            session.flush()
        self.audit.record("device.updated", f"Updated connection settings for {device.name}.", device.id)
        return device

    async def pair(self, payload: PairRequest) -> str:
        try:
            output = await asyncio.to_thread(
                self.adb.pair,
                f"{payload.host}:{payload.port}",
                payload.pairing_code,
            )
            self.audit.record("adb.paired", f"Paired wireless debugging with {payload.host}:{payload.port}.")
            return output
        except ADBError as exc:
            self.audit.record("adb.pair_failed", f"Wireless pairing failed for {payload.host}:{payload.port}.", level="ERROR")
            raise ADBError(
                "Unable to pair with Android. Confirm the pairing address, port, and current six-digit code."
            ) from exc

    async def connect(self, device_id: str) -> Device:
        device = self.get(device_id)
        self._set_status(device_id, ConnectionStatus.CONNECTING, None)
        try:
            serial = await asyncio.to_thread(self.adb.connect, f"{device.host}:{device.port}")
            details = await asyncio.to_thread(self.android.inspect, serial)
        except ADBError as exc:
            logger.warning("device_connection_failed device_id=%s", device_id)
            self.audit.record("device.connect_failed", f"Connection failed for {device.name}.", device_id, "ERROR")
            return self._set_status(device_id, ConnectionStatus.ERROR, self._friendly_error(device, exc))
        connected = self._apply_details(device_id, serial, details)
        self.audit.record("device.connected", f"Connected to {device.name} over Wi-Fi.", device_id)
        return connected

    async def disconnect(self, device_id: str) -> Device:
        device = self.get(device_id)
        if device.serial:
            try:
                await asyncio.to_thread(self.adb.disconnect, device.serial)
            except ADBError as exc:
                return self._set_status(device_id, ConnectionStatus.ERROR, self._friendly_error(device, exc))
        disconnected = self._set_status(device_id, ConnectionStatus.DISCONNECTED, None)
        self.audit.record("device.disconnected", f"Disconnected {device.name}.", device_id)
        return disconnected

    async def reboot(self, device_id: str) -> Device:
        device = self.get(device_id)
        if not device.serial:
            raise ADBError("Connect the device before requesting a reboot.")
        try:
            await asyncio.to_thread(self.adb.reboot, device.serial)
        except ADBError as exc:
            return self._set_status(device_id, ConnectionStatus.ERROR, self._friendly_error(device, exc))
        rebooting = self._set_status(device_id, ConnectionStatus.RECONNECTING, None)
        self.audit.record("device.rebooted", f"Requested a reboot for {device.name}.", device_id)
        return rebooting

    async def delete(self, device_id: str) -> None:
        device = self.get(device_id)
        if device.serial:
            try:
                await asyncio.to_thread(self.adb.disconnect, device.serial)
            except ADBError:
                logger.info("device_delete_disconnect_failed device_id=%s", device_id)
        with self.database.session() as session:
            self.environments.delete_for_device(session, device_id)
            self.repository.delete(session, self._required(session, device_id))
        self.audit.record("device.deleted", f"Removed {device.name} from the registry.", device_id)

    async def refresh(self, device_id: str) -> Device:
        device = self.get(device_id)
        if not device.serial:
            return await self.connect(device_id)
        try:
            details = await asyncio.to_thread(self.android.inspect, device.serial)
        except ADBError as exc:
            return self._set_status(device_id, ConnectionStatus.ERROR, self._friendly_error(device, exc))
        refreshed = self._apply_details(device_id, device.serial, details)
        self.audit.record("device.refreshed", f"Refreshed details for {device.name}.", device_id)
        return refreshed

    def _apply_details(self, device_id: str, serial: str, details: AndroidDetails) -> Device:
        with self.database.session() as session:
            device = self._required(session, device_id)
            device.serial = serial
            device.connection_status = ConnectionStatus.CONNECTED.value
            device.last_error = None
            device.details_updated_at = datetime.now(UTC)
            for field, value in details.__dict__.items():
                setattr(device, field, value)
            session.flush()
            logger.info("device_connected device_id=%s", device_id)
            return device

    def _set_status(self, device_id: str, status: ConnectionStatus, error: str | None) -> Device:
        with self.database.session() as session:
            device = self._required(session, device_id)
            device.connection_status = status.value
            device.last_error = error
            session.flush()
            return device

    def _required(self, session, device_id: str) -> Device:
        device = self.repository.get(session, device_id)
        if device is None:
            raise DeviceNotFoundError(device_id)
        return device

    @staticmethod
    def _friendly_error(device: Device, error: ADBError) -> str:
        detail = str(error).lower()
        if "unauthorized" in detail:
            return "Android rejected this ADB key. Unlock the device and approve the debugging authorization prompt."
        if "offline" in detail:
            return "Android is visible but offline. Toggle wireless debugging and connect again."
        return (
            f"Unable to connect to Android at {device.host}:{device.port}. "
            "Check that ADB over TCP is enabled, the device is online, and the network address is reachable."
        )
