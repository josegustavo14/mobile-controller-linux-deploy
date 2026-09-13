import subprocess

import pytest

from backend.app.services.adb import ADBError, ADBTimeoutError, RealADBClient


def test_list_devices_parses_connected_and_offline_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RealADBClient("adb", 5037, 5)
    monkeypatch.setattr(
        client,
        "_run",
        lambda *args: "List of devices attached\n192.168.15.98:5555\tdevice\nserial-offline\toffline\n",
    )

    assert [(item.serial, item.state) for item in client.list_devices()] == [
        ("192.168.15.98:5555", "device"),
        ("serial-offline", "offline"),
    ]


def test_connect_rejects_unexpected_adb_output(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RealADBClient("adb", 5037, 5)
    monkeypatch.setattr(client, "_run", lambda *args: "failed to connect")

    with pytest.raises(ADBError, match="failed to connect"):
        client.connect("192.168.15.98:5555")


def test_pair_accepts_success_and_rejects_failed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RealADBClient("adb", 5037, 5)
    monkeypatch.setattr(client, "_run", lambda *args: "Successfully paired to 192.168.15.98:37123")

    assert "Successfully paired" in client.pair("192.168.15.98:37123", "123456")

    monkeypatch.setattr(client, "_run", lambda *args: "Failed: wrong password")
    with pytest.raises(ADBError, match="wrong password"):
        client.pair("192.168.15.98:37123", "654321")


def test_timeout_is_exposed_as_safe_adb_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RealADBClient("adb", 5037, 5)

    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("adb", 5)

    monkeypatch.setattr(subprocess, "run", timed_out)

    with pytest.raises(ADBTimeoutError, match="did not respond"):
        client.list_devices()


def test_root_shell_preserves_nested_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RealADBClient("adb", 5037, 5)
    received: list[tuple[str, ...]] = []

    def capture(*args: str) -> str:
        received.append(args)
        return "ok"

    monkeypatch.setattr(client, "_run", capture)
    command = "printf '%s' \"$HOME\""

    assert client.root_shell("192.168.15.98:5555", command) == "ok"
    assert received == [
        (
            "-s",
            "192.168.15.98:5555",
            "shell",
            "su -c 'printf '\"'\"'%s'\"'\"' \"$HOME\"'",
        )
    ]
