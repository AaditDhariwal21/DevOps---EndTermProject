import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.routers import activity, tickets
from app.schemas import SystemInfo

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("deskflow")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DeskFlow helpdesk ticketing API — DevOps capstone project.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)
app.include_router(activity.router)

# Exposes http_requests_total, http_request_duration_seconds, ... on /metrics.
# Probe and scrape endpoints are excluded so they don't drown out real traffic.
Instrumentator(
    excluded_handlers=["/metrics", "/health", "/ready"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


def _database_ok(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - any DB failure means "not ready"
        logger.exception("Database check failed")
        return False


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "git_sha": settings.git_sha,
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness: the process is up and serving HTTP. Deliberately does not touch the DB."""
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def ready(db: Session = Depends(get_db)) -> JSONResponse:
    """Readiness: only accept traffic when the database is reachable."""
    if _database_ok(db):
        return JSONResponse({"status": "ready", "database": "ok"})
    return JSONResponse({"status": "not ready", "database": "unreachable"}, status_code=503)


@app.get("/api/system", response_model=SystemInfo, tags=["system"])
def system_info(db: Session = Depends(get_db)) -> SystemInfo:
    """Deployment info shown in the UI's pipeline panel (proves which commit is live)."""
    return SystemInfo(
        app=settings.app_name,
        version=settings.app_version,
        git_sha=settings.git_sha,
        environment=settings.environment,
        database="ok" if _database_ok(db) else "unreachable",
    )
