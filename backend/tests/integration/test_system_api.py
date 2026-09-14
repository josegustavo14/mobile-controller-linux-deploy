from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.adb import FakeADBClient


def test_dashboard_and_audit_log_reflect_device_activity(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'system.db'}", FakeADBClient())
    with TestClient(app) as client:
        created = client.post("/api/devices", json={"name": "node", "host": "10.0.0.8"})
        assert created.status_code == 201

        dashboard = client.get("/api/system/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["total_devices"] == 1
        assert dashboard.json()["recent_activity"][0]["action"] == "device.created"

        logs = client.get("/api/system/logs")
        assert logs.status_code == 200
        assert logs.json()[0]["device_id"] == created.json()["id"]


def test_admin_token_protects_control_plane_apis(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'auth.db'}", FakeADBClient())
    app.state.settings.admin_token = "correct-horse-battery-staple"
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/devices").status_code == 401
        assert client.get("/api/devices", headers={"Authorization": "Bearer wrong"}).status_code == 401
        authorized = client.get(
            "/api/devices",
            headers={"Authorization": "Bearer correct-horse-battery-staple"},
        )
        assert authorized.status_code == 200


def test_system_info_does_not_expose_admin_token(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'info.db'}", FakeADBClient())
    with TestClient(app) as client:
        body = client.get("/api/system/info").json()
        assert body["version"] == "1.1.0"
        assert body["database_backend"] == "sqlite"
        assert "admin_token" not in body
