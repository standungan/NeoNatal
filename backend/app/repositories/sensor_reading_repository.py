import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading

# Metrics with a minute rollup — the ones a baby's history chart can draw.
# respiratory_rate has no producer and no rollup column.
HISTORY_METRICS = (
    "suhu_bayi",
    "suhu_inkubator",
    "kelembapan_inkubator",
    "heart_rate",
    "spo2",
)


class SensorReadingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, reading: SensorReading) -> SensorReading:
        self.db.add(reading)
        await self.db.flush()
        await self.db.refresh(reading)
        return reading

    async def get_recent(
        self, incubator_id: uuid.UUID, limit: int = 120, since: datetime | None = None
    ) -> list[SensorReading]:
        """Newest-first slice for the chart backfill.

        Served straight off idx_sensor_readings_incubator_time; callers reverse it
        for plotting (charts want oldest → newest). `since` cuts it at the start of
        the incubator's current occupancy, so a new baby's chart never opens on the
        previous baby's last readings.
        """
        q = select(SensorReading).where(SensorReading.incubator_id == incubator_id)
        if since is not None:
            q = q.where(SensorReading.recorded_at >= since)
        result = await self.db.execute(
            q.order_by(SensorReading.recorded_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def sparkline_by_incubator(
        self,
        incubator_ids: list[uuid.UUID],
        metric: str = "suhu_bayi",
        points: int = 30,
        since: dict[uuid.UUID, datetime] | None = None,
    ) -> dict[uuid.UUID, list[float | None]]:
        """Last `points` values of one metric for many incubators, oldest first.

        A window function rather than a query per card: the dashboard renders
        every incubator at once, so per-card fetching would be an N+1 on every
        poll. `metric` is interpolated, so it is checked against a whitelist —
        never take a column name from a caller unvalidated.

        `since` maps an incubator to the start of its current occupancy; readings
        before it belong to an earlier baby and stay off this card.
        """
        allowed = {
            "suhu_bayi", "suhu_inkubator", "kelembapan_inkubator",
            "heart_rate", "spo2",
        }
        if metric not in allowed:
            raise ValueError(f"unsupported sparkline metric: {metric}")
        if not incubator_ids:
            return {}
        since = since or {}
        starts = [since.get(i) for i in incubator_ids]

        rows = await self.db.execute(
            text(
                f"""
                SELECT incubator_id, {metric} AS v
                FROM (
                    SELECT r.incubator_id, r.{metric},
                           row_number() OVER (
                               PARTITION BY r.incubator_id ORDER BY r.recorded_at DESC
                           ) AS rn
                    FROM sensor_readings r
                    JOIN unnest(CAST(:ids AS uuid[]), CAST(:starts AS timestamptz[]))
                         AS p(incubator_id, since)
                      ON p.incubator_id = r.incubator_id
                    WHERE p.since IS NULL OR r.recorded_at >= p.since
                ) t
                WHERE rn <= :points
                ORDER BY incubator_id, rn DESC
                """
            ),
            {"ids": incubator_ids, "starts": starts, "points": points},
        )
        out: dict[uuid.UUID, list[float | None]] = {}
        for inc_id, v in rows.all():
            out.setdefault(inc_id, []).append(None if v is None else float(v))
        return out

    async def baby_history(self, baby_id: uuid.UUID, max_points: int = 600) -> tuple[int, list[dict]]:
        """One baby's whole sensor history, evenly bucketed. Returns (bucket_minutes, rows).

        Raw readings are pruned after the retention window, so the history is the
        union of two sources: the minute rollups (everything older) and raw rows
        not yet rolled up, summarised to the same per-minute shape on the fly. A
        minute that exists in both is taken from the rollup only.

        Keyed on baby_id rather than incubator: this is what survives the
        incubator being reused by the next baby, or archived.

        Buckets are widened so a stay of any length comes back as at most
        `max_points` rows, each with avg AND min/max — a bucket mean alone would
        hide a short desaturation, which is the event worth seeing.
        """
        m = HISTORY_METRICS
        rollup_cols = ", ".join(
            f"{x}_avg AS {x}, {x}_min, {x}_max" for x in m
        )
        raw_cols = ", ".join(
            f"AVG(r.{x}) AS {x}, MIN(r.{x}) AS {x}_min, MAX(r.{x}) AS {x}_max" for x in m
        )
        bucket_cols = ", ".join(
            f"AVG(p.{x}) AS {x}, MIN(p.{x}_min) AS {x}_min, MAX(p.{x}_max) AS {x}_max"
            for x in m
        )
        rows = await self.db.execute(
            text(
                f"""
                WITH per_minute AS (
                    SELECT minute AS t, sample_count AS n, {rollup_cols}
                    FROM sensor_reading_minutes
                    WHERE baby_id = :baby
                  UNION ALL
                    SELECT date_trunc('minute', r.recorded_at) AS t, COUNT(*) AS n, {raw_cols}
                    FROM sensor_readings r
                    WHERE r.baby_id = :baby
                      AND NOT EXISTS (
                          SELECT 1 FROM sensor_reading_minutes mm
                          WHERE mm.incubator_id = r.incubator_id
                            AND mm.minute = date_trunc('minute', r.recorded_at)
                      )
                    GROUP BY date_trunc('minute', r.recorded_at)
                ),
                w AS (
                    SELECT min(t) AS t0,
                           GREATEST(1, CEIL(
                               (EXTRACT(EPOCH FROM max(t) - min(t)) / 60 + 1) / :max_points
                           ))::int AS width
                    FROM per_minute
                )
                SELECT w.width AS width,
                       w.t0 + make_interval(
                           mins => (FLOOR(EXTRACT(EPOCH FROM p.t - w.t0) / 60 / w.width) * w.width)::int
                       ) AS t,
                       SUM(p.n)::int AS samples,
                       {bucket_cols}
                FROM per_minute p CROSS JOIN w
                GROUP BY w.width, 2
                ORDER BY 2
                """
            ),
            {"baby": baby_id, "max_points": max_points},
        )
        out = [dict(r._mapping) for r in rows.all()]
        width = out[0]["width"] if out else 1
        for r in out:
            del r["width"]
        return width, out
