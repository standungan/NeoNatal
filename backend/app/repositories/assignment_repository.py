import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import BabyIncubatorAssignment


class AssignmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_by_baby(self, baby_id: uuid.UUID) -> BabyIncubatorAssignment | None:
        result = await self.db.execute(
            select(BabyIncubatorAssignment)
            .where(
                BabyIncubatorAssignment.baby_id == baby_id,
                BabyIncubatorAssignment.status == "active",
            )
            .options(selectinload(BabyIncubatorAssignment.incubator))
        )
        return result.scalar_one_or_none()

    async def get_active_by_incubator(self, incubator_id: uuid.UUID) -> BabyIncubatorAssignment | None:
        result = await self.db.execute(
            select(BabyIncubatorAssignment)
            .where(
                BabyIncubatorAssignment.incubator_id == incubator_id,
                BabyIncubatorAssignment.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_baby(self, baby_id: uuid.UUID) -> list[BabyIncubatorAssignment]:
        """Every placement this baby has had, active or not, newest first."""
        result = await self.db.execute(
            select(BabyIncubatorAssignment)
            .where(BabyIncubatorAssignment.baby_id == baby_id)
            .options(
                selectinload(BabyIncubatorAssignment.incubator),
                selectinload(BabyIncubatorAssignment.assigned_by_user),
                selectinload(BabyIncubatorAssignment.dpjp),
            )
            .order_by(BabyIncubatorAssignment.assigned_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_incubator(self, incubator_id: uuid.UUID) -> list[BabyIncubatorAssignment]:
        """Every baby this incubator has held, newest first — its usage history."""
        result = await self.db.execute(
            select(BabyIncubatorAssignment)
            .where(BabyIncubatorAssignment.incubator_id == incubator_id)
            .options(
                selectinload(BabyIncubatorAssignment.baby),
                selectinload(BabyIncubatorAssignment.assigned_by_user),
                selectinload(BabyIncubatorAssignment.dpjp),
            )
            .order_by(BabyIncubatorAssignment.assigned_at.desc())
        )
        return list(result.scalars().all())

    async def latest_by_babies(
        self, baby_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, BabyIncubatorAssignment]:
        """The most recent placement per baby, for list views. One query, not one per row."""
        if not baby_ids:
            return {}
        result = await self.db.execute(
            select(BabyIncubatorAssignment)
            .where(BabyIncubatorAssignment.baby_id.in_(baby_ids))
            .options(
                selectinload(BabyIncubatorAssignment.incubator),
                selectinload(BabyIncubatorAssignment.assigned_by_user),
                selectinload(BabyIncubatorAssignment.dpjp),
            )
            .order_by(BabyIncubatorAssignment.assigned_at.desc())
        )
        out: dict[uuid.UUID, BabyIncubatorAssignment] = {}
        for a in result.scalars().all():
            out.setdefault(a.baby_id, a)  # first seen = newest
        return out

    async def occupancy_starts(
        self, incubator_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, datetime]:
        """When each incubator's current period began.

        Occupied: the current baby's admission. Empty: the last discharge. Never
        used: absent from the result, meaning "everything is current".

        This is the line that keeps one baby's sensor data off the next baby's
        screen: an incubator page shows readings and alerts from this moment on,
        and everything earlier belongs to — and is shown with — the baby it was
        recorded for.
        """
        if not incubator_ids:
            return {}
        a = BabyIncubatorAssignment
        result = await self.db.execute(
            select(
                a.incubator_id,
                func.max(a.assigned_at).filter(a.status == "active"),
                func.max(a.discharged_at),
            )
            .where(a.incubator_id.in_(incubator_ids))
            .group_by(a.incubator_id)
        )
        out: dict[uuid.UUID, datetime] = {}
        for inc_id, active_start, last_end in result.all():
            start = active_start or last_end
            if start is not None:
                out[inc_id] = start
        return out

    async def occupancy_start(self, incubator_id: uuid.UUID) -> datetime | None:
        return (await self.occupancy_starts([incubator_id])).get(incubator_id)

    async def create(self, assignment: BabyIncubatorAssignment) -> BabyIncubatorAssignment:
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def update(self, assignment: BabyIncubatorAssignment) -> BabyIncubatorAssignment:
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment
