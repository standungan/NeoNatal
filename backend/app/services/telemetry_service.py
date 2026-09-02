import ipaddress
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_device_key, hash_device_key
from app.models.device import Device
from app.models.sensor_reading import SensorReading
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.incubator_repository import IncubatorRepository
from app.repositories.sensor_reading_repository import SensorReadingRepository
from app.schemas.telemetry import (
    DeviceCreate,
    DeviceProvisionResponse,
    DeviceResponse,
    DeviceUpdate,
    LegacyTelemetryIn,
    SensorReadingResponse,
    TelemetryAck,
    TelemetryIn,
)
from app.services import alert_service, telemetry_stream
from app.services.audit_service import log_action

def ip_allowed(allowed: str | None, client_ip: str | None) -> bool:
    """Is this source address permitted for a device with `allowed` set?

    Accepts a single address ("192.168.0.2") or a CIDR ("192.168.0.0/24").
    An unset allowlist permits everything, which is the default. A malformed
    value permits everything too, deliberately: a typo in an optional safety
    filter must not silently stop a ward's telemetry.
    """
    if not allowed:
        return True
    if not client_ip:
        return False
    try:
        return ipaddress.ip_address(client_ip) in ipaddress.ip_network(allowed, strict=False)
    except ValueError:
        return True


# ── Ingest ──────────────────────────────────────────────────────────────────────


async def ingest(
    data: TelemetryIn, device: Device, db: AsyncSession, client_ip: str | None = None
) -> TelemetryAck:
    """Store one telemetry sample. Called by POST /api/v1/telemetry.

    The device is already authenticated by the `get_current_device` dependency;
    everything here is about turning a raw sample into a correctly-attributed row.

    Note what the device does NOT get to decide: the timestamp (no RTC on an
    ESP8266), which baby the reading belongs to (that is a runtime assignment
    that flips on admission/discharge), or whether 0 bpm is a real vital sign
    (TelemetryIn normalises that to null).
    """
    if device.incubator_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device belum terpasang pada inkubator manapun",
        )

    await DeviceRepository(db).touch_last_seen(device, ip=client_ip)

    # Device is alive but every sensor came back empty (probe off, DHT22 read
    # failure). last_seen_at above keeps the online badge honest; storing a row
    # of nothing would just pad the table.
    if data.is_empty():
        return TelemetryAck(stored=False)

    # Resolve the baby from the ACTIVE assignment, never from the payload. Null
    # is legitimate here: an idle incubator still reports its air temperature.
    assignment = await AssignmentRepository(db).get_active_by_incubator(device.incubator_id)

    reading = SensorReading(
        incubator_id=device.incubator_id,
        baby_id=assignment.baby_id if assignment else None,
        device_id=device.device_id,
        suhu_bayi=data.suhu_bayi,
        suhu_inkubator=data.suhu_inkubator,
        kelembapan_inkubator=data.kelembapan_inkubator,
        heart_rate=data.heart_rate,
        spo2=data.spo2,
        source="sensor",
    )
    reading = await SensorReadingRepository(db).create(reading)

    # Steps 1-7 above are the transactional part. Everything from here is
    # in-process fan-out: the row is already stored, so a subscriber problem
    # must never turn a successful ingest into an error.
    telemetry_stream.publish(
        device.incubator_id, SensorReadingResponse.model_validate(reading)
    )
    await alert_service.evaluate(device.incubator_id, db)

    return TelemetryAck(stored=True, reading_id=reading.reading_id)


async def latest_for_baby(
    baby_id: uuid.UUID, db: AsyncSession
) -> SensorReadingResponse | None:
    """Most recent sensor reading for whichever incubator this baby occupies.

    Baby-scoped on purpose: the vitals form is opened for a baby, not an
    incubator, and resolving the assignment here keeps that lookup off the
    client — where it would go stale the moment a baby is moved.

    Returns None when there is no active assignment or no readings yet; both are
    ordinary states, not errors.
    """
    assignment = await AssignmentRepository(db).get_active_by_baby(baby_id)
    if assignment is None:
        return None
    rows = await SensorReadingRepository(db).get_recent(assignment.incubator_id, 1)
    return SensorReadingResponse.model_validate(rows[0]) if rows else None


# ── Legacy prototype ingest ─────────────────────────────────────────────────────


def _incubator_no_from_label(label: str) -> str:
    """Map the firmware's label ("inc1") to an incubator_no ("01").

    The prototype identifies its position with a free-text label rather than a
    key. Anything non-numeric is passed through untouched, so a rig flashed with
    "01" works without special-casing.
    """
    digits = "".join(ch for ch in label if ch.isdigit())
    return digits.zfill(2) if digits else label


