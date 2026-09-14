from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from backend.app.services.audit import AuditService

VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class UpdaterError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateStatus:
    current_version: str
    latest_version: str | None
    update_available: bool
    updater_enabled: bool
    message: str


class UpdaterService:
    def __init__(
        self,
        audit: AuditService,
        manifest_url: str,
        updater_url: str,
        updater_token: str,
        updater_image: str,
    ) -> None:
        self.audit = audit
        self.manifest_url = manifest_url
        self.updater_url = updater_url.rstrip("/")
        self.updater_token = updater_token
        self.updater_image = updater_image

    def status(self, current_version: str) -> UpdateStatus:
        enabled = bool(self.updater_url and self.updater_token)
        try:
            with httpx.Client(timeout=5, follow_redirects=False) as client:
                response = client.get(self.manifest_url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            latest_version = payload.get("version") if isinstance(payload, dict) else None
            current = self._parse_version(current_version)
            latest = self._parse_version(latest_version)
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return UpdateStatus(
                current_version=current_version,
                latest_version=None,
                update_available=False,
                updater_enabled=enabled,
                message="Could not check GitHub for a newer version.",
            )
        available = latest > current
        if available and enabled:
            message = f"Version {latest_version} is ready to install."
        elif available:
            message = f"Version {latest_version} is available, but the updater is not configured."
        else:
            message = "The application is up to date."
        return UpdateStatus(current_version, latest_version, available, enabled, message)

    def apply(self) -> None:
        if not self.updater_url or not self.updater_token:
            raise UpdaterError("The ZimaOS updater is not configured.")
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                response = client.post(
                    f"{self.updater_url}/v1/update",
                    params={"image": self.updater_image, "async": "true"},
                    headers={"Authorization": f"Bearer {self.updater_token}"},
                )
        except httpx.RequestError as exc:
            raise UpdaterError("Could not reach the local ZimaOS updater.") from exc
        if response.status_code not in {200, 202}:
            raise UpdaterError(f"The local updater rejected the request (HTTP {response.status_code}).")
        self.audit.record("application.update", "Requested an application image update.")

    @staticmethod
    def _parse_version(value: str | None) -> tuple[int, int, int]:
        if not isinstance(value, str):
            raise ValueError("version is missing")
        match = VERSION_PATTERN.fullmatch(value)
        if match is None:
            raise ValueError("version must use semantic versioning")
        return tuple(int(part) for part in match.groups())
