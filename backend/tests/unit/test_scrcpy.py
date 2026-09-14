from io import BytesIO

from backend.app.services.scrcpy import ScrcpyService


class FakeAudit:
    def record(self, *args, **kwargs) -> None:
        pass


class FakeProcess:
    def __init__(self) -> None:
        self.running = True

    def poll(self):
        return None if self.running else 0

    def terminate(self) -> None:
        self.running = False

    def wait(self, timeout=None) -> int:
        self.running = False
        return 0

    def kill(self) -> None:
        self.running = False


def test_scrcpy_reuses_the_configured_adb_server(monkeypatch) -> None:
    service = ScrcpyService(FakeAudit(), "/opt/scrcpy/scrcpy", "/opt/adb", 5038, 6080)  # type: ignore[arg-type]
    environments: list[dict[str, str]] = []
    commands: list[list[str]] = []

    def fake_spawn(command: list[str], environment: dict[str, str]) -> None:
        commands.append(command)
        environments.append(environment)
        service.processes.append(FakeProcess())  # type: ignore[arg-type]

    monkeypatch.setattr(service, "_check_runtime", lambda: None)
    monkeypatch.setattr(service, "_wait_for_x_server", lambda: None)
    monkeypatch.setattr(service, "_spawn", fake_spawn)
    monkeypatch.setattr("backend.app.services.scrcpy.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("backend.app.services.scrcpy.Path.open", lambda *_args, **_kwargs: BytesIO())

    status = service.start("device-id", "192.0.2.2:5555")

    assert status.running is True
    assert all(item["ADB_SERVER_SOCKET"] == "tcp:127.0.0.1:5038" for item in environments)
    assert all(item["ANDROID_ADB_SERVER_PORT"] == "5038" for item in environments)
    assert "-no6" in commands[1]
    service.stop()
