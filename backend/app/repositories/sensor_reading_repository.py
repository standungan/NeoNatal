import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading


class SensorReadingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, reading: SensorReading) -> SensorReading:
        self.db.add(reading)
        await self.db.flush()
        await self.db.refresh(reading)
        return reading

    async def get_recent(self, incubator_id: uuid.UUID, limit: int = 120) -> list[SensorReading]:
        """Newest-first slice for the chart backfill.

        Served straight off idx_sensor_readings_incubator_time; callers reverse it
        for plotting (charts want oldest → newest).
        """
        result = await self.db.execute(
            select(SensorReading)
            .where(SensorReading.incubator_id == incubator_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def sparkline_by_incubator(
        self, incubator_ids: list[uuid.UUID], metric: str = "suhu_bayi", points: int = 30
    ) -> dict[uuid.UUID, list[float | None]]:
        """Last `points` values of one metric for many incubators, oldest first.

        A window function rather than a query per card: the dashboard renders
        every incubator at once, so per-card fetching would be an N+1 on every
        poll. `metric` is interpolated, so it is checked against a whitelist —
        never take a column name from a caller unvalidated.
        """
        allowed = {
            "suhu_bayi", "suhu_inkubator", "kelembapan_inkubator",
            "heart_rate", "spo2",
        }
        if metric not in allowed:
            raise ValueError(f"unsupported sparkline metric: {metric}")
        if not incubator_ids:
            return {}

        rows = await self.db.execute(
            text(
                f"""
                SELECT incubator_id, {metric} AS v
                FROM (
                    SELECT incubator_id, {metric},
                           row_number() OVER (
                               PARTITION BY incubator_id ORDER BY recorded_at DESC
                           ) AS rn
                    FROM sensor_readings
                    WHERE incubator_id = ANY(:ids)
                ) t
                WHERE rn <= :points
                ORDER BY incubator_id, rn DESC
                """
            ),
            {"ids": incubator_ids, "points": points},
        )
        out: dict[uuid.UUID, list[float | None]] = {}
        for inc_id, v in rows.all():
            out.setdefault(inc_id, []).append(None if v is None else float(v))
        return out
