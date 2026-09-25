import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    aksi,
    audit,
    auth,
    babies,
    dashboard,
    doctor_notes,
    incubators,
    involvement,
    monitoring,
    observation,
    reports,
    telemetry,
    users,
)
from app.core.config import settings
from app.jobs import retention

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start the sensor-retention loop alongside the app.

    Single-process assumption, the same one the SSE fan-out makes: compose runs
    uvicorn without `--workers`, so exactly one loop exists. Set
    SENSOR_RETENTION_INTERVAL_HOURS=0 and drive it from cron if that changes.
    """
    task = asyncio.create_task(retention.run_forever())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The directory is created here so the first upload has somewhere to land. It is
# deliberately NOT mounted as static files: these are patient photos, and a static
# mount serves them to anyone who can reach the port, with no session and nothing
# in the audit trail. They are read through GET /api/v1/monitoring/{id}/photo,
# which is gated like every other clinical read.
uploads_dir = Path(settings.storage_local_path)
uploads_dir.mkdir(parents=True, exist_ok=True)

app.include_router(auth.router,        prefix="/api/v1/auth",        tags=["Auth"])
app.include_router(users.router,       prefix="/api/v1/users",       tags=["Users"])
app.include_router(incubators.router,  prefix="/api/v1/incubators",  tags=["Incubators"])
app.include_router(babies.router,      prefix="/api/v1/babies",      tags=["Babies"])
app.include_router(monitoring.router,  prefix="/api/v1",             tags=["Monitoring"])
app.include_router(involvement.router, prefix="/api/v1",             tags=["Involvement"])
app.include_router(observation.router, prefix="/api/v1",             tags=["Observation"])
app.include_router(aksi.router,        prefix="/api/v1",             tags=["Aksi"])
app.include_router(doctor_notes.router, prefix="/api/v1",            tags=["Doctor Notes"])
app.include_router(dashboard.router,   prefix="/api/v1/dashboard",   tags=["Dashboard"])
app.include_router(reports.router,     prefix="/api/v1",             tags=["Reports"])
app.include_router(telemetry.router,   prefix="/api/v1",             tags=["Telemetry"])
# Prototype firmware posts to /api/sensors; gated by LEGACY_SENSOR_INGEST.
app.include_router(telemetry.legacy_router, prefix="/api",           tags=["Telemetry (legacy)"])
app.include_router(audit.router,       prefix="/api/v1/audit-logs",  tags=["Audit"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.app_version}
