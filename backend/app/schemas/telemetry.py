import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer, field_validator

# Metric fields carried by a telemetry payload. Used to detect an all-null
# reading (device alive, sensors reporting nothing) — see telemetry_service.
METRIC_FIELDS = (
    "suhu_bayi",
    "suhu_inkubator",
    "kelembapan_inkubator",
    "heart_rate",
    "spo2",
)


class TelemetryIn(BaseModel):
    """One sample posted by an incubator's IoT device.

    Keys are the *clinical* field names, not the device's sensor names
    (`ds18b20_temp` → `suhu_bayi`, `dht22_temp` → `suhu_inkubator`,
    `dht22_humidity` → `kelembapan_inkubator`), so there is no mapping layer
    between the wire format and the database.

    `extra="forbid"`: unlike the JSONB prototype this feeds a clinical schema, so
    an unrecognised key is a bug worth surfacing, not something to wave through.
    There is deliberately no `ts` field — the ESP8266 has no RTC, so the server
    timestamps every reading.
    """

    model_config = {"extra": "forbid"}

    suhu_bayi: Decimal | None = Field(default=None, ge=-40, le=125)
    suhu_inkubator: Decimal | None = Field(default=None, ge=-40, le=125)
    kelembapan_inkubator: Decimal | None = Field(default=None, ge=0, le=100)
    heart_rate: int | None = Field(default=None, ge=0, le=300)
    spo2: Decimal | None = Field(default=None, ge=0, le=100)

    @field_validator("heart_rate", "spo2")
    @classmethod
    def zero_means_no_reading(cls, v):
        """The firmware reports 0 for HR/SpO2 when nothing is on the probe.

        Storing that as a real value would draw a cliff to zero on the chart and
        fire a bradycardia/desaturation alert every time the sensor is off the
        baby. 0 is not a survivable vital sign — it means "no reading".

        Firmware is being fixed to send null directly; this stays regardless,
        because a device in the field may not have been reflashed.
        """
        if v is not None and v == 0:
            return None
        return v

    def is_empty(self) -> bool:
        """True when no sensor reported anything — device alive, nothing to store."""
        return all(getattr(self, f) is None for f in METRIC_FIELDS)


class TelemetryAck(BaseModel):
    """Deliberately tiny — the firmware only logs the status code."""

    ok: bool = True
    stored: bool
    reading_id: uuid.UUID | None = None


class DeviceCreate(BaseModel):
    label: str | None = None


class DeviceResponse(BaseModel):
    device_id: uuid.UUID
    incubator_id: uuid.UUID | None
    label: str | None
    firmware_version: str | None
    last_seen_at: datetime | None
    # Provenance only. Shown so an admin can match a row to a physical box; a
    # DHCP change moves it and nothing breaks.
    last_ip: str | None = None
    # Optional coarse filter on the unauthenticated legacy route. NULL = accept any.
    allowed_ip: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceProvisionResponse(DeviceResponse):
    """Returned only by POST /incubators/{id}/device.

    `device_key` is the one and only time the plaintext exists outside the
    firmware — the database holds nothing but its SHA-256. Losing it means
    re-provisioning, which is the intended trade.
    """

    device_key: str


class SensorReadingResponse(BaseModel):
    """One stored sample, as served to the chart.

    Every metric is nullable and a null is meaningful: it means the sensor had
    nothing to report (probe off the baby, DHT22 read failure), not zero. The
    chart must break the line rather than draw down to the axis.
    """

    reading_id: uuid.UUID
    incubator_id: uuid.UUID
    baby_id: uuid.UUID | None
    recorded_at: datetime
    suhu_bayi: Decimal | None
    suhu_inkubator: Decimal | None
    kelembapan_inkubator: Decimal | None
    heart_rate: int | None
    spo2: Decimal | None
    respiratory_rate: int | None
    source: str

    model_config = {"from_attributes": True}

    @field_serializer(
        "suhu_bayi", "suhu_inkubator", "kelembapan_inkubator", "spo2"
    )
    def _decimal_as_number(self, v: Decimal | None) -> float | None:
        """Emit JSON numbers, not strings.

        Pydantic serialises Decimal as a string to protect precision. That is
        right for money and wrong for a chart: the client would receive
        "52.00" and have to coerce it before any axis-domain or threshold
        comparison, and a missed coercion fails silently by sorting
        lexicographically. Decimal stays the storage type; only the wire
        format changes.
        """
        return float(v) if v is not None else None


# ── Legacy prototype payload (POST /api/sensors) ────────────────────────────────


class LegacySensors(BaseModel):
    """The prototype firmware's raw sensor block, keyed by hardware name."""

    model_config = {"extra": "ignore"}

    ds18b20_temp: Decimal | None = Field(default=None, ge=-40, le=125)
    dht22_temp: Decimal | None = Field(default=None, ge=-40, le=125)
    dht22_humidity: Decimal | None = Field(default=None, ge=0, le=100)
    heart_rate: int | None = Field(default=None, ge=0, le=300)
    spo2: Decimal | None = Field(default=None, ge=0, le=100)


class LegacyTelemetryIn(BaseModel):
    """What the bench rig's prototype firmware posts.

    Kept apart from TelemetryIn rather than widened into it, so the sensor->
    clinical rename lives at this boundary only and never leaks into the
    authenticated path.

    `baby_id` is accepted and deliberately IGNORED: which baby occupies an
    incubator is a runtime assignment that changes on admission and discharge,
    and the firmware's value is a hardcoded label set at flash time.
    """

    model_config = {"extra": "ignore"}

    incubator_id: str
    baby_id: str | None = None
    sensors: LegacySensors

    def to_telemetry(self) -> "TelemetryIn":
        """Rename hardware keys to clinical ones and reuse the strict schema.

        Routing through TelemetryIn is the point: the 0-means-no-reading rule and
        the physiological range checks then apply identically on both paths.
        """
        s = self.sensors
        return TelemetryIn(
            suhu_bayi=s.ds18b20_temp,
            suhu_inkubator=s.dht22_temp,
            kelembapan_inkubator=s.dht22_humidity,
            heart_rate=s.heart_rate,
            spo2=s.spo2,
        )


class DeviceUpdate(BaseModel):
    """Admin-editable device fields. Everything is optional; omitted stays put."""

    label: str | None = None
    # Single address ("192.168.0.2") or CIDR ("192.168.0.0/24"). Empty string clears it.
    allowed_ip: str | None = None


# ── Alerts (updates03 P4) ───────────────────────────────────────────────────────


class SensorAlertResponse(BaseModel):
    """One alert episode, as shown in the feed.

    `value`/`threshold` are the reading and the bound at the moment it opened —
    stored rather than recomputed, so the entry still reads correctly after an
    admin edits the incubator's thresholds.
    """

    alert_id: uuid.UUID
    incubator_id: uuid.UUID
    baby_id: uuid.UUID | None
    baby_name: str | None = None
    alert_type: str
    metric_key: str
    severity: str
    value: Decimal | None
    threshold: Decimal | None
    started_at: datetime
    resolved_at: datetime | None
    acknowledged_by: uuid.UUID | None
    acknowledged_by_name: str | None = None
    acknowledged_at: datetime | None

    model_config = {"from_attributes": True}

    @field_serializer("value", "threshold")
    def _decimal_as_number(self, v: Decimal | None) -> float | None:
        """Numbers, not strings — same reasoning as SensorReadingResponse."""
        return float(v) if v is not None else None
