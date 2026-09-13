from __future__ import annotations

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
