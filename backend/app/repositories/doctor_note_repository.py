import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor_note import DoctorNote


class DoctorNoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, note: DoctorNote) -> DoctorNote:
        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def get_by_id(self, note_id: uuid.UUID) -> DoctorNote | None:
        result = await self.db.execute(
            select(DoctorNote)
            .where(DoctorNote.note_id == note_id)
            .options(selectinload(DoctorNote.recorder))
        )
        return result.scalar_one_or_none()

    async def get_by_baby(
        self,
        baby_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[DoctorNote]:
        result = await self.db.execute(
            select(DoctorNote)
            .where(DoctorNote.baby_id == baby_id)
            .options(selectinload(DoctorNote.recorder))
            .order_by(DoctorNote.observation_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_by_baby(self, baby_id: uuid.UUID) -> DoctorNote | None:
        records = await self.get_by_baby(baby_id, limit=1)
        return records[0] if records else None
