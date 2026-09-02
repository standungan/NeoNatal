import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device


class DeviceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_key_hash(self, key_hash: str) -> Device | None:
        """Single indexed equality lookup — the hot path, hit on every POST."""
        result = await self.db.execute(
            select(Device).where(Device.device_key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_incubator(self, incubator_id: uuid.UUID) -> Device | None:
        result = await self.db.execute(
            select(Device).where(Device.incubator_id == incubator_id)
        )
        return result.scalar_one_or_none()

    async def get_by_incubator_ids(
        self, incubator_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Device]:
        """Devices for many incubators at once, keyed by incubator_id.

        The dashboard renders one card per incubator; fetching each card's
        device separately would be a query per incubator on every poll.
        """
        if not incubator_ids:
            return {}
        result = await self.db.execute(
            select(Device).where(Device.incubator_id.in_(incubator_ids))
        )
        return {d.incubator_id: d for d in result.scalars().all()}

    async def create(self, device: Device) -> Device:
        self.db.add(device)
        await self.db.flush()
        await self.db.refresh(device)
        return device

    async def delete(self, device: Device) -> None:
        await self.db.delete(device)
        await self.db.flush()

    async def touch_last_seen(self, device: Device, ip: str | None = None) -> None:
        device.last_seen_at = datetime.now(timezone.utc)
        if ip:
            device.last_ip = ip
        await self.db.flush()
