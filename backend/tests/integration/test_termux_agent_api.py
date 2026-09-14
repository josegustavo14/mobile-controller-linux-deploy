from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.adb import FakeADBClient


def test_termux_agent_discovers_sensors_and_reads_selected_data(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'termux-agent.db'}", FakeADBClient())
    with TestClient(app) as client:
        device_id = client.post(
            "/api/devices",
            json={"name": "Personal phone", "host": "192.168.15.98"},
        ).json()["id"]

        def fake_request(_device_id: str, path: str):
            if path == "/v1/capabilities":
                return {
                    "sensors": ["BMI160 Accelerometer", "Light sensor", "BMI160 Accelerometer"],
                    "apis": ["wifi", "battery"],
                }
            if path.startswith("/v1/sensor"):
                return {"BMI160 Accelerometer": {"values": [0.1, 9.8, 0.2]}}
            return {"percentage": 82, "status": "DISCHARGING"}

        app.state.termux_agent_service._request = fake_request  # type: ignore[method-assign]

        capabilities = client.get(f"/api/termux-agent/{device_id}/capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json() == {
            "sensors": ["BMI160 Accelerometer", "Light sensor"],
            "apis": ["battery", "wifi"],
        }

        sensor = client.post(
            f"/api/termux-agent/{device_id}/sensor",
            json={"name": "BMI160 Accelerometer"},
        )
        assert sensor.status_code == 200
        assert sensor.json()["source"] == "BMI160 Accelerometer"
        assert sensor.json()["payload"]["BMI160 Accelerometer"]["values"][1] == 9.8

        battery = client.post(
            f"/api/termux-agent/{device_id}/api",
            json={"name": "battery"},
        )
        assert battery.status_code == 200
        assert battery.json()["payload"]["percentage"] == 82
