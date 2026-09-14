#!/data/data/com.termux/files/usr/bin/python
"""Read-only Termux:API bridge for Android Server Manager."""

from __future__ import annotations

import hmac
import json
import os
import shutil
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("ASM_AGENT_HOST", "0.0.0.0")
PORT = int(os.environ.get("ASM_AGENT_PORT", "8765"))
TOKEN = os.environ.get("ASM_AGENT_TOKEN", "")
READ_ONLY_APIS = {
    "battery": ["termux-battery-status"],
    "wifi": ["termux-wifi-connectioninfo"],
    "location": ["termux-location", "-p", "network", "-r", "once"],
    "camera": ["termux-camera-info"],
    "audio": ["termux-audio-info"],
}


def run_json(command: list[str], timeout: int = 20):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"{command[0]} failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{command[0]} returned invalid JSON") from exc


def available_sensors() -> list[str]:
    payload = run_json(["termux-sensor", "-l"])
    sensors = payload.get("sensors", []) if isinstance(payload, dict) else []
    return sorted({value for value in sensors if isinstance(value, str)})


class AgentHandler(BaseHTTPRequestHandler):
    server_version = "AndroidServerManagerTermuxAgent/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "invalid agent token"})
            return
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/v1/health":
                self._send(HTTPStatus.OK, {"status": "ok"})
                return
            if parsed.path == "/v1/capabilities":
                apis = [name for name, command in READ_ONLY_APIS.items() if shutil.which(command[0])]
                sensors = available_sensors() if shutil.which("termux-sensor") else []
                self._send(HTTPStatus.OK, {"sensors": sensors, "apis": apis})
                return
            if parsed.path == "/v1/sensor":
                requested = parse_qs(parsed.query).get("name", [""])[0]
                if requested not in available_sensors():
                    self._send(HTTPStatus.BAD_REQUEST, {"error": "sensor is not available"})
                    return
                self._send(HTTPStatus.OK, run_json(["termux-sensor", "-s", requested, "-n", "1"]))
                return
            if parsed.path.startswith("/v1/api/"):
                name = parsed.path.removeprefix("/v1/api/")
                command = READ_ONLY_APIS.get(name)
                if command is None or shutil.which(command[0]) is None:
                    self._send(HTTPStatus.NOT_FOUND, {"error": "API is not available"})
                    return
                self._send(HTTPStatus.OK, run_json(command))
                return
            self._send(HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"})
        except subprocess.TimeoutExpired:
            self._send(HTTPStatus.GATEWAY_TIMEOUT, {"error": "Termux:API timed out"})
        except RuntimeError as exc:
            self._send(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})

    def log_message(self, message: str, *args) -> None:
        print(f"{self.address_string()} - {message % args}", flush=True)

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
        return bool(TOKEN) and hmac.compare_digest(supplied, TOKEN)

    def _send(self, status: HTTPStatus, payload) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    if len(TOKEN) < 16:
        raise SystemExit("Set ASM_AGENT_TOKEN to a random value with at least 16 characters.")
    print(f"Termux:API agent listening on {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), AgentHandler).serve_forever()


if __name__ == "__main__":
    main()
