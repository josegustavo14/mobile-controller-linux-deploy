from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.adb import ADBError, FakeADBClient


def fake_android() -> FakeADBClient:
    return FakeADBClient(
        commands={
            "getprop ro.product.manufacturer": "samsung",
            "getprop ro.product.model": "SM-G985F",
            "getprop ro.build.version.release": "13",
            "getprop ro.build.version.sdk": "33",
            "getprop ro.hardware": "exynos990",
            "getprop ro.product.cpu.abi": "arm64-v8a",
            "getprop ro.build.display.id": "TP1A.220624.014",
            "uname -r": "4.19.113-android12",
            "dumpsys battery": """AC powered: false
USB powered: false
Wireless powered: false
status: 3
level: 82
temperature: 315""",
            "df -h /data /sdcard 2>/dev/null": "Filesystem Size Used Avail Use% Mounted on\n/dev/block/dm-8 110G 64G 46G 59% /data",
            "ip -f inet addr show 2>/dev/null": "inet 192.168.15.98/24 scope global wlan0\ninet 100.70.80.90/32 scope global tun0",
            "cat /proc/uptime": "12345.67 111.20",
            "dumpsys power": "mWakefulness=Awake",
            "pm path com.termux": "package:/data/app/com.termux/base.apk",
            "pm path com.tailscale.ipn": "package:/data/app/com.tailscale.ipn/base.apk",
            "pm list packages -3": "package:com.whatsapp\npackage:com.termux",
            "echo personal-phone": "personal-phone",
            "input keyevent KEYCODE_HOME": "",
            "monkey -p com.termux -c android.intent.category.LAUNCHER 1": "Events injected: 1",
            "monkey -p com.whatsapp -c android.intent.category.LAUNCHER 1": "Events injected: 1",
        }
    )


def test_register_connect_refresh_and_disconnect_a_device(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'devices.db'}", fake_android())
    with TestClient(app) as client:
        created = client.post("/api/devices", json={"name": "S20+", "host": "192.168.15.98", "port": 5555})
        assert created.status_code == 201
        device_id = created.json()["id"]

        connected = client.post(f"/api/devices/{device_id}/connect")
        assert connected.status_code == 200
        body = connected.json()["device"]
        assert body["connection_status"] == "CONNECTED"
        assert body["model"] == "SM-G985F"
        assert body["root_available"] is True

        refreshed = client.post(f"/api/devices/{device_id}/refresh")
        assert refreshed.status_code == 200
        assert refreshed.json()["kernel"] == "4.19.113-android12"

        disconnected = client.post(f"/api/devices/{device_id}/disconnect")
        assert disconnected.json()["device"]["connection_status"] == "DISCONNECTED"


def test_duplicate_name_and_connection_error_have_human_api_responses(tmp_path) -> None:
    fake = fake_android()
    app = create_app(f"sqlite:///{tmp_path / 'errors.db'}", fake)
    with TestClient(app) as client:
        first = client.post("/api/devices", json={"name": "S20+", "host": "100.64.0.12"})
        assert first.status_code == 201
        assert client.post("/api/devices", json={"name": "S20+", "host": "100.64.0.13"}).status_code == 409

        fake.error = ADBError("connection refused")
        failed = client.post(f"/api/devices/{first.json()['id']}/connect")
        assert failed.status_code == 200
        assert failed.json()["device"]["connection_status"] == "ERROR"
        assert "Check that ADB over TCP" in failed.json()["device"]["last_error"]


