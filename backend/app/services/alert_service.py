"""Threshold alert engine (updates03 P4).

Runs inline in the ingest path, after the reading is stored. Three rules from the
plan, none of them incidental:

1. **Thresholds come from the incubator**, via `incubator_service`'s merged
   defaults + admin overrides — the same source the chart's bands use. Hardcoding
   them here would let the chart and the alarm disagree about what "normal" is.

2. **Debounce: N consecutive breaching readings before opening, N consecutive
   in-range before resolving.** This hardware makes it essential — the pulse-ox
   drops in and out constantly, and single-sample triggering would produce an
   alarm storm that staff would learn to ignore.

3. **Only metrics a real sensor produces may fire.** `respiratory_rate` has no
   producer, so no apnea alert; likewise nothing for door/noise/light.

The debounce window is read from the database rather than kept in memory: a
process restart must not silently re-arm every alarm, and the legacy ingest path
has no per-device state to hang it on.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.baby import Baby
from app.models.incubator import Incubator
from app.models.user import User
from app.models.sensor_alert import SensorAlert
from app.models.sensor_reading import SensorReading
from app.repositories.assignment_repository import AssignmentRepository
from app.services.audit_service import log_action
from app.schemas.incubator import DEFAULT_THRESHOLDS
from app.schemas.telemetry import SensorAlertResponse

# Consecutive readings required to open, and to resolve. 3 ≈ 9 s at the
# firmware's 3 s cadence: long enough to ride out a probe glitch, short enough
# that a real desaturation is not missed.
CONSECUTIVE_TO_OPEN = 3
CONSECUTIVE_TO_RESOLVE = 3

# Metric → the alert type a breach raises. A metric absent from this map cannot
# alert at all, which is how respiratory_rate stays silent while still being a
# column: nothing produces it, so nothing may alarm on it.
_LOW_ALERT = {
    "spo2": "desaturation",
    "heart_rate": "bradycardia",
    "suhu_bayi": "temp_out_of_range",
    "suhu_inkubator": "temp_out_of_range",
    "kelembapan_inkubator": None,  # tracked on the chart, not alarmed on
}
_HIGH_ALERT = {
    "spo2": None,  # a high SpO2 is not a clinical alarm
    "heart_rate": "tachycardia",
    "suhu_bayi": "temp_out_of_range",
    "suhu_inkubator": "temp_out_of_range",
    "kelembapan_inkubator": None,
}

ALERTABLE_METRICS = [
    k for k in _LOW_ALERT if _LOW_ALERT.get(k) or _HIGH_ALERT.get(k)
]


def _effective_thresholds(inc: Incubator) -> dict[str, dict]:
    """Admin overrides merged over the defaults — the same merge the API serves."""
    stored = inc.alert_thresholds or {}
    out: dict[str, dict] = {}
    for key, dflt in DEFAULT_THRESHOLDS.items():
        s = stored.get(key) or {}
        out[key] = {
            "min": s.get("min", dflt["min"]),
            "max": s.get("max", dflt["max"]),
        }
    return out


def _breach(value, bounds: dict) -> tuple[str | None, float | None]:
    """(direction, crossed bound) for a value, or (None, None) if in range."""
    if value is None:
        return None, None
    v = float(value)
    lo, hi = bounds.get("min"), bounds.get("max")
    if lo is not None and v < float(lo):
        return "low", float(lo)
    if hi is not None and v > float(hi):
        return "high", float(hi)
    return None, None


def _alert_type_for(metric: str, direction: str) -> str | None:
    return (_LOW_ALERT if direction == "low" else _HIGH_ALERT).get(metric)


async def has_open_alert(incubator_id: uuid.UUID, db: AsyncSession) -> bool:
    """Is this engine currently flagging a breach on this incubator?

    Exposed so other modules can ask before clearing `status='warning'` — the
    status has three independent producers, and none of them should silently
    resolve another's flag.
    """
    row = (
        await db.execute(
            select(SensorAlert.alert_id).where(
                SensorAlert.incubator_id == incubator_id,
                SensorAlert.resolved_at.is_(None),
            )
        )
    ).first()
    return row is not None


async def evaluate(
    incubator_id: uuid.UUID, db: AsyncSession
) -> list[SensorAlert]:
    """Open or resolve alerts for one incubator, based on its recent readings.

    Called after a reading is stored. Returns the alerts that CHANGED state, so
    the caller can act on them (broadcast, notify) without re-querying.

    Deliberately does not raise: the reading is already committed, and a fault in
    the alarm logic must not turn a stored reading into a failed request.
    """
    inc = await db.get(Incubator, incubator_id)
    if inc is None:
        return []

    window = max(CONSECUTIVE_TO_OPEN, CONSECUTIVE_TO_RESOLVE)
    recent = (
        (
            await db.execute(
                select(SensorReading)
                .where(SensorReading.incubator_id == incubator_id)
                .order_by(SensorReading.recorded_at.desc())
                .limit(window)
            )
        )
        .scalars()
        .all()
    )
    if not recent:
        return []

    thresholds = _effective_thresholds(inc)
    open_alerts = {
        a.alert_type: a
        for a in (
            await db.execute(
                select(SensorAlert).where(
                    SensorAlert.incubator_id == incubator_id,
                    SensorAlert.resolved_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    }

    assignment = await AssignmentRepository(db).get_active_by_incubator(incubator_id)
    baby_id = assignment.baby_id if assignment else None

    changed: list[SensorAlert] = []
    # An alert type can be raised by more than one metric (temp_out_of_range from
    # either probe), so decide per type: still breaching if ANY of its metrics is.
    breaching_types: dict[str, tuple[str, float, float]] = {}

    for metric in ALERTABLE_METRICS:
        bounds = thresholds.get(metric)
        if not bounds:
            continue

        values = [r.metric_value(metric) for r in recent]
        # Nulls are "no reading", not "in range": they neither open nor resolve.
        # A probe that is off cannot prove a baby is well.
        latest = values[0] if values else None

        direction, crossed = _breach(latest, bounds)
        if direction is None:
            continue
        atype = _alert_type_for(metric, direction)
        if atype is None:
            continue

        breaching = [
            v for v in values[:CONSECUTIVE_TO_OPEN] if v is not None
        ]
        if len(breaching) < CONSECUTIVE_TO_OPEN:
            continue  # not enough readings yet to be sure
        if not all(_breach(v, bounds)[0] == direction for v in breaching):
            continue  # not consecutive

        breaching_types[atype] = (metric, float(latest), crossed)

    # ── open new alerts ────────────────────────────────────────────────────────
    for atype, (metric, value, crossed) in breaching_types.items():
        if atype in open_alerts:
            continue  # already open; the partial unique index enforces this too
        alert = SensorAlert(
            incubator_id=incubator_id,
            baby_id=baby_id,
            alert_type=atype,
            metric_key=metric,
            severity="warning",
            value=Decimal(str(round(value, 2))),
            threshold=Decimal(str(round(crossed, 2))),
        )
        db.add(alert)
        changed.append(alert)

    # ── resolve alerts whose metric has been in range for N readings ───────────
    for atype, alert in open_alerts.items():
        if atype in breaching_types:
            continue
        bounds = thresholds.get(alert.metric_key)
        if not bounds:
            continue
        values = [r.metric_value(alert.metric_key) for r in recent]
        recovered = [v for v in values[:CONSECUTIVE_TO_RESOLVE] if v is not None]
        if len(recovered) < CONSECUTIVE_TO_RESOLVE:
            continue
        if any(_breach(v, bounds)[0] is not None for v in recovered):
            continue
        alert.resolved_at = datetime.now(timezone.utc)
        changed.append(alert)

    await db.flush()
    # Only hand back control of the status if THIS engine resolved something.
    resolved_any = any(a.resolved_at is not None for a in changed)
    await _sync_incubator_status(inc, db, resolved_any=resolved_any)
    return changed



async def _sync_incubator_status(
    inc: Incubator, db: AsyncSession, *, resolved_any: bool = False
) -> None:
    """Keep `incubators.status` in step with whether any alert is open.

    Two things this must NOT do:

    'warning' has three producers — this engine, an observation item scored 0
    (observation_service), and a manual vitals entry (monitoring_service). So a
    warning with no open sensor alert belongs to someone else, and clearing it
    would silently erase a clinical flag a nurse set. The status is only handed
    back when this call actually resolved an alert of its own.

    And on recovery it returns to 'terisi' ONLY if a baby is really assigned;
    restoring it blindly would mark an empty incubator as occupied.
    'tidak_tersedia' is never touched — that is a human decision about hardware.
    """
    if inc.status == "tidak_tersedia":
        return

    still_open = (
        await db.execute(
            select(SensorAlert.alert_id).where(
                SensorAlert.incubator_id == inc.incubator_id,
                SensorAlert.resolved_at.is_(None),
            )
        )
    ).first()

    if still_open:
        inc.status = "warning"
        return

    if inc.status == "warning" and resolved_any:
        assignment = await AssignmentRepository(db).get_active_by_incubator(
            inc.incubator_id
        )
        inc.status = "terisi" if assignment else "kosong"


# ── Feed + acknowledgement ──────────────────────────────────────────────────────


async def list_for_incubator(
    incubator_id: uuid.UUID,
    db: AsyncSession,
    *,
    only_open: bool = False,
    limit: int = 50,
) -> list[SensorAlertResponse]:
    """Alert history for one incubator, newest first.

    Joins the baby and acknowledging user so the feed reads as prose rather than
    a wall of UUIDs — an alarm log nobody can interpret is barely better than none.
    """
    q = (
        select(SensorAlert, Baby.baby_name, User.full_name)
        .outerjoin(Baby, Baby.baby_id == SensorAlert.baby_id)
        .outerjoin(User, User.id == SensorAlert.acknowledged_by)
        .where(SensorAlert.incubator_id == incubator_id)
        .order_by(SensorAlert.started_at.desc())
        .limit(limit)
    )
    if only_open:
        q = q.where(SensorAlert.resolved_at.is_(None))

    out: list[SensorAlertResponse] = []
    for alert, baby_name, ack_name in (await db.execute(q)).all():
        item = SensorAlertResponse.model_validate(alert)
        item.baby_name = baby_name
        item.acknowledged_by_name = ack_name
        out.append(item)
    return out


async def acknowledge(
    alert_id: uuid.UUID,
    db: AsyncSession,
    *,
    actor_id: uuid.UUID,
    ip: str | None = None,
) -> SensorAlertResponse:
    """Record that a human has seen this alert.

    Acknowledging does NOT resolve it: the breach either persists or it does not,
    and that is decided by readings, never by a click. Conflating the two would
    let an alarm be silenced while the baby is still out of range.
    """
    alert = await db.get(SensorAlert, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Alert tidak ditemukan"
        )
    if alert.acknowledged_at is None:
        alert.acknowledged_by = actor_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        await db.flush()
        await log_action(
            db,
            user_id=actor_id,
            action="UPDATE",
            table_name="sensor_alerts",
            record_id=alert.alert_id,
            ip_address=ip,
            details={"alert_type": alert.alert_type, "acknowledged": True},
        )
    return SensorAlertResponse.model_validate(alert)
