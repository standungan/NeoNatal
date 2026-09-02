import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Device(Base):
    """An IoT sensor unit bolted to one incubator (ESP8266 + MAX30102 / DS18B20 / DHT22).

    Authenticates with an opaque device key sent as the `X-Device-Key` header. Only
    the SHA-256 of that key is stored, so a database leak hands out no working
    credentials; the plaintext is shown exactly once, at provisioning.

    The UNIQUE on `incubator_id` is what enforces "one device per incubator" — the
    binding is a database constraint, not a convention.
    """

    __tablename__ = "devices"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable so a device can be provisioned before (or after) it is bound to an
    # incubator; ingest rejects an unbound device with 409.
    incubator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        # SET NULL, not CASCADE: deleting an incubator record must not destroy the
        # physical device's credentials. The unit is still bolted to a real box; it
        # gets a diagnosable 409 and can be rebound with an UPDATE instead of a reflash.
        ForeignKey("incubators.incubator_id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    device_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100))
    firmware_version: Mapped[str | None] = mapped_column(String(20))
    # Touched on every accepted POST — drives the online/offline badge without
    # needing MQTT's Last-Will.
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Provenance, not identity. Recorded on every accepted POST so an admin can
    # match a row to a physical box; a DHCP change moves it harmlessly.
    last_ip: Mapped[str | None] = mapped_column(String(45))
    # Optional coarse filter for the UNAUTHENTICATED legacy route. Accepts a single
    # address or a CIDR. NULL means no filtering.
    allowed_ip: Mapped[str | None] = mapped_column(String(45))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # one-directional (no back_populates → no change to the Incubator model)
    incubator: Mapped["Incubator | None"] = relationship("Incubator")  # noqa: F821
