import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.involvement import ParentInvolvementRecord
from app.repositories.baby_repository import BabyRepository
from app.repositories.involvement_repository import InvolvementRepository
from app.schemas.involvement import (
    InvolvementCreate,
    InvolvementResponse,
    InvolvementSummary,
)
from app.services.audit_service import log_action

# ── Scoring formula ────────────────────────────────────────────────────────────
# menyusui: benchmark 30 min/session → 60 pts max   (2 pts/min)
# interaksi: benchmark 60 min/session → 40 pts max  (0.667 pts/min)

_SCORE_CATEGORIES = [
    (76, "Sangat Baik"),
    (51, "Baik"),
    (26, "Sedang"),
    (0,  "Rendah"),
]


def calculate_score(durasi_menyusui: int | None, durasi_interaksi: int | None) -> int:
    menyusui = durasi_menyusui or 0
    interaksi = durasi_interaksi or 0
    menyusui_pts = min(60, menyusui * 2)
    interaksi_pts = min(40, round(interaksi * 40 / 60))
    return round(menyusui_pts + interaksi_pts)


def score_to_category(score: int | None) -> str | None:
    if score is None:
        return None
    for threshold, label in _SCORE_CATEGORIES:
        if score >= threshold:
            return label
    return "Rendah"


def _to_response(record: ParentInvolvementRecord) -> InvolvementResponse:
    return InvolvementResponse(
        involvement_id=record.involvement_id,
        baby_id=record.baby_id,
        recorded_by=record.recorded_by,
        recorder_name=record.recorder.full_name if record.recorder else None,
        observation_time=record.observation_time,
        durasi_menyusui=record.durasi_menyusui,
        durasi_interaksi=record.durasi_interaksi,
        catatan=record.catatan,
        skor_keterlibatan=record.skor_keterlibatan,
        skor_kategori=score_to_category(record.skor_keterlibatan),
        kondisi_bayi=record.kondisi_bayi,
        created_at=record.created_at,
    )


async def create_involvement(
    baby_id: uuid.UUID,
    data: InvolvementCreate,
    db: AsyncSession,
    actor_id: uuid.UUID,
    ip: str | None = None,
) -> InvolvementResponse:
    baby = await BabyRepository(db).get_by_id(baby_id)
    if not baby:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data bayi tidak ditemukan")

    skor = calculate_score(data.durasi_menyusui, data.durasi_interaksi)

    record = ParentInvolvementRecord(
        baby_id=baby_id,
        recorded_by=actor_id,
        observation_time=data.observation_time,
        durasi_menyusui=data.durasi_menyusui,
        durasi_interaksi=data.durasi_interaksi,
        catatan=data.catatan,
        skor_keterlibatan=skor,
        kondisi_bayi=data.kondisi_bayi,
    )

    repo = InvolvementRepository(db)
    record = await repo.create(record)

    await log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        table_name="parent_involvement_records",
        record_id=record.involvement_id,
        ip_address=ip,
        details={"skor": skor, "kategori": score_to_category(skor)},
    )
    return _to_response(record)


async def list_involvement(
    baby_id: uuid.UUID,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> list[InvolvementResponse]:
    records = await InvolvementRepository(db).get_by_baby(baby_id, skip=skip, limit=limit)
    return [_to_response(r) for r in records]


async def get_involvement_summary(baby_id: uuid.UUID, db: AsyncSession) -> InvolvementSummary:
    repo = InvolvementRepository(db)
    stats = await repo.get_summary_stats(baby_id)
    records = await repo.get_by_baby(baby_id, limit=1)
    latest = records[0] if records else None

    return InvolvementSummary(
        total_sessions=stats["total"],
        avg_skor=round(stats["avg_skor"], 1) if stats["avg_skor"] else None,
        avg_durasi_menyusui=round(stats["avg_menyusui"], 1) if stats["avg_menyusui"] else None,
        avg_durasi_interaksi=round(stats["avg_interaksi"], 1) if stats["avg_interaksi"] else None,
        latest_skor=latest.skor_keterlibatan if latest else None,
        latest_kategori=score_to_category(latest.skor_keterlibatan) if latest else None,
    )
