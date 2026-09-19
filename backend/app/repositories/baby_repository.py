import uuid

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import BabyIncubatorAssignment
from app.models.baby import Baby
from app.models.incubator import Incubator
from app.models.monitoring import MonitoringRecord
from app.models.parent import Parent


class BabyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self, *, status: str = "aktif", q: str | None = None, limit: int = 100
    ) -> list[Baby]:
        """Babies for the list view, newest first.

        `status`: "aktif" (in an incubator), "pulang" (discharged) or "semua".
        `q` matches the name, the baby's medical-record number, or any of their
        NICU registration numbers — the three things staff look a baby up by.
        """
        stmt = select(Baby)
        if status == "aktif":
            stmt = stmt.where(Baby.is_active == True)  # noqa: E712
        elif status == "pulang":
            stmt = stmt.where(Baby.is_active == False)  # noqa: E712
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Baby.baby_name.ilike(like),
                    Baby.no_rm_bayi.ilike(like),
                    exists().where(
                        BabyIncubatorAssignment.baby_id == Baby.baby_id,
                        BabyIncubatorAssignment.no_registrasi_nicu.ilike(like),
                    ),
                )
            )
        result = await self.db.execute(stmt.order_by(Baby.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def get_by_id(self, baby_id: uuid.UUID) -> Baby | None:
        result = await self.db.execute(
            select(Baby)
            .where(Baby.baby_id == baby_id)
            .options(
                selectinload(Baby.parent),
                selectinload(Baby.maternal_record),
                selectinload(Baby.assignments.and_(
                    BabyIncubatorAssignment.status == "active"
                )).selectinload(BabyIncubatorAssignment.incubator),
                selectinload(Baby.assignments.and_(
                    BabyIncubatorAssignment.status == "active"
                )).selectinload(BabyIncubatorAssignment.assigned_by_user),
                selectinload(Baby.assignments.and_(
                    BabyIncubatorAssignment.status == "active"
                )).selectinload(BabyIncubatorAssignment.dpjp),
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_monitoring(self, baby_id: uuid.UUID) -> MonitoringRecord | None:
        result = await self.db.execute(
            select(MonitoringRecord)
            .where(MonitoringRecord.baby_id == baby_id)
            .order_by(MonitoringRecord.observation_time.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, baby: Baby) -> Baby:
        self.db.add(baby)
        await self.db.flush()
        await self.db.refresh(baby)
        return baby

    async def update(self, baby: Baby) -> Baby:
        await self.db.flush()
        await self.db.refresh(baby)
        return baby
