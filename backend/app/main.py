import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes.environments import router as environments_router
from backend.app.api.routes.devices import router as devices_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.scrcpy import router as scrcpy_router
from backend.app.api.routes.system import router as system_router
from backend.app.api.routes.termux_agent import router as termux_agent_router
from backend.app.api.routes.update import router as update_router
from backend.app.core.config import get_settings
from backend.app.core.database import Database
from backend.app.core.logging import configure_logging
from backend.app.core.version import APP_VERSION
from backend.app.services.adb import ADBClient, RealADBClient
from backend.app.services.audit import AuditService
from backend.app.services.devices import DeviceService
from backend.app.services.linux_deploy import LinuxDeployService
from backend.app.services.scrcpy import ScrcpyService
from backend.app.services.termux_agent import TermuxAgentService
from backend.app.services.updater import UpdaterService

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    # The container workdir is /app, while unit tests deliberately use the
    # repository-local volume. This keeps the persistence contract portable.
    Path("data").mkdir(parents=True, exist_ok=True)
    app.state.database.create_schema()
    app.state.device_service.reset_transient_connections()
    logger.info("application_started")
    yield
    app.state.scrcpy_service.stop(record_audit=False)
    logger.info("application_stopped")


def create_app(database_url: str | None = None, adb_client: ADBClient | None = None) -> FastAPI:
    settings = get_settings().model_copy(deep=True)
    app = FastAPI(title="Android Server Manager", version=APP_VERSION, lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    database = Database(database_url or settings.database_url)
    adb = adb_client or RealADBClient(settings.adb_path, settings.adb_server_port, settings.adb_timeout)
    audit_service = AuditService(database)
    app.state.settings = settings
    app.state.database = database
    app.state.audit_service = audit_service
    device_service = DeviceService(database, adb, audit_service)
    app.state.device_service = device_service
    app.state.scrcpy_service = ScrcpyService(
        audit_service,
        settings.scrcpy_path,
        settings.adb_path,
        settings.adb_server_port,
        settings.scrcpy_viewer_port,
    )
    app.state.termux_agent_service = TermuxAgentService(
        device_service,
        audit_service,
        settings.termux_agent_port,
        settings.termux_agent_token,
    )
    app.state.updater_service = UpdaterService(
        audit_service,
        settings.update_manifest_url,
        settings.updater_url,
        settings.updater_token,
        settings.updater_image,
    )
    app.state.linux_deploy_service = LinuxDeployService(
        database,
        adb,
        device_service,
        audit_service,
        settings.linux_deploy_cli,
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Authorization"])
    app.include_router(health_router)
    app.include_router(devices_router)
    app.include_router(environments_router)
    app.include_router(scrcpy_router)
    app.include_router(termux_agent_router)
    app.include_router(update_router)
    app.include_router(system_router)
    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def frontend(full_path: str) -> FileResponse:
            return FileResponse(FRONTEND_DIST / "index.html")
    return app


app = create_app()
