from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from backend.app.services.audit import AuditService
from backend.app.services.devices import DeviceService


class TermuxAgentError(RuntimeError):
    pass


class TermuxAgentService:
    def __init__(
        self,
        devices: DeviceService,
        audit: AuditService,
        port: int,
        token: str,
    ) -> None:
        self.devices = devices
        self.audit = audit
        self.port = port
        self.token = token

    def capabilities(self, device_id: str) -> dict[str, list[str]]:
        payload = self._request(device_id, "/v1/capabilities")
        if not isinstance(payload, dict):
            raise TermuxAgentError("The Termux agent returned an invalid capability response.")
        sensors = sorted({value for value in payload.get("sensors", []) if isinstance(value, str)})
        apis = sorted({value for value in payload.get("apis", []) if isinstance(value, str)})
        return {"sensors": sensors[:256], "apis": apis}

    def read_sensor(self, device_id: str, name: str) -> Any:
        payload = self._request(device_id, f"/v1/sensor?name={quote(name, safe='')}")
        self.audit.record("termux.sensor", f"Read the {name} sensor through Termux:API.", device_id)
        return payload

    def read_api(self, device_id: str, name: str) -> Any:
        payload = self._request(device_id, f"/v1/api/{name}")
        self.audit.record("termux.api", f"Read {name} through the Termux:API agent.", device_id)
        return payload

    def _request(self, device_id: str, path: str) -> Any:
        if not self.token:
            raise TermuxAgentError("Configure TERMUX_AGENT_TOKEN on ZimaOS before connecting the Termux agent.")
        device = self.devices.get(device_id)
        host = device.host.strip("[]")
        if ":" in host:
            host = f"[{host}]"
        url = f"http://{host}:{self.port}{path}"
        try:
            with httpx.Client(timeout=25, follow_redirects=False) as client:
                response = client.get(url, headers={"Authorization": f"Bearer {self.token}"})
        except httpx.RequestError as exc:
            raise TermuxAgentError(
                f"Could not reach the Termux:API agent at {device.host}:{self.port}."
            ) from exc
        if len(response.content) > 1_000_000:
            raise TermuxAgentError("The Termux agent response exceeded the safety limit.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TermuxAgentError("The Termux agent returned invalid JSON.") from exc
        if response.is_error:
            detail = payload.get("error") if isinstance(payload, dict) else None
            raise TermuxAgentError(detail or f"The Termux agent returned HTTP {response.status_code}.")
        return payload
