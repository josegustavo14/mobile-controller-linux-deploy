from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.adb import FakeADBClient

CLI = "/data/user/0/ru.meefik.linuxdeploy/files/bin/linuxdeploy"


def fake_linux_deploy() -> FakeADBClient:
    return FakeADBClient(
        commands={
            "getprop ro.product.manufacturer": "samsung",
            "getprop ro.product.model": "SM-G985F",
            "getprop ro.build.version.release": "13",
            "getprop ro.build.version.sdk": "33",
            "getprop ro.hardware": "exynos990",
            "getprop ro.product.cpu.abi": "arm64-v8a",
            "getprop ro.build.display.id": "build",
            "uname -r": "4.19",
            f"test -x {CLI} && echo available": "available",
            f"{CLI} -p default status": "container is running and mounted",
            f"{CLI} -p default start -m": "started",
            f"{CLI} -p default stop -u": "stopped",
            f"{CLI} -p default shell -u root 'service --status-all 2>&1'": " [ + ] ssh\n [ - ] cron",
            f"{CLI} -p default shell -u root 'service ssh restart'": "Restarting ssh: sshd.",
            f"{CLI} -p default shell -u android 'uname -a'": "Linux localhost 4.19 arm64",
        }
    )


def connected_device(client: TestClient) -> str:
    created = client.post("/api/devices", json={"name": "S20+", "host": "192.168.1.30"})
    device_id = created.json()["id"]
    assert client.post(f"/api/devices/{device_id}/connect").status_code == 200
    return device_id


def test_linux_deploy_environment_service_and_terminal_lifecycle(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'linux-deploy.db'}", fake_linux_deploy())
    with TestClient(app) as client:
        device_id = connected_device(client)
        created = client.post(
            "/api/environments",
            json={"device_id": device_id, "name": "Debian server", "profile": "default", "default_user": "android"},
        )
        assert created.status_code == 201
        environment_id = created.json()["id"]
        assert created.json()["status"] == "RUNNING"

        started = client.post(f"/api/environments/{environment_id}/start")
        assert started.status_code == 200
        assert started.json()["environment"]["status"] == "RUNNING"

        services = client.get(f"/api/environments/{environment_id}/services")
        assert services.json()["services"] == [
            {"name": "ssh", "running": True, "raw": " [ + ] ssh"},
            {"name": "cron", "running": False, "raw": " [ - ] cron"},
        ]

        controlled = client.post(
            f"/api/environments/{environment_id}/services",
            json={"name": "ssh", "action": "restart"},
        )
        assert "Restarting ssh" in controlled.json()["output"]

        terminal = client.post(
            f"/api/environments/{environment_id}/terminal",
            json={"command": "uname -a"},
        )
        assert "Linux localhost" in terminal.json()["output"]

        stopped = client.post(f"/api/environments/{environment_id}/stop")
        assert stopped.json()["environment"]["status"] == "STOPPED"
        assert client.delete(f"/api/environments/{environment_id}").status_code == 204


def test_environment_requires_connected_rooted_device(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'offline.db'}", FakeADBClient())
    with TestClient(app) as client:
        created = client.post("/api/devices", json={"name": "offline", "host": "192.168.1.31"})
        response = client.post(
            "/api/environments",
            json={"device_id": created.json()["id"], "name": "Debian", "profile": "default"},
        )
        assert response.status_code == 502
        assert "Connect the Android device" in response.json()["detail"]


def test_deleting_device_removes_its_environments(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'cascade.db'}", fake_linux_deploy())
    with TestClient(app) as client:
        device_id = connected_device(client)
        assert client.post(
            "/api/environments",
            json={"device_id": device_id, "name": "Debian", "profile": "default"},
        ).status_code == 201
        assert client.delete(f"/api/devices/{device_id}").status_code == 204
        assert client.get("/api/environments").json() == []


def test_failed_start_persists_error_status(tmp_path) -> None:
    adb = fake_linux_deploy()
    app = create_app(f"sqlite:///{tmp_path / 'failed-start.db'}", adb)
    with TestClient(app) as client:
        device_id = connected_device(client)
        created = client.post(
            "/api/environments",
            json={"device_id": device_id, "name": "Debian", "profile": "default"},
        )
        environment_id = created.json()["id"]
        del adb.commands[f"{CLI} -p default start -m"]

        failed = client.post(f"/api/environments/{environment_id}/start")

        assert failed.status_code == 502
        environments = client.get("/api/environments").json()
        assert environments[0]["status"] == "ERROR"
        assert "Unexpected fake command" in environments[0]["last_output"]
