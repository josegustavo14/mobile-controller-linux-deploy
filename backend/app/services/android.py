from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.services.adb import ADBClient, ADBError

PROPERTY_KEYS = (
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.hardware",
    "ro.product.cpu.abi",
    "ro.build.display.id",
)


@dataclass(frozen=True)
class AndroidDetails:
    manufacturer: str | None
    model: str | None
    android_version: str | None
    sdk: str | None
    hardware: str | None
    cpu_abi: str | None
    display_id: str | None
    kernel: str | None
    root_available: bool


@dataclass(frozen=True)
class AndroidDiagnostics:
    battery_level: int | None
    battery_status: str | None
    charging: bool | None
    temperature_c: float | None
    uptime_seconds: int | None
    screen_state: str | None
    wifi_ipv4: str | None
    tailscale_ipv4: str | None
    termux_installed: bool
    tailscale_installed: bool
    storage: str


class AndroidService:
    def __init__(self, adb: ADBClient) -> None:
        self.adb = adb

    def inspect(self, serial: str) -> AndroidDetails:
        properties = {key: self.adb.shell(serial, f"getprop {key}").strip() or None for key in PROPERTY_KEYS}
        kernel = self.adb.shell(serial, "uname -r").strip() or None
        try:
            root_available = self.adb.root_shell(serial, "id -u").strip() == "0"
        except ADBError:
            root_available = False
        return AndroidDetails(
            manufacturer=properties["ro.product.manufacturer"],
            model=properties["ro.product.model"],
            android_version=properties["ro.build.version.release"],
            sdk=properties["ro.build.version.sdk"],
            hardware=properties["ro.hardware"],
            cpu_abi=properties["ro.product.cpu.abi"],
            display_id=properties["ro.build.display.id"],
            kernel=kernel,
            root_available=root_available,
        )

    def diagnostics(self, serial: str) -> AndroidDiagnostics:
        battery = self.adb.shell(serial, "dumpsys battery")
        storage = self.adb.shell(serial, "df -h /data /sdcard 2>/dev/null")
        network = self.adb.shell(serial, "ip -f inet addr show 2>/dev/null")
        uptime = self.adb.shell(serial, "cat /proc/uptime")
        power = self.adb.shell(serial, "dumpsys power")
        termux = self.adb.shell(serial, "pm path com.termux")
        tailscale = self.adb.shell(serial, "pm path com.tailscale.ipn")

        level = self._integer_field(battery, "level")
        status_code = self._integer_field(battery, "status")
        temperature = self._integer_field(battery, "temperature")
        status_labels = {1: "Unknown", 2: "Charging", 3: "Discharging", 4: "Not charging", 5: "Full"}
        powered = re.search(r"(?:AC|USB|Wireless) powered:\s*true", battery, re.IGNORECASE)
        addresses = re.findall(r"\binet\s+(\d+\.\d+\.\d+\.\d+)/", network)
        tailscale_ipv4 = next((address for address in addresses if self._is_tailscale(address)), None)
        wifi_ipv4 = next(
            (
                address
                for address in addresses
                if address != "127.0.0.1" and address != tailscale_ipv4 and self._is_private(address)
            ),
            None,
        )
        uptime_match = re.match(r"\s*(\d+(?:\.\d+)?)", uptime)
        screen_match = re.search(r"(?:mWakefulness=|Wakefulness:\s*)(\w+)", power)
        return AndroidDiagnostics(
            battery_level=level,
            battery_status=status_labels.get(status_code),
            charging=bool(powered) if powered or status_code is not None else None,
            temperature_c=temperature / 10 if temperature is not None else None,
            uptime_seconds=int(float(uptime_match.group(1))) if uptime_match else None,
            screen_state=screen_match.group(1) if screen_match else None,
            wifi_ipv4=wifi_ipv4,
            tailscale_ipv4=tailscale_ipv4,
            termux_installed=termux.strip().startswith("package:"),
            tailscale_installed=tailscale.strip().startswith("package:"),
            storage=storage,
        )

    @staticmethod
    def _integer_field(output: str, name: str) -> int | None:
        match = re.search(rf"^\s*{re.escape(name)}:\s*(-?\d+)", output, re.MULTILINE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_tailscale(address: str) -> bool:
        octets = [int(value) for value in address.split(".")]
        return octets[0] == 100 and 64 <= octets[1] <= 127

    @staticmethod
    def _is_private(address: str) -> bool:
        first, second, *_ = [int(value) for value in address.split(".")]
        return first == 10 or (first == 172 and 16 <= second <= 31) or (first == 192 and second == 168)
