import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ParentInvolvementRecord(Base):
    """One Keterlibatan Orang Tua session — Pillar 6 "Kerjasama dengan Keluarga"
    (6 items scored 0–3, stored as JSONB). Replaces the FICare 8-domain model."""

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
    # { item_code: score(0-3) }
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    catatan: Mapped[str | None] = mapped_column(Text)
    # optional contextual fields (not part of the pillar scoring)
    durasi_menyusui: Mapped[int | None] = mapped_column(SmallInteger)    # minutes
    durasi_interaksi: Mapped[int | None] = mapped_column(SmallInteger)   # minutes
    kondisi_bayi: Mapped[str | None] = mapped_column(String(255))
    # computed at write time (also recomputed on read from the catalog)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)   # 0–18
    percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    category: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    baby: Mapped["Baby"] = relationship(back_populates="involvement_records")
    recorder: Mapped["User"] = relationship(back_populates="involvement_records")