async def ingest_legacy(
    data: LegacyTelemetryIn, db: AsyncSession, client_ip: str | None = None
) -> TelemetryAck:
    """Store one sample from the prototype firmware (POST /api/sensors).

    Everything after the rename is the authenticated path's logic, reached via
    TelemetryIn: the same 0-means-no-reading normalisation, the same range
    limits, the same server-assigned timestamp, and the same rule that baby_id
    comes from the ACTIVE assignment and never from the payload.

    The one real difference is that nothing here proves which device is talking,
    which is why the route is off unless settings.legacy_sensor_ingest is set.
    """
    incubator_no = _incubator_no_from_label(data.incubator_id)
    inc = await IncubatorRepository(db).get_by_no(incubator_no)
    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inkubator '{data.incubator_id}' tidak dikenal (dicari sebagai '{incubator_no}')",
        )

    # The allowlist is checked against the incubator's bound device, if one
    # exists. Nothing here authenticates the caller -- this only narrows who can
    # reach an already-unauthenticated route, so it is defence in depth and not
    # a substitute for the device key.
    bound = await DeviceRepository(db).get_by_incubator(inc.incubator_id)
    if bound is not None and not ip_allowed(bound.allowed_ip, client_ip):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Alamat {client_ip} tidak diizinkan untuk inkubator ini",
        )

    payload = data.to_telemetry()
    if payload.is_empty():
        return TelemetryAck(stored=False)

    assignment = await AssignmentRepository(db).get_active_by_incubator(inc.incubator_id)

    reading = SensorReading(
        incubator_id=inc.incubator_id,
        baby_id=assignment.baby_id if assignment else None,
        device_id=None,          # no device identified itself on this route
        suhu_bayi=payload.suhu_bayi,
        suhu_inkubator=payload.suhu_inkubator,
        kelembapan_inkubator=payload.kelembapan_inkubator,
        heart_rate=payload.heart_rate,
        spo2=payload.spo2,
        source="sensor",
    )
    reading = await SensorReadingRepository(db).create(reading)

    # Mark this incubator's device as seen, if one is bound. The reading is not
    # proof that THAT device sent it -- nothing on this route proves identity --
    # but last_seen_at answers "when did this incubator's sensor last report",
    # which is exactly what the online badge is asking. Without this the card
    # reads "Offline" beside a chart that is visibly updating.
    device = await DeviceRepository(db).get_by_incubator(inc.incubator_id)
    if device is not None:
        await DeviceRepository(db).touch_last_seen(device, ip=client_ip)

    telemetry_stream.publish(
        inc.incubator_id, SensorReadingResponse.model_validate(reading)
    )
    # The alert engine keys off the incubator, not the device, so it works
    # identically on this unauthenticated path.
    await alert_service.evaluate(inc.incubator_id, db)

    return TelemetryAck(stored=True, reading_id=reading.reading_id)


# ── Readings (chart backfill) ───────────────────────────────────────────────────


async def get_recent_readings(
    incubator_id: uuid.UUID, db: AsyncSession, limit: int = 120
) -> list[SensorReadingResponse]:
    """Recent samples for one incubator, oldest first.

    The repository returns newest-first (that is the direction the index runs);
    reversing here means every client gets plot order without each one having to
    remember to do it.
    """
    rows = await SensorReadingRepository(db).get_recent(incubator_id, limit)
    return [SensorReadingResponse.model_validate(r) for r in reversed(rows)]


# ── Device provisioning (admin) ─────────────────────────────────────────────────


async def get_device(incubator_id: uuid.UUID, db: AsyncSession) -> DeviceResponse | None:
    device = await DeviceRepository(db).get_by_incubator(incubator_id)
    return DeviceResponse.model_validate(device) if device else None


async def provision_device(
    incubator_id: uuid.UUID,
    data: DeviceCreate,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> DeviceProvisionResponse:
    """Bind a new device to an incubator and mint its key.

    The plaintext key is returned exactly once, here — the row stores only its
    SHA-256. It goes into the firmware's DEVICE_KEY and nowhere else; the audit
    entry records that a key was minted, never the key itself.
    """
    inc = await IncubatorRepository(db).get_by_id(incubator_id)
    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inkubator tidak ditemukan"
        )

    repo = DeviceRepository(db)
    # One device per incubator — also a UNIQUE constraint; checked here to return
    # a readable 409 instead of an IntegrityError.
    if await repo.get_by_incubator(incubator_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inkubator ini sudah memiliki device. Hapus device lama terlebih dahulu.",
        )

    plain_key = generate_device_key()
    device = await repo.create(
        Device(
            incubator_id=incubator_id,
            device_key_hash=hash_device_key(plain_key),
            label=data.label or f"IoT device — INC-{inc.incubator_no}",
        )
    )

    await log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        table_name="devices",
        record_id=device.device_id,
        ip_address=ip,
        details={"incubator_no": inc.incubator_no, "label": device.label},
    )

    return DeviceProvisionResponse(
        **DeviceResponse.model_validate(device).model_dump(), device_key=plain_key
    )


async def update_device(
    incubator_id: uuid.UUID,
    data: DeviceUpdate,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> DeviceResponse:
    """Edit an existing device's label or IP allowlist (admin).

    Never touches the key: rotating a key means revoke + re-provision, because
    the plaintext cannot be recovered to reflash with.
    """
    repo = DeviceRepository(db)
    device = await repo.get_by_incubator(incubator_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inkubator ini belum memiliki device",
        )

    if data.label is not None:
        device.label = data.label or None
    if data.allowed_ip is not None:
        allowed = data.allowed_ip.strip()
        if allowed:
            try:
                ipaddress.ip_network(allowed, strict=False)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"'{allowed}' bukan alamat IP atau CIDR yang valid",
                )
        device.allowed_ip = allowed or None

    await db.flush()
    await log_action(
        db, user_id=actor_id, action="UPDATE", table_name="devices",
        record_id=device.device_id, ip_address=ip,
        details={"allowed_ip": device.allowed_ip, "label": device.label},
    )
    return DeviceResponse.model_validate(device)


async def revoke_device(
    incubator_id: uuid.UUID,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> None:
    """Delete an incubator's device. Its readings survive (device_id → NULL)."""
    repo = DeviceRepository(db)
    device = await repo.get_by_incubator(incubator_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inkubator ini belum memiliki device",
        )

    device_id = device.device_id
    await repo.delete(device)

    await log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        table_name="devices",
        record_id=device_id,
        ip_address=ip,
    )
