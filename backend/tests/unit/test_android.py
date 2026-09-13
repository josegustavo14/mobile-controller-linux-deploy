from backend.app.services.adb import FakeADBClient
from backend.app.services.android import AndroidService


def test_android_service_collects_properties_and_root_status() -> None:
    fake = FakeADBClient(
        commands={
            "getprop ro.product.manufacturer": "samsung",
            "getprop ro.product.model": "SM-G985F",
            "getprop ro.build.version.release": "13",
            "getprop ro.build.version.sdk": "33",
            "getprop ro.hardware": "exynos990",
            "getprop ro.product.cpu.abi": "arm64-v8a",
            "getprop ro.build.display.id": "TP1A.220624.014",
            "uname -r": "4.19.113-android12",
        },
        root=True,
    )

    details = AndroidService(fake).inspect("192.168.15.98:5555")

    assert details.model == "SM-G985F"
    assert details.cpu_abi == "arm64-v8a"
    assert details.root_available is True


def test_android_service_reports_missing_root_without_failing_inspection() -> None:
    fake = FakeADBClient(
        commands={
            "getprop ro.product.manufacturer": "Google",
            "getprop ro.product.model": "Pixel",
            "getprop ro.build.version.release": "13",
            "getprop ro.build.version.sdk": "33",
            "getprop ro.hardware": "tensor",
            "getprop ro.product.cpu.abi": "arm64-v8a",
            "getprop ro.build.display.id": "build",
            "uname -r": "5.10",
        },
        root=False,
    )

    assert AndroidService(fake).inspect("pixel:5555").root_available is False
