"""In-process fan-out of sensor readings to SSE subscribers.

Steps 1-7 of ingest are transactional and live in telemetry_service; everything
here is process-local state that no database sees. Keeping it separate makes
that boundary obvious — nothing in this module may fail an ingest.

⚠️ SINGLE-PROCESS ASSUMPTION. docker-compose.yml runs
`uvicorn app.main:app --host 0.0.0.0 --port 8000` with **no `--workers`**, so a
POST and a subscriber always land in the same process and this dict is enough.
If workers are ever added, a reading ingested by worker 1 will never reach a
subscriber parked on worker 2, and the chart will silently stop updating for
half the users. Crossing that bridge means Postgres LISTEN/NOTIFY or Redis
pub/sub behind the same broadcast() call — not a bigger dict.
"""

import asyncio
import uuid
from collections import defaultdict, deque

from app.schemas.telemetry import SensorReadingResponse

# ~6 minutes at the firmware's 3 s cadence. Replayed to each new subscriber so a
# chart opened mid-stream is never blank while it waits for the next sample.
BUFFER_SIZE = 120

# Bounded so a subscriber that stops reading (a paused tab, a wedged proxy)
# cannot grow a queue without limit. On overflow we drop the OLDEST reading:
# for a live chart, the most recent sample matters more than a stale one.
QUEUE_SIZE = 240

_buffers: dict[uuid.UUID, deque[SensorReadingResponse]] = defaultdict(
    lambda: deque(maxlen=BUFFER_SIZE)
)
_subscribers: dict[uuid.UUID, set[asyncio.Queue]] = defaultdict(set)


def publish(incubator_id: uuid.UUID, reading: SensorReadingResponse) -> None:
    """Record a reading and hand it to every subscriber on this incubator.

    Never raises: ingest has already committed by the time this runs, and a
    broken subscriber must not turn a stored reading into a 500.
    """
    _buffers[incubator_id].append(reading)

    for q in list(_subscribers.get(incubator_id, ())):
        try:
            q.put_nowait(reading)
        except asyncio.QueueFull:
            # Drop the oldest, keep the newest — a live chart wants recency.
            try:
                q.get_nowait()
                q.put_nowait(reading)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass


def replay(incubator_id: uuid.UUID) -> list[SensorReadingResponse]:
    """Everything still in the ring buffer, oldest first (plot order)."""
    return list(_buffers.get(incubator_id, ()))


def subscribe(incubator_id: uuid.UUID) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    _subscribers[incubator_id].add(q)
    return q


def unsubscribe(incubator_id: uuid.UUID, q: asyncio.Queue) -> None:
    """Always call this in a finally: a generator abandoned when the browser
    navigates away would otherwise leak its queue and be published to forever.
    """
    subs = _subscribers.get(incubator_id)
    if subs:
        subs.discard(q)
        if not subs:
            _subscribers.pop(incubator_id, None)


def subscriber_count(incubator_id: uuid.UUID) -> int:
    return len(_subscribers.get(incubator_id, ()))
