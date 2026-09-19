import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SensorAlert(Base):
    """A threshold breach raised by the ingest path (updates03 P4).

    One row per episode, not per breaching reading: a partial unique index on
    (incubator_id, alert_type) WHERE resolved_at IS NULL means a breach lasting a
    minute refreshes one row instead of opening twenty. Recovery sets
    `resolved_at`, which frees the slot for the next episode.
    """

    __tablename__ = "sensor_alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incubator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incubators.incubator_id", ondelete="CASCADE"),
        nullable=False,
    )
    # Which baby was in the incubator when this fired. Denormalised on purpose:
    # the assignment can change later, and an alert must stay attributable to
    # whoever was actually in the box at the time.
    baby_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("babies.baby_id", ondelete="SET NULL")
    )
    alert_type: Mapped[str] = mapped_column(
        Enum(
            "desaturation",
            "bradycardia",
            "tachycardia",
            "temp_out_of_range",
            name="sensor_alert_type",
            create_type=False,
        ),
        nullable=False,
    )
    metric_key: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(
        Enum("warning", "critical", name="sensor_alert_severity", create_type=False),
        nullable=False,
        default="warning",
    )
    # Captured at open time so the alert reads correctly even after an admin
    # edits the incubator's thresholds.
    value: Mapped[float | None] = mapped_column(Numeric(6, 2))
    threshold: Mapped[float | None] = mapped_column(Numeric(6, 2))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Who closed it. NULL = readings came back in range (the engine); 'discharged' =
    # the baby went home; 'archived' = the incubator was retired. Kept so the history
    # never reads as a recovery that did not happen.
    resolved_reason: Mapped[str | None] = mapped_column(String(20))
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
