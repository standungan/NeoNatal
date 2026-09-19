import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incubator import Incubator
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.incubator_repository import IncubatorRepository
from app.schemas.incubator import (
    DEFAULT_THRESHOLDS,
    THRESHOLD_METRICS,
    CurrentBabySummary,
    IncubatorCreate,
    IncubatorDetailResponse,
    IncubatorPlacement,
    IncubatorResponse,
    IncubatorThresholdsResponse,
    IncubatorThresholdsUpdate,
    IncubatorUpdate,
    ThresholdMetric,
)
from app.services import alert_service
from app.services.audit_service import log_action

# Statuses an admin may set (or that allow deletion) by hand. 'terisi' and
# 'warning' are managed automatically by the assignment/monitoring flows.
MANUAL_STATUSES = ("kosong", "tidak_tersedia")


def _next_incubator_no(existing: list[Incubator]) -> str:
    """Next sequential number: highest numeric incubator_no + 1, zero-padded to 2."""
    max_n = 0
    for inc in existing:
        try:
            max_n = max(max_n, int(inc.incubator_no))
        except (TypeError, ValueError):
            continue  # ignore any non-numeric legacy numbers
    return f"{max_n + 1:02d}"


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inkubator tidak ditemukan")


def _reject_if_archived(inc: Incubator) -> None:
    """An archived incubator is read-only: its history is shown, nothing is changed."""
    if inc.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inkubator {inc.incubator_no} sudah diarsipkan. Pulihkan terlebih dahulu.",
        )


async def get_all_incubators(
    db: AsyncSession, archived: bool = False
) -> list[IncubatorDetailResponse]:
    """Active incubators, or with `archived` only the archived ones (the archive list)."""
    repo = IncubatorRepository(db)
    incubators = await repo.get_all_with_assignment(archived=archived)
    history = await repo.ids_with_history([i.incubator_id for i in incubators])
    return [_to_detail_response(inc, inc.incubator_id in history) for inc in incubators]


async def get_incubator(incubator_id: uuid.UUID, db: AsyncSession) -> IncubatorDetailResponse:
    """One incubator, archived or not — an archived one stays readable for its history."""
    repo = IncubatorRepository(db)
    inc = await repo.get_by_id_with_assignment(incubator_id)
    if not inc:
        raise _not_found()
    return _to_detail_response(inc, await repo.has_assignments(incubator_id))


async def get_placements(incubator_id: uuid.UUID, db: AsyncSession) -> list[IncubatorPlacement]:
    """Every baby this incubator has held, newest first.

    The incubator's usage history — who was in this box, and when. It answers the
    question an infection-control review asks, and links each stay to the baby
    whose records it belongs to.
    """
    if not await IncubatorRepository(db).get_by_id(incubator_id):
        raise _not_found()
    return [
        IncubatorPlacement(
            assignment_id=a.assignment_id,
            baby_id=a.baby_id,
            baby_name=a.baby.baby_name,
            no_registrasi_nicu=a.no_registrasi_nicu,
            status=a.status,
            assigned_at=a.assigned_at,
            discharged_at=a.discharged_at,
            assigned_by_name=a.assigned_by_user.full_name if a.assigned_by_user else None,
            dpjp_name=a.dpjp.full_name if a.dpjp else None,
        )
        for a in await AssignmentRepository(db).list_by_incubator(incubator_id)
    ]


async def get_available_incubators(db: AsyncSession) -> list[IncubatorResponse]:
    repo = IncubatorRepository(db)
    incubators = await repo.get_available()
    return [IncubatorResponse.model_validate(i) for i in incubators]


async def create_incubator(
    data: IncubatorCreate,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> IncubatorResponse:
    repo = IncubatorRepository(db)

    # Auto-assign the next sequential number (max existing + 1, zero-padded).
    incubator_no = _next_incubator_no(await repo.get_all())

    inc = Incubator(incubator_no=incubator_no, location=data.location)
    inc = await repo.create(inc)

    await log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        table_name="incubators",
        record_id=inc.incubator_id,
        ip_address=ip,
        details={"incubator_no": inc.incubator_no},
    )
    return IncubatorResponse.model_validate(inc)


