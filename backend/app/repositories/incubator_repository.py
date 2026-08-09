import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import BabyIncubatorAssignment
from app.models.incubator import Incubator


class IncubatorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Incubator]:
        result = await self.db.execute(
            select(Incubator).order_by(Incubator.incubator_no)
        )
        return list(result.scalars().all())

    async def get_all_with_assignment(self) -> list[Incubator]:
        """Load incubators with their active assignment + baby for the dashboard."""
        result = await self.db.execute(
            select(Incubator)
            .options(
                selectinload(Incubator.assignments.and_(
                    BabyIncubatorAssignment.status == "active"
                )).selectinload(BabyIncubatorAssignment.baby)
            )
            .order_by(Incubator.incubator_no)
        )
        return list(result.scalars().all())

    async def get_by_id(self, incubator_id: uuid.UUID) -> Incubator | None:
        result = await self.db.execute(
            select(Incubator).where(Incubator.incubator_id == incubator_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_assignment(self, incubator_id: uuid.UUID) -> Incubator | None:
        result = await self.db.execute(
            select(Incubator)
            .where(Incubator.incubator_id == incubator_id)
            .options(
                selectinload(Incubator.assignments.and_(
                    BabyIncubatorAssignment.status == "active"
                )).selectinload(BabyIncubatorAssignment.baby)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, incubator: Incubator) -> Incubator:
        self.db.add(incubator)
        await self.db.flush()
        await self.db.refresh(incubator)
        return incubator

    async def update(self, incubator: Incubator) -> Incubator:
        await self.db.flush()
        await self.db.refresh(incubator)
        return incubator

    async def delete(self, incubator: Incubator) -> None:
        await self.db.delete(incubator)
        await self.db.flush()

    async def has_assignments(self, incubator_id: uuid.UUID) -> bool:
        """True if any assignment (active or historical) references this incubator."""
        result = await self.db.execute(
            select(BabyIncubatorAssignment.assignment_id)
            .where(BabyIncubatorAssignment.incubator_id == incubator_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def has_active_assignment(self, incubator_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(BabyIncubatorAssignment.assignment_id)
            .where(
                and_(
                    BabyIncubatorAssignment.incubator_id == incubator_id,
                    BabyIncubatorAssignment.status == "active",
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_available(self) -> list[Incubator]:
        """Return incubators that can accept a new baby."""
        result = await self.db.execute(
            select(Incubator)
            .where(Incubator.status == "kosong")
            .order_by(Incubator.incubator_no)
        )
        return list(result.scalars().all())
