import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incubator import Incubator
from app.repositories.incubator_repository import IncubatorRepository
from app.schemas.incubator import (
    DEFAULT_THRESHOLDS,
    THRESHOLD_METRICS,
    CurrentBabySummary,
    IncubatorCreate,
    IncubatorDetailResponse,
    IncubatorResponse,
    IncubatorThresholdsResponse,
    IncubatorThresholdsUpdate,
    IncubatorUpdate,
    ThresholdMetric,
)
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


async def get_all_incubators(db: AsyncSession) -> list[IncubatorDetailResponse]:
    repo = IncubatorRepository(db)
    incubators = await repo.get_all_with_assignment()
    return [_to_detail_response(inc) for inc in incubators]


async def get_incubator(incubator_id: uuid.UUID, db: AsyncSession) -> IncubatorDetailResponse:
    repo = IncubatorRepository(db)
    inc = await repo.get_by_id_with_assignment(incubator_id)
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inkubator tidak ditemukan")
    return _to_detail_response(inc)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inkubator tidak ditemukan")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inkubator tidak ditemukan")

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
                "Tandai sebagai 'Tidak Tersedia' sebagai gantinya."
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inkubator tidak ditemukan")

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


def _to_detail_response(inc: Incubator) -> IncubatorDetailResponse:
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
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        current_baby=current_baby,
    )
