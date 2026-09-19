import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Incubator(Base):
    __tablename__ = "incubators"

    incubator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incubator_no: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum("kosong", "terisi", "warning", "tidak_tersedia", name="incubator_status"),
        nullable=False,
        default="kosong",
    )
    # admin-set sensor alert bounds { metric: {min, max} }; NULL → code defaults
    alert_thresholds: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Set when an incubator that has held a baby is retired: the row stays so its
    # placements, readings and alerts stay attached, but the app stops offering it.
    # See incubator_service.archive_incubator.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # relationships
    assignments: Mapped[list["BabyIncubatorAssignment"]] = relationship(back_populates="incubator")
