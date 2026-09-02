import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, SmallInteger, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SensorReading(Base):
    """One telemetry sample from an incubator's IoT device.

    Deliberately separate from `monitoring_records`: that table is clinical and
    attested (`recorded_by` is a non-nullable user FK), whereas this one is
    high-frequency machine output with no human in the loop. Column types mirror
    `monitoring_records` exactly so the vitals-form auto-fill is a straight copy.

    Metrics are all nullable — a null means "the sensor had nothing to report"
    (probe off the baby, DHT22 read failure), which is information. A reading with
    every metric null is never stored; see telemetry_service.ingest.
    """

    __tablename__ = "sensor_readings"

    reading_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incubator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incubators.incubator_id", ondelete="CASCADE"),
        nullable=False,
    )
    # Denormalized from the ACTIVE assignment at ingest time — the device never
    # sends this. Null when the incubator is empty (telemetry from an idle unit).
    baby_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("babies.baby_id", ondelete="SET NULL"), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True
    )
    # Server-assigned: the ESP8266 has no RTC and runs no NTP, so a device-supplied
    # timestamp would be meaningless.
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    suhu_bayi: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))              # °C, DS18B20
    suhu_inkubator: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))         # °C, DHT22
    kelembapan_inkubator: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))   # % RH, DHT22
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger)                  # bpm, MAX30102
    spo2: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))                   # %, MAX30102
    # No sensor produces this yet — column exists for parity with monitoring_records.
    respiratory_rate: Mapped[int | None] = mapped_column(SmallInteger)

    source: Mapped[str] = mapped_column(
        Enum("sensor", "simulator", name="sensor_source"), nullable=False, default="sensor"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def metric_value(self, key: str) -> float | None:
        """Value for a metric key, or None if this sample has no reading for it.

        Lets the alert engine iterate metrics generically instead of branching
        per column — and keeps "no reading" as None rather than coercing to 0.
        """
        v = {
            "suhu_bayi": self.suhu_bayi,
            "suhu_inkubator": self.suhu_inkubator,
            "kelembapan_inkubator": self.kelembapan_inkubator,
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "respiratory_rate": self.respiratory_rate,
        }.get(key)
        return None if v is None else float(v)
