from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import Protocol


class ADBError(RuntimeError):
    """A user-safe failure from the ADB transport."""


class ADBTimeoutError(ADBError):
    """ADB did not respond before the configured deadline."""


@dataclass(frozen=True)
class ADBDevice:
    serial: str
    state: str


class ADBClient(Protocol):
    def list_devices(self) -> list[ADBDevice]: ...
    def pair(self, address: str, pairing_code: str) -> str: ...
    def connect(self, address: str) -> str: ...
    def disconnect(self, serial: str) -> None: ...
    def shell(self, serial: str, command: str) -> str: ...
    def root_shell(self, serial: str, command: str) -> str: ...
    def screenshot(self, serial: str) -> bytes: ...
    def reboot(self, serial: str) -> None: ...


class RealADBClient:
    """The single backend boundary for Android Debug Bridge commands."""

    def __init__(self, path: str, server_port: int, timeout: float) -> None:
        self.path = path
        self.server_port = server_port
        self.timeout = timeout

    def _run(self, *args: str) -> str:
        try:
            result = subprocess.run(
                [self.path, "-P", str(self.server_port), *args],
                capture_output=True,
                check=False,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ADBTimeoutError("Android did not respond before the ADB timeout.") from exc
        except OSError as exc:
            raise ADBError("ADB is unavailable inside the application container.") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise ADBError(detail or "ADB rejected the operation.")
        return result.stdout.strip()

    def list_devices(self) -> list[ADBDevice]:
        output = self._run("devices")
        devices: list[ADBDevice] = []
        for line in output.splitlines():
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            fields = line.split()
            if len(fields) >= 2:
                devices.append(ADBDevice(serial=fields[0], state=fields[1]))
        return devices

    def connect(self, address: str) -> str:
        output = self._run("connect", address)
        if "connected to" not in output.lower() and "already connected" not in output.lower():
            raise ADBError(output or "ADB could not connect to the Android device.")
        return output.rsplit(" ", maxsplit=1)[-1]

    def pair(self, address: str, pairing_code: str) -> str:
        output = self._run("pair", address, pairing_code)
        if "successfully paired" not in output.lower():
            raise ADBError(output or "ADB could not pair with the Android device.")
        return output

    def disconnect(self, serial: str) -> None:
        self._run("disconnect", serial)

    def shell(self, serial: str, command: str) -> str:
        return self._run("-s", serial, "shell", command)

    def root_shell(self, serial: str, command: str) -> str:
        return self.shell(serial, f"su -c {shlex.quote(command)}")

    def screenshot(self, serial: str) -> bytes:
        try:
            result = subprocess.run(
                [self.path, "-P", str(self.server_port), "-s", serial, "exec-out", "screencap", "-p"],
                capture_output=True,
                check=False,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ADBTimeoutError("Android did not return a screenshot before the ADB timeout.") from exc
        except OSError as exc:
            raise ADBError("ADB is unavailable inside the application container.") from exc
        if result.returncode != 0:
            detail = result.stderr.decode(errors="replace").strip()
            raise ADBError(detail or "Android could not capture the screen.")
        if not result.stdout.startswith(b"\x89PNG"):
            raise ADBError("Android returned an invalid screenshot.")
        return result.stdout

    def reboot(self, serial: str) -> None:
        self._run("-s", serial, "reboot")


class FakeADBClient:
    """Deterministic ADB test double; it never invokes a local executable."""

    def __init__(self, devices: list[ADBDevice] | None = None, commands: dict[str, str] | None = None, root: bool = True) -> None:
        self.devices = devices or []
        self.commands = commands or {}
        self.root = root
        self.connected: list[str] = []
        self.paired: list[tuple[str, str]] = []
        self.disconnected: list[str] = []
        self.rebooted: list[str] = []
        self.error: ADBError | None = None
        self.screenshot_data = b"\x89PNG\r\n\x1a\n"

    def _check(self) -> None:
        if self.error:
            raise self.error

    def list_devices(self) -> list[ADBDevice]:
        self._check()
        return self.devices

    def connect(self, address: str) -> str:
        self._check()
        self.connected.append(address)
        if not any(device.serial == address for device in self.devices):
            self.devices.append(ADBDevice(serial=address, state="device"))
        return address

    def pair(self, address: str, pairing_code: str) -> str:
        self._check()
        self.paired.append((address, pairing_code))
        return f"Successfully paired to {address}"

    def disconnect(self, serial: str) -> None:
        self._check()
        self.disconnected.append(serial)

    def shell(self, serial: str, command: str) -> str:
        self._check()
        if command not in self.commands:
            raise ADBError(f"Unexpected fake command: {command}")
        return self.commands[command]

    def root_shell(self, serial: str, command: str) -> str:
        self._check()
        if not self.root:
            raise ADBError("Root access is not available.")
        if command == "id -u":
            return "0"
        return self.shell(serial, command)

    def screenshot(self, serial: str) -> bytes:
        self._check()
        return self.screenshot_data

    def reboot(self, serial: str) -> None:
        self._check()
        self.rebooted.append(serial)
