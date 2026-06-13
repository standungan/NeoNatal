import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ParentInvolvementRecord(Base):
    __tablename__ = "parent_involvement_records"

    involvement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    baby_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("babies.baby_id"), nullable=False
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    observation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    durasi_menyusui: Mapped[int | None] = mapped_column(SmallInteger)    # minutes
    durasi_interaksi: Mapped[int | None] = mapped_column(SmallInteger)   # minutes
    catatan: Mapped[str | None] = mapped_column(Text)
    skor_keterlibatan: Mapped[int | None] = mapped_column(SmallInteger)  # 0–100, computed in service
    kondisi_bayi: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("skor_keterlibatan BETWEEN 0 AND 100", name="ck_skor_keterlibatan"),
    )

    # relationships
    baby: Mapped["Baby"] = relationship(back_populates="involvement_records")
    recorder: Mapped["User"] = relationship(back_populates="involvement_records")
