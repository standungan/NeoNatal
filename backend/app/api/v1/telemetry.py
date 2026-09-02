import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyRole, CurrentDevice, PerawatOrAdmin
from app.core.database import get_db
from app.core.config import settings
from app.schemas.telemetry import (
    LegacyTelemetryIn,
    SensorAlertResponse,
    SensorReadingResponse,
    TelemetryAck,
    TelemetryIn,
)
from app.services import alert_service, telemetry_service

router = APIRouter()


@router.post("/telemetry", response_model=TelemetryAck, status_code=status.HTTP_201_CREATED)
async def post_telemetry(
    data: TelemetryIn,
    device: CurrentDevice,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Ingest one sample from an incubator's IoT device.

    The only endpoint devices may reach, and the only one authenticated by
    `X-Device-Key` instead of a JWT.

    201 = stored · 202 = device alive but no sensor had anything to report.
    The distinction matters: 202 keeps the online badge lit without writing a row
    of nulls.
    """
    ip = request.client.host if request.client else None
    ack = await telemetry_service.ingest(data, device, db, client_ip=ip)
    if not ack.stored:
        response.status_code = status.HTTP_202_ACCEPTED
    return ack


@router.get(
    "/babies/{baby_id}/latest-reading", response_model=SensorReadingResponse | None
)
async def get_latest_reading_for_baby(
    baby_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    """Latest sensor sample for this baby's incubator, or null.

    Feeds the vitals form's "fill from sensor" action. Null is a normal answer —
    no device, no assignment, or nothing recorded yet.
    """
    return await telemetry_service.latest_for_baby(baby_id, db)


@router.post("/alerts/{alert_id}/acknowledge", response_model=SensorAlertResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    request: Request,
    current_user: PerawatOrAdmin,
    db: AsyncSession = Depends(get_db),
):
    """Record that a human has seen this alert.

    Acknowledging is not resolving: the breach ends when the readings say so, not
    when someone clicks. PerawatOrAdmin matches every other clinical write —
    dokter is read-only throughout.
    """
    ip = request.client.host if request.client else None
    return await alert_service.acknowledge(alert_id, db, actor_id=current_user.id, ip=ip)


# ── Legacy prototype ingest ─────────────────────────────────────────────────────
#
# A second router, mounted at /api (not /api/v1), because the prototype firmware
# has POST /api/sensors compiled into it and cannot be re-pointed without a
# reflash. Separate from the router above so the two surfaces never blur: this
# one is UNAUTHENTICATED and disabled unless a deployment opts in.

legacy_router = APIRouter()


@legacy_router.post("/sensors", response_model=TelemetryAck, status_code=status.HTTP_201_CREATED)
async def post_legacy_sensors(
    data: LegacyTelemetryIn,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Ingest from prototype firmware that predates device keys.

    Nothing authenticates the caller here — anything able to reach this port can
    write vitals — so it answers 404 unless LEGACY_SENSOR_INGEST is enabled,
    which keeps it a lab-bench affordance rather than something that can quietly
    reach a real deployment.

    The payload's `baby_id` is ignored; the baby is resolved from the active
    assignment exactly as on the authenticated path.
    """
    if not settings.legacy_sensor_ingest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Legacy sensor ingest is disabled. Use POST /api/v1/telemetry with X-Device-Key.",
        )

    ip = request.client.host if request.client else None
    ack = await telemetry_service.ingest_legacy(data, db, client_ip=ip)
    if not ack.stored:
        response.status_code = status.HTTP_202_ACCEPTED
    return ack
