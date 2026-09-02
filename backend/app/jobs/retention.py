"""Retention runner: in-process scheduler plus a CLI entry point.

    python -m app.jobs.retention          # run once, now

⚠️ Single-process assumption, same as the SSE fan-out: docker-compose runs
uvicorn with no `--workers`, so exactly one loop exists. If workers are ever
added, every worker would run this concurrently — the rollup is idempotent and
the prune is guarded, so the result stays correct, but the work would be done N
times. Set SENSOR_RETENTION_INTERVAL_HOURS=0 and use cron in that case.
"""

import asyncio
import logging

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services import retention_service

log = logging.getLogger(__name__)


async def run_once() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        result = await retention_service.run_retention(
            db, retention_days=settings.sensor_retention_days
        )
    log.info(
        "retention: %s buckets written, %s raw rows pruned%s",
        result["buckets"], result["pruned"],
        " (disabled)" if result["skipped"] else "",
    )
    return result


async def run_forever() -> None:
    """Periodic loop, started from the app lifespan when the interval is > 0."""
    interval = settings.sensor_retention_interval_hours
    if interval <= 0:
        log.info("retention: in-process job disabled (interval = 0)")
        return
    while True:
        try:
            await run_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Retention failing must never take the API down with it; the next
            # tick retries, and the symptom is a table that grows.
            log.exception("retention run failed")
        await asyncio.sleep(interval * 3600)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(asyncio.run(run_once()))