async def update_incubator(
    incubator_id: uuid.UUID,
    data: IncubatorUpdate,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> IncubatorResponse:
    repo = IncubatorRepository(db)
    inc = await repo.get_by_id(incubator_id)
    if not inc:
        raise _not_found()
    _reject_if_archived(inc)

    if data.location is not None:
        inc.location = data.location
    if data.status is not None:
        # Manual status changes are admin-only (enforced at the route) and limited
        # to the two non-occupied states. 'terisi'/'warning' are set automatically
        # by the assignment/monitoring/observation flows, never by hand.
        if data.status not in MANUAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status hanya dapat diubah menjadi Kosong atau Tidak Tersedia",
            )
        if await repo.has_active_assignment(incubator_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inkubator sedang terisi — status tidak dapat diubah",
            )
        inc.status = data.status

    inc = await repo.update(inc)

    await log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        table_name="incubators",
        record_id=incubator_id,
        ip_address=ip,
    )
    return IncubatorResponse.model_validate(inc)


async def delete_incubator(
    incubator_id: uuid.UUID,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> None:
    repo = IncubatorRepository(db)
    inc = await repo.get_by_id(incubator_id)
    if not inc:
        raise _not_found()

    if inc.status not in MANUAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hanya inkubator berstatus Kosong atau Tidak Tersedia yang dapat dihapus",
        )
    if await repo.has_assignments(incubator_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Inkubator memiliki riwayat penempatan bayi dan tidak dapat dihapus. "
                "Arsipkan inkubator ini sebagai gantinya."
            ),
        )

    incubator_no = inc.incubator_no
    await repo.delete(inc)

    await log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        table_name="incubators",
        record_id=incubator_id,
        ip_address=ip,
        details={"incubator_no": incubator_no},
    )


async def archive_incubator(
    incubator_id: uuid.UUID,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> IncubatorDetailResponse:
    """Retire an incubator without losing anything recorded in it.

    Deleting would take every placement, reading and alert with it, so the row
    stays and is marked instead. What changes is only what the app offers:

    - gone from the dashboard, its stats and the admission picker;
    - read-only — status, location, thresholds and device are frozen (409);
    - its device is unbound, so nothing reports into a box nobody watches;
    - open alerts are closed as 'archived' (nobody is left to recover);
    - status becomes 'tidak_tersedia', so even a path that forgets to check
      archived_at never admits a baby into it — nor does restoring it.

    Its number stays taken; its history stays readable from the archive list and
    from each baby who used it.
    """
    repo = IncubatorRepository(db)
    inc = await repo.get_by_id(incubator_id)
    if not inc:
        raise _not_found()
    if inc.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inkubator {inc.incubator_no} sudah diarsipkan",
        )
    if await repo.has_active_assignment(incubator_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inkubator sedang ditempati bayi. Pulangkan bayi terlebih dahulu.",
        )

    alerts_closed = await alert_service.close_open_alerts(
        db, incubator_id=incubator_id, reason="archived"
    )

    device_repo = DeviceRepository(db)
    device = await device_repo.get_by_incubator(incubator_id)
    device_unbound = device is not None
    if device is not None:
        device_id = device.device_id
        await device_repo.delete(device)  # readings survive: device_id -> NULL
        await log_action(
            db, user_id=actor_id, action="DELETE", table_name="devices",
            record_id=device_id, ip_address=ip,
            details={"incubator_no": inc.incubator_no, "reason": "incubator archived"},
        )

    inc.archived_at = datetime.now(timezone.utc)
    inc.status = "tidak_tersedia"
    await repo.update(inc)

    await log_action(
        db,
        user_id=actor_id,
        action="ARCHIVE",
        table_name="incubators",
        record_id=incubator_id,
        ip_address=ip,
        details={
            "incubator_no": inc.incubator_no,
            "alerts_closed": alerts_closed,
            "device_unbound": device_unbound,
        },
    )
    return await get_incubator(incubator_id, db)


