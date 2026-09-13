import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes.devices import router as devices_router
from backend.app.api.routes.health import router as health_router
from backend.app.core.config import get_settings
from backend.app.core.database import Database
from backend.app.core.logging import configure_logging
from backend.app.services.adb import ADBClient, RealADBClient
from backend.app.services.devices import DeviceService

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
    logger.info("application_started")
    yield
    logger.info("application_stopped")


def create_app(database_url: str | None = None, adb_client: ADBClient | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Android Server Manager", version="0.1.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    database = Database(database_url or settings.database_url)
    adb = adb_client or RealADBClient(settings.adb_path, settings.adb_server_port, settings.adb_timeout)
    app.state.database = database
    app.state.device_service = DeviceService(database, adb)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Authorization"])
    app.include_router(health_router)
    app.include_router(devices_router)
    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def frontend(full_path: str) -> FileResponse:
            return FileResponse(FRONTEND_DIST / "index.html")
    return app


app = create_app()
