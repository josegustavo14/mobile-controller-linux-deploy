from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, supplied exclusively through the environment."""

    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8080, ge=1, le=65535)
    database_url: str = "sqlite:///./data/app.db"
    adb_path: str = "/opt/android-platform-tools/adb"
    adb_server_port: int = Field(default=5037, ge=1, le=65535)
    adb_timeout: float = Field(default=15.0, gt=0)
    scrcpy_path: str = "/opt/scrcpy/scrcpy"
    scrcpy_viewer_port: int = Field(default=6080, ge=1, le=65535)
    termux_agent_port: int = Field(default=8765, ge=1, le=65535)
    termux_agent_token: str = ""
    update_manifest_url: str = (
        "https://raw.githubusercontent.com/josegustavo14/"
        "mobile-controller-linux-deploy/main/version.json"
    )
    updater_url: str = ""
    updater_token: str = ""
    updater_image: str = "ghcr.io/josegustavo14/mobile-controller-linux-deploy:latest"
    admin_token: str = ""
    linux_deploy_cli: str = "/data/user/0/ru.meefik.linuxdeploy/files/bin/linuxdeploy"
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:8080"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