async def restore_incubator(
    incubator_id: uuid.UUID,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> IncubatorDetailResponse:
    """Bring an archived incubator back to the dashboard.

    It returns as 'tidak_tersedia' and without a device: putting it back into
    service — re-provisioning the sensor, marking it Kosong — is a separate,
    deliberate step, not a side effect of undoing an archive.
    """
    repo = IncubatorRepository(db)
    inc = await repo.get_by_id(incubator_id)
    if not inc:
        raise _not_found()
    if inc.archived_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inkubator {inc.incubator_no} tidak sedang diarsipkan",
        )

    inc.archived_at = None
    await repo.update(inc)

    await log_action(
        db,
        user_id=actor_id,
        action="RESTORE",
        table_name="incubators",
        record_id=incubator_id,
        ip_address=ip,
        details={"incubator_no": inc.incubator_no},
    )
    return await get_incubator(incubator_id, db)


def _thresholds_response(inc: Incubator) -> IncubatorThresholdsResponse:
    stored = inc.alert_thresholds or {}
    metrics: list[ThresholdMetric] = []
    for m in THRESHOLD_METRICS:
        key = m["key"]
        s = stored.get(key) or {}
        dflt = DEFAULT_THRESHOLDS[key]
        metrics.append(ThresholdMetric(
            key=key,
            label=m["label"],
            unit=m["unit"],
            min=s.get("min", dflt["min"]),
            max=s.get("max", dflt["max"]),
        ))
    return IncubatorThresholdsResponse(
        incubator_id=inc.incubator_id,
        incubator_no=inc.incubator_no,
        is_custom=inc.alert_thresholds is not None,
        metrics=metrics,
    )


async def get_thresholds(incubator_id: uuid.UUID, db: AsyncSession) -> IncubatorThresholdsResponse:
    inc = await IncubatorRepository(db).get_by_id(incubator_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inkubator tidak ditemukan")
    return _thresholds_response(inc)


async def update_thresholds(
    incubator_id: uuid.UUID,
    data: IncubatorThresholdsUpdate,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> IncubatorThresholdsResponse:
    repo = IncubatorRepository(db)
    inc = await repo.get_by_id(incubator_id)
    if not inc:
        raise _not_found()
    _reject_if_archived(inc)

    normalized: dict[str, dict] = {}
    for key, bound in data.thresholds.items():
        if key not in DEFAULT_THRESHOLDS:
            continue  # ignore unknown metrics
        if bound.min is not None and bound.max is not None and bound.min > bound.max:
            label = next((m["label"] for m in THRESHOLD_METRICS if m["key"] == key), key)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nilai minimum {label} tidak boleh lebih besar dari maksimum",
            )
        normalized[key] = {"min": bound.min, "max": bound.max}

    inc.alert_thresholds = normalized
    inc = await repo.update(inc)

    await log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        table_name="incubators",
        record_id=incubator_id,
        ip_address=ip,
        details={"alert_thresholds": normalized},
    )
    return _thresholds_response(inc)


def _to_detail_response(inc: Incubator, has_history: bool) -> IncubatorDetailResponse:
    active = next((a for a in inc.assignments if a.status == "active"), None)
    current_baby = None
    if active and active.baby:
        current_baby = CurrentBabySummary(
            baby_id=active.baby.baby_id,
            baby_name=active.baby.baby_name,
            birth_date=active.baby.birth_date,
            assigned_at=active.assigned_at,
        )
    return IncubatorDetailResponse(
        incubator_id=inc.incubator_id,
        incubator_no=inc.incubator_no,
        location=inc.location,
        status=inc.status,
        archived_at=inc.archived_at,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        current_baby=current_baby,
        has_history=has_history,
    )
