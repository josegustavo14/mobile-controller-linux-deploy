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
