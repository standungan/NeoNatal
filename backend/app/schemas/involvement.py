import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class InvolvementCreate(BaseModel):
    observation_time: datetime
    durasi_menyusui: int | None = None    # minutes
    durasi_interaksi: int | None = None   # minutes
    catatan: str | None = None
    kondisi_bayi: str | None = None

    @field_validator("durasi_menyusui", "durasi_interaksi")
    @classmethod
    def non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Durasi tidak boleh negatif")
        return v


class InvolvementResponse(BaseModel):
    involvement_id: uuid.UUID
    baby_id: uuid.UUID
    recorded_by: uuid.UUID
    recorder_name: str | None = None
    observation_time: datetime
    durasi_menyusui: int | None
    durasi_interaksi: int | None
    catatan: str | None
    skor_keterlibatan: int | None
    skor_kategori: str | None = None     # Rendah / Sedang / Baik / Sangat Baik
    kondisi_bayi: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvolvementSummary(BaseModel):
    total_sessions: int
    avg_skor: float | None
    avg_durasi_menyusui: float | None
    avg_durasi_interaksi: float | None
    latest_skor: int | None
    latest_kategori: str | None
