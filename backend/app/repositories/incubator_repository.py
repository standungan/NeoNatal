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
        """Every incubator, archived ones included.

        Numbering reads this, so an archived incubator's number is never handed to
        a new one — "Inkubator 03" in a baby's history must keep meaning one box.
        """
        result = await self.db.execute(
            select(Incubator).order_by(Incubator.incubator_no)
        )
        return list(result.scalars().all())

    async def get_all_with_assignment(self, archived: bool = False) -> list[Incubator]:
        """Incubators with their active assignment + baby, for the dashboard.

        Archived incubators are left out unless asked for — they only appear in the
        archive list.
        """
        result = await self.db.execute(
            select(Incubator)
            .where(
                Incubator.archived_at.is_not(None)
                if archived
                else Incubator.archived_at.is_(None)
            )
            .options(
                selectinload(Incubator.assignments.and_(
                    BabyIncubatorAssignment.status == "active"
                )).selectinload(BabyIncubatorAssignment.baby)
            )
            .order_by(Incubator.incubator_no)
        )
        return list(result.scalars().all())

    async def ids_with_history(self, incubator_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """Which of these incubators have ever held a baby — the ones that can only be archived."""
        if not incubator_ids:
            return set()
        result = await self.db.execute(
            select(BabyIncubatorAssignment.incubator_id)
            .where(BabyIncubatorAssignment.incubator_id.in_(incubator_ids))
            .distinct()
        )
        return set(result.scalars().all())

    async def get_by_no(self, incubator_no: str) -> Incubator | None:
        """Look up by the human-facing number ("01"), not the UUID.

        Used by the legacy ingest route, whose firmware identifies itself with a
        label like "inc1" rather than a key.
        """
        result = await self.db.execute(
            select(Incubator).where(Incubator.incubator_no == incubator_no)
        )
        return result.scalar_one_or_none()

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
            .where(Incubator.status == "kosong", Incubator.archived_at.is_(None))
            .order_by(Incubator.incubator_no)
        )
        return list(result.scalars().all())
