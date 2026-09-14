from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.adb import FakeADBClient
from backend.app.services.updater import UpdateStatus


def test_update_status_and_apply_are_exposed_without_leaking_token(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'update.db'}", FakeADBClient())
    app.state.updater_service.status = lambda current: UpdateStatus(  # type: ignore[method-assign]
        current_version=current,
        latest_version="1.4.0",
        update_available=True,
        updater_enabled=True,
        message="Version 1.4.0 is ready to install.",
    )
    applied: list[bool] = []
    app.state.updater_service.apply = lambda: applied.append(True)  # type: ignore[method-assign]

    with TestClient(app) as client:
        status = client.get("/api/update/status")
        assert status.status_code == 200
        assert status.json() == {
            "current_version": "1.3.0",
            "latest_version": "1.4.0",
            "update_available": True,
            "updater_enabled": True,
            "message": "Version 1.4.0 is ready to install.",
        }
        assert "token" not in status.text.lower()

        response = client.post("/api/update/apply")
        assert response.status_code == 202
        assert applied == [True]
