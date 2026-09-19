import asyncio
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyRole
from app.core.database import AsyncSessionLocal, get_db
from app.repositories.assignment_repository import AssignmentRepository
from app.schemas.incubator import (
    IncubatorCreate,
    IncubatorDetailResponse,
    IncubatorPlacement,
    IncubatorResponse,
    IncubatorThresholdsResponse,
    IncubatorThresholdsUpdate,
    IncubatorUpdate,
)
from app.schemas.telemetry import (
    DeviceCreate,
    DeviceProvisionResponse,
    DeviceResponse,
    DeviceUpdate,
    SensorAlertResponse,
    SensorReadingResponse,
)
from app.services import (
    alert_service,
    incubator_service,
    telemetry_service,
    telemetry_stream,
)

router = APIRouter()


@router.get("", response_model=list[IncubatorDetailResponse])
async def list_incubators(
    current_user: AnyRole,
    archived: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Incubators in service. `archived=true` lists the archived ones instead."""
    return await incubator_service.get_all_incubators(db, archived=archived)


@router.get("/available", response_model=list[IncubatorResponse])
async def list_available_incubators(
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    """Returns only 'kosong' incubators — used when assigning a baby."""
    return await incubator_service.get_available_incubators(db)


@router.get("/{incubator_id}", response_model=IncubatorDetailResponse)
async def get_incubator(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    return await incubator_service.get_incubator(incubator_id, db)


@router.post("", response_model=IncubatorResponse, status_code=status.HTTP_201_CREATED)
async def create_incubator(
    data: IncubatorCreate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await incubator_service.create_incubator(data, db, actor_id=current_user.id, ip=ip)


@router.put("/{incubator_id}", response_model=IncubatorResponse)
async def update_incubator(
    incubator_id: uuid.UUID,
    data: IncubatorUpdate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await incubator_service.update_incubator(
        incubator_id, data, db, actor_id=current_user.id, ip=ip
    )


@router.delete("/{incubator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incubator(
    incubator_id: uuid.UUID,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Delete an incubator that has never held a baby (admin only).

    One with placement history is refused (409) — archive it instead.
    """
    ip = request.client.host if request.client else None
    await incubator_service.delete_incubator(
        incubator_id, db, actor_id=current_user.id, ip=ip
    )


@router.post("/{incubator_id}/archive", response_model=IncubatorDetailResponse)
async def archive_incubator(
    incubator_id: uuid.UUID,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Retire an incubator, keeping every placement, reading and alert (admin only).

    Refused while a baby is in it. Its device is unbound, open alerts are closed as
    'archived', and it becomes read-only and hidden from the dashboard and admission.
    """
    ip = request.client.host if request.client else None
    return await incubator_service.archive_incubator(
        incubator_id, db, actor_id=current_user.id, ip=ip
    )


@router.post("/{incubator_id}/restore", response_model=IncubatorDetailResponse)
async def restore_incubator(
    incubator_id: uuid.UUID,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Return an archived incubator to the dashboard, as 'tidak_tersedia' (admin only)."""
    ip = request.client.host if request.client else None
    return await incubator_service.restore_incubator(
        incubator_id, db, actor_id=current_user.id, ip=ip
    )


@router.get("/{incubator_id}/placements", response_model=list[IncubatorPlacement])
async def list_incubator_placements(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    """Every baby this incubator has held, newest first — its usage history."""
    return await incubator_service.get_placements(incubator_id, db)


@router.get("/{incubator_id}/thresholds", response_model=IncubatorThresholdsResponse)
async def get_incubator_thresholds(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    """Effective sensor alert thresholds (stored overrides merged with defaults)."""
    return await incubator_service.get_thresholds(incubator_id, db)


@router.put("/{incubator_id}/thresholds", response_model=IncubatorThresholdsResponse)
async def update_incubator_thresholds(
    incubator_id: uuid.UUID,
    data: IncubatorThresholdsUpdate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Set per-incubator sensor alert thresholds (admin only)."""
    ip = request.client.host if request.client else None
    return await incubator_service.update_thresholds(
        incubator_id, data, db, actor_id=current_user.id, ip=ip
    )


@router.get("/{incubator_id}/alerts", response_model=list[SensorAlertResponse])
async def get_incubator_alerts(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    only_open: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Alert history for this incubator, newest first.

    Readable by any role: an alarm only a subset of staff can see is not an alarm.
    """
    return await alert_service.list_for_incubator(
        incubator_id, db, only_open=only_open, limit=limit
    )


# ── IoT sensor readings (chart backfill) ────────────────────────────────────────


@router.get("/{incubator_id}/readings", response_model=list[SensorReadingResponse])
async def get_incubator_readings(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    limit: int = Query(120, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Recent sensor samples for this incubator, oldest first (plot order).

    Readable by any role: a nurse looking at the vitals chart needs this as much
    as an admin does. Null metrics are returned as null and mean "no reading",
    so clients must break the line rather than plot a zero.
    """
    return await telemetry_service.get_recent_readings(incubator_id, db, limit=limit)


@router.get("/{incubator_id}/stream")
async def stream_incubator_readings(
    incubator_id: uuid.UUID,
    request: Request,
    current_user: AnyRole,
):
    """Live sensor readings for one incubator as Server-Sent Events.

    SSE rather than a WebSocket because telemetry is one-way: this rides the
    dashboard's existing cookie->Bearer proxy unchanged, reconnects natively in
    the browser, and needs no short-lived ticket for the client to authenticate.

    On connect the ring buffer is replayed so a chart opened mid-stream is never
    blank, then new readings arrive as they are ingested. A comment line is sent
    every 15 s so idle proxies do not close the connection.

    The replay starts at the incubator's current occupancy, like GET /readings —
    the buffer does not know who was in the box. The lookup uses its own
    short-lived session: a request-scoped one would stay checked out of the pool
    for as long as the stream is open.
    """
    async with AsyncSessionLocal() as session:
        since = await AssignmentRepository(session).occupancy_start(incubator_id)

    async def events():
        q = telemetry_stream.subscribe(incubator_id)
        try:
            for reading in telemetry_stream.replay(incubator_id, since=since):
                yield f"data: {reading.model_dump_json()}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    reading = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"   # keepalive, ignored by EventSource
                    continue
                yield f"data: {reading.model_dump_json()}\n\n"
        finally:
            # Runs on disconnect and on cancellation alike; without it every
            # navigation would leak a queue that publish() writes to forever.
            telemetry_stream.unsubscribe(incubator_id, q)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Tell nginx (VPS deploy) not to buffer, or nothing ships until the
            # response ends — which for a stream is never.
            "X-Accel-Buffering": "no",
        },
    )


# ── IoT device binding (one device per incubator) ───────────────────────────────


@router.get("/{incubator_id}/device", response_model=DeviceResponse | None)
async def get_incubator_device(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    """The device bound to this incubator, or null if none is installed."""
    return await telemetry_service.get_device(incubator_id, db)


@router.post(
    "/{incubator_id}/device",
    response_model=DeviceProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_incubator_device(
    incubator_id: uuid.UUID,
    data: DeviceCreate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Bind a device to this incubator and mint its key (admin only).

    The response carries the plaintext `device_key` — the only time it exists
    outside the firmware. Copy it into the sketch; it cannot be recovered later.
    """
    ip = request.client.host if request.client else None
    return await telemetry_service.provision_device(
        incubator_id, data, db, actor_id=current_user.id, ip=ip
    )


@router.put("/{incubator_id}/device", response_model=DeviceResponse)
async def update_incubator_device(
    incubator_id: uuid.UUID,
    data: DeviceUpdate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Edit this incubator's device — label and IP allowlist (admin only).

    Cannot change the key: the plaintext is unrecoverable by design, so rotating
    one means revoke + re-provision + reflash.
    """
    ip = request.client.host if request.client else None
    return await telemetry_service.update_device(
        incubator_id, data, db, actor_id=current_user.id, ip=ip
    )


@router.delete("/{incubator_id}/device", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_incubator_device(
    incubator_id: uuid.UUID,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Revoke this incubator's device (admin only). Past readings are kept."""
    ip = request.client.host if request.client else None
    await telemetry_service.revoke_device(incubator_id, db, actor_id=current_user.id, ip=ip)