def test_pair_edit_reboot_and_delete_device(tmp_path) -> None:
    fake = fake_android()
    app = create_app(f"sqlite:///{tmp_path / 'management.db'}", fake)
    with TestClient(app) as client:
        paired = client.post(
            "/api/devices/pair",
            json={"host": "192.168.15.98", "port": 37123, "pairing_code": "123456"},
        )
        assert paired.status_code == 200
        assert fake.paired == [("192.168.15.98:37123", "123456")]

        created = client.post("/api/devices", json={"name": "S20+", "host": "192.168.15.98"})
        device_id = created.json()["id"]

        updated = client.put(
            f"/api/devices/{device_id}",
            json={"name": "Compute phone", "host": "192.168.15.99", "port": 5555},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Compute phone"

        client.post(f"/api/devices/{device_id}/connect")
        rebooted = client.post(f"/api/devices/{device_id}/reboot")
        assert rebooted.json()["device"]["connection_status"] == "RECONNECTING"
        assert fake.rebooted == ["192.168.15.99:5555"]

        deleted = client.delete(f"/api/devices/{device_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/devices/{device_id}").status_code == 404


def test_duplicate_endpoint_is_rejected(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'duplicates.db'}", fake_android())
    with TestClient(app) as client:
        assert client.post("/api/devices", json={"name": "one", "host": "10.0.0.8"}).status_code == 201
        duplicate = client.post("/api/devices", json={"name": "two", "host": "10.0.0.8"})
        assert duplicate.status_code == 409


def test_restart_clears_stale_adb_connection_state(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'restart.db'}"
    with TestClient(create_app(database_url, fake_android())) as client:
        created = client.post("/api/devices", json={"name": "S20+", "host": "192.168.15.98"})
        device_id = created.json()["id"]
        connected = client.post(f"/api/devices/{device_id}/connect")
        assert connected.json()["device"]["connection_status"] == "CONNECTED"

    with TestClient(create_app(database_url, fake_android())) as restarted_client:
        device = restarted_client.get(f"/api/devices/{device_id}").json()
        assert device["connection_status"] == "DISCONNECTED"
        assert device["serial"] is None


def test_android_console_supports_diagnostics_non_root_shell_and_controls(tmp_path) -> None:
    fake = fake_android()
    app = create_app(f"sqlite:///{tmp_path / 'console.db'}", fake)
    with TestClient(app) as client:
        device = client.post(
            "/api/devices",
            json={"name": "Personal phone", "host": "192.168.15.98"},
        ).json()
        device_id = device["id"]
        assert client.post(f"/api/devices/{device_id}/connect").status_code == 200

        diagnostics = client.get(f"/api/devices/{device_id}/diagnostics")
        assert diagnostics.status_code == 200
        assert diagnostics.json() == {
            "battery_level": 82,
            "battery_status": "Discharging",
            "charging": False,
            "temperature_c": 31.5,
            "uptime_seconds": 12345,
            "screen_state": "Awake",
            "wifi_ipv4": "192.168.15.98",
            "tailscale_ipv4": "100.70.80.90",
            "termux_installed": True,
            "tailscale_installed": True,
            "storage": "Filesystem Size Used Avail Use% Mounted on\n/dev/block/dm-8 110G 64G 46G 59% /data",
        }

        shell = client.post(
            f"/api/devices/{device_id}/shell",
            json={"command": "echo personal-phone", "root": False},
        )
        assert shell.status_code == 200
        assert shell.json() == {"output": "personal-phone", "root": False}

        action = client.post(f"/api/devices/{device_id}/actions", json={"action": "home"})
        assert action.status_code == 200

        apps = client.get(f"/api/devices/{device_id}/apps")
        assert apps.json() == {"packages": ["com.termux", "com.whatsapp"]}
        launched = client.post(
            f"/api/devices/{device_id}/apps/launch",
            json={"package": "com.whatsapp"},
        )
        assert launched.status_code == 200

        opened = client.post(f"/api/devices/{device_id}/termux/open")
        assert opened.status_code == 200

        termux_intents: list[str] = []

        def capture_termux_intent(_serial: str, command: str) -> str:
            termux_intents.append(command)
            return "Starting service"

        fake.root_shell = capture_termux_intent  # type: ignore[method-assign]
        termux = client.post(
            f"/api/devices/{device_id}/termux/run",
            json={"command": "termux-battery-status"},
        )
        assert termux.status_code == 200
        assert "com.termux.app.RunCommandService" in termux_intents[0]
        assert "termux-battery-status" in termux_intents[0]

        screenshot = client.get(f"/api/devices/{device_id}/screenshot")
        assert screenshot.status_code == 200
        assert screenshot.headers["content-type"] == "image/png"
        assert screenshot.headers["cache-control"] == "no-store"
        assert screenshot.content.startswith(b"\x89PNG")


def test_personal_phone_without_root_can_still_use_adb_shell(tmp_path) -> None:
    fake = fake_android()
    fake.root = False
    app = create_app(f"sqlite:///{tmp_path / 'non-root.db'}", fake)
    with TestClient(app) as client:
        device_id = client.post(
            "/api/devices",
            json={"name": "Stock Android", "host": "192.168.15.99"},
        ).json()["id"]
        connected = client.post(f"/api/devices/{device_id}/connect").json()["device"]
        assert connected["root_available"] is False

        shell = client.post(
            f"/api/devices/{device_id}/shell",
            json={"command": "echo personal-phone"},
        )
        assert shell.status_code == 200
        assert shell.json()["output"] == "personal-phone"

        root_shell = client.post(
            f"/api/devices/{device_id}/shell",
            json={"command": "echo personal-phone", "root": True},
        )
        assert root_shell.status_code == 502
        assert "root access is not available" in root_shell.json()["detail"]

        termux = client.post(
            f"/api/devices/{device_id}/termux/run",
            json={"command": "termux-battery-status"},
        )
        assert termux.status_code == 502
        assert "Termux blocks RUN_COMMAND" in termux.json()["detail"]
