from __future__ import annotations

import os
import secrets
import shutil
import string
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from backend.app.services.audit import AuditService


class ScrcpyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScrcpyStatus:
    running: bool
    device_id: str | None
    serial: str | None
    viewer_port: int
    password: str | None
    message: str


class ScrcpyService:
    """Owns the single scrcpy + Xvfb + noVNC session exposed by the appliance."""

    def __init__(
        self,
        audit: AuditService,
        scrcpy_path: str,
        adb_path: str,
        adb_server_port: int,
        viewer_port: int,
    ) -> None:
        self.audit = audit
        self.scrcpy_path = scrcpy_path
        self.adb_path = adb_path
        self.adb_server_port = adb_server_port
        self.viewer_port = viewer_port
        self.processes: list[subprocess.Popen[bytes]] = []
        self.log_handle: BinaryIO | None = None
        self.device_id: str | None = None
        self.serial: str | None = None
        self.password: str | None = None

    def start(self, device_id: str, serial: str) -> ScrcpyStatus:
        self.stop(record_audit=False)
        self._check_runtime()
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(8))
        log_path = Path("/tmp/android-server-manager-scrcpy.log")
        self.log_handle = log_path.open("ab", buffering=0)
        environment = os.environ.copy()
        environment.update(
            {
                "DISPLAY": ":99",
                "ADB": self.adb_path,
                "ADB_SERVER_SOCKET": f"tcp:127.0.0.1:{self.adb_server_port}",
                "ANDROID_ADB_SERVER_PORT": str(self.adb_server_port),
                "HOME": os.environ.get("HOME", "/app/data"),
            }
        )
        try:
            self._spawn(["Xvfb", ":99", "-screen", "0", "1280x800x24", "-nolisten", "tcp"], environment)
            self._wait_for_x_server()
            self._spawn(
                [
                    "x11vnc",
                    "-display",
                    ":99",
                    "-rfbport",
                    "5900",
                    "-listen",
                    "localhost",
                    "-no6",
                    "-forever",
                    "-shared",
                    "-passwd",
                    password,
                    "-noxdamage",
                ],
                environment,
            )
            self._spawn(
                [
                    "websockify",
                    "--web=/usr/share/novnc",
                    f"0.0.0.0:{self.viewer_port}",
                    "127.0.0.1:5900",
                ],
                environment,
            )
            self._spawn(
                [
                    self.scrcpy_path,
                    "--serial",
                    serial,
                    "--no-audio",
                    "--max-size=1080",
                    "--video-bit-rate=4M",
                    "--window-title=Android Server Manager",
                    "--stay-awake",
                ],
                environment,
            )
            time.sleep(1)
            if self.processes[-1].poll() is not None:
                raise ScrcpyError(self._failure_message())
        except (OSError, ScrcpyError) as exc:
            self.stop(record_audit=False)
            raise ScrcpyError(str(exc) or "scrcpy could not start.") from exc
        self.device_id = device_id
        self.serial = serial
        self.password = password
        self.audit.record("scrcpy.started", "Started a browser-accessible scrcpy session.", device_id)
        return self.status()

    def stop(self, record_audit: bool = True) -> ScrcpyStatus:
        previous_device_id = self.device_id
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(self.processes):
            if process.poll() is None:
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
        self.processes.clear()
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None
        self.device_id = None
        self.serial = None
        self.password = None
        if record_audit and previous_device_id:
            self.audit.record("scrcpy.stopped", "Stopped the scrcpy session.", previous_device_id)
        return self.status()

    def status(self) -> ScrcpyStatus:
        running = bool(self.processes) and all(process.poll() is None for process in self.processes)
        message = "scrcpy is ready for browser control." if running else "No scrcpy session is running."
        if self.processes and not running:
            message = self._failure_message()
        return ScrcpyStatus(
            running=running,
            device_id=self.device_id if running else None,
            serial=self.serial if running else None,
            viewer_port=self.viewer_port,
            password=self.password if running else None,
            message=message,
        )

    def _spawn(self, command: list[str], environment: dict[str, str]) -> None:
        assert self.log_handle is not None
        self.processes.append(
            subprocess.Popen(
                command,
                env=environment,
                stdout=self.log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        )

    def _wait_for_x_server(self) -> None:
        socket = Path("/tmp/.X11-unix/X99")
        for _ in range(30):
            if socket.exists():
                return
            if self.processes[0].poll() is not None:
                break
            time.sleep(0.1)
        raise ScrcpyError("The virtual display required by scrcpy did not start.")

    def _check_runtime(self) -> None:
        required = ["Xvfb", "x11vnc", "websockify"]
        missing = [command for command in required if shutil.which(command) is None]
        if not Path(self.scrcpy_path).is_file():
            missing.append(self.scrcpy_path)
        if missing:
            raise ScrcpyError(f"scrcpy web runtime is incomplete: {', '.join(missing)}")

    @staticmethod
    def _failure_message() -> str:
        path = Path("/tmp/android-server-manager-scrcpy.log")
        if not path.is_file():
            return "scrcpy stopped unexpectedly."
        output = path.read_text(errors="replace")[-3000:].strip()
        return output or "scrcpy stopped unexpectedly."
