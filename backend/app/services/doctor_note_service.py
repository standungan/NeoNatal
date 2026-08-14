import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor_note import DoctorNote
from app.repositories.baby_repository import BabyRepository
from app.repositories.doctor_note_repository import DoctorNoteRepository
from app.schemas.doctor_note import DoctorNoteCreate, DoctorNoteResponse
from app.services.audit_service import log_action


def _to_response(note: DoctorNote) -> DoctorNoteResponse:
    return DoctorNoteResponse(
        note_id=note.note_id,
        baby_id=note.baby_id,
        recorded_by=note.recorded_by,
        recorder_name=note.recorder.full_name if note.recorder else None,
        observation_time=note.observation_time,
        catatan=note.catatan,
        created_at=note.created_at,
    )


async def create_note(
    baby_id: uuid.UUID,
    data: DoctorNoteCreate,
    db: AsyncSession,
    actor_id: uuid.UUID,
    ip: str | None = None,
) -> DoctorNoteResponse:
    baby = await BabyRepository(db).get_by_id(baby_id)
    if not baby:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data bayi tidak ditemukan")

    catatan = (data.catatan or "").strip()
    if not catatan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Catatan tidak boleh kosong"
        )

    repo = DoctorNoteRepository(db)
    note = DoctorNote(
        baby_id=baby_id,
        recorded_by=actor_id,
        observation_time=data.observation_time,
        catatan=catatan,
    )
    note = await repo.create(note)

    await log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        table_name="doctor_notes",
        record_id=note.note_id,
        ip_address=ip,
    )

    note = await repo.get_by_id(note.note_id)
    return _to_response(note)


async def list_notes(
    baby_id: uuid.UUID,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> list[DoctorNoteResponse]:
    records = await DoctorNoteRepository(db).get_by_baby(baby_id, skip=skip, limit=limit)
    return [_to_response(r) for r in records]


async def get_latest_note(baby_id: uuid.UUID, db: AsyncSession) -> DoctorNoteResponse | None:
    note = await DoctorNoteRepository(db).get_latest_by_baby(baby_id)
    return _to_response(note) if note else None
