"""Retention: roll raw sensor readings into 1-minute buckets, then prune (P4).

At the firmware's 3 s cadence one incubator writes ~28,800 rows/day — about
8.6 M/month across ten. The plan treats this as a hard deliverable rather than an
open question, and the chosen trade is to keep the 3 s cadence (it is what makes
the live chart feel live) and drop raw data once it has been summarised.

**Order matters: roll up first, prune second.** Doing it the other way, or
pruning a window the rollup has not covered, destroys history irrecoverably. The
prune below therefore only ever deletes rows strictly older than the newest
minute that has actually been rolled up.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

# Metrics carried into the rollup. respiratory_rate is excluded: nothing produces
# it, so a bucket of nulls would be noise.
ROLLUP_METRICS = (
    "suhu_bayi",
    "suhu_inkubator",
    "kelembapan_inkubator",
    "heart_rate",
    "spo2",
)


def _agg_columns() -> str:
    parts = []
    for m in ROLLUP_METRICS:
        parts.append(f"AVG({m})::numeric AS {m}_avg")
        parts.append(f"MIN({m})::numeric AS {m}_min")
        parts.append(f"MAX({m})::numeric AS {m}_max")
    return ",\n               ".join(parts)


def _insert_columns() -> tuple[str, str, str]:
    cols, vals, updates = [], [], []
    for m in ROLLUP_METRICS:
        for agg in ("avg", "min", "max"):
            cols.append(f"{m}_{agg}")
            vals.append(f"src.{m}_{agg}")
            updates.append(f"{m}_{agg} = EXCLUDED.{m}_{agg}")
    return ", ".join(cols), ", ".join(vals), ", ".join(updates)


async def rollup(db: AsyncSession, *, before: datetime) -> int:
    """Summarise every raw reading older than `before` into 1-minute buckets.

    Idempotent by construction: ON CONFLICT on (incubator_id, minute) updates the
    bucket, so a job killed halfway can simply be run again. Returns the number
    of buckets written.

    baby_id is taken as the MAX over the minute rather than an arbitrary row —
    an admission mid-minute is vanishingly rare, and picking deterministically
    beats picking at random.
    """
    cols, vals, updates = _insert_columns()
    sql = text(
        f"""
        WITH src AS (
            SELECT incubator_id,
                   MAX(baby_id::text)::uuid AS baby_id,
                   date_trunc('minute', recorded_at) AS minute,
                   COUNT(*)::smallint AS sample_count,
                   {_agg_columns()}
            FROM sensor_readings
            WHERE recorded_at < :before
            GROUP BY incubator_id, date_trunc('minute', recorded_at)
        )
        INSERT INTO sensor_reading_minutes
            (incubator_id, baby_id, minute, sample_count, {cols})
        SELECT src.incubator_id, src.baby_id, src.minute, src.sample_count, {vals}
        FROM src
        ON CONFLICT (incubator_id, minute) DO UPDATE SET
            baby_id = EXCLUDED.baby_id,
            sample_count = EXCLUDED.sample_count,
            {updates}
        """
    ).bindparams(bindparam("before"))
    result = await db.execute(sql, {"before": before})
    return result.rowcount or 0


async def prune(db: AsyncSession, *, before: datetime) -> int:
    """Delete raw readings older than `before`, but ONLY where a bucket exists.

    The guard is the point: without it, a rollup that silently failed would be
    followed by a prune that destroys the data anyway. A row with no bucket
    covering its minute is left alone, and shows up as a growing table rather
    than as missing history.
    """
    sql = text(
        """
        DELETE FROM sensor_readings r
        WHERE r.recorded_at < :before
          AND EXISTS (
              SELECT 1 FROM sensor_reading_minutes m
              WHERE m.incubator_id = r.incubator_id
                AND m.minute = date_trunc('minute', r.recorded_at)
          )
        """
    ).bindparams(bindparam("before"))
    result = await db.execute(sql, {"before": before})
    return result.rowcount or 0


async def run_retention(
    db: AsyncSession, *, retention_days: int, now: datetime | None = None
) -> dict[str, int]:
    """Roll up then prune. Returns counts, for logging and for the tests.

    A `retention_days` of 0 or less is treated as "keep everything": disabling
    retention must be possible without editing code, and the failure mode of a
    misread config should be keeping too much, never deleting too much.
    """
    if retention_days <= 0:
        return {"buckets": 0, "pruned": 0, "skipped": 1}

    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)

    buckets = await rollup(db, before=cutoff)
    pruned = await prune(db, before=cutoff)
    await db.commit()
    return {"buckets": buckets, "pruned": pruned, "skipped": 0}


async def recent_buckets(
    incubator_id: uuid.UUID, db: AsyncSession, *, limit: int = 240
) -> list[dict]:
    """Rolled-up history for one incubator, oldest first.

    Kept here rather than in telemetry_service because it answers a different
    question: telemetry serves the live window, this serves what survived it.
    """
    cols = ", ".join(
        f"{m}_{agg}" for m in ROLLUP_METRICS for agg in ("avg", "min", "max")
    )
    rows = await db.execute(
        text(
            f"""
            SELECT minute, sample_count, {cols}
            FROM sensor_reading_minutes
            WHERE incubator_id = :inc
            ORDER BY minute DESC
            LIMIT :limit
            """
        ),
        {"inc": incubator_id, "limit": limit},
    )
    return [dict(r._mapping) for r in reversed(rows.all())]
