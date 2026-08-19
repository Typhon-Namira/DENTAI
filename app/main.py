from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1 import (
    administration,
    ai,
    auth,
    branches,
    clinical,
    dashboard,
    patients,
    radar,
    radar_connections,
    users,
    xrays,
)
from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, unexpected_error_handler
from app.core.logging import configure_logging, request_logging, security_headers
from app.database.sessions import ControlSession, dispose_control_engine
from app.outreach import api as outreach

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await resolver.dispose_all()
        await dispose_control_engine()


app = FastAPI(title="DENTAI Backend", version="0.1.0", lifespan=lifespan)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)
app.middleware("http")(request_logging)
app.middleware("http")(security_headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
for router in (
    auth.router,
    branches.router,
    patients.router,
    xrays.router,
    ai.router,
    dashboard.router,
    users.router,
    clinical.router,
    administration.router,
    radar.router,
    radar_connections.router,
    outreach.router,
):
    app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready():
    async with ControlSession() as db:
        await db.execute(text("SELECT 1"))
    return {"status": "ready"}


frontend_dist = Path("/app/frontend-dist")
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
