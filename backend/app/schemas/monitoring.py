import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class MonitoringCreate(BaseModel):
    observation_time: datetime
    suhu_bayi: Decimal | None = None
    suhu_inkubator: Decimal | None = None
    heart_rate: int | None = None
    spo2: Decimal | None = None
    expression_score: int | None = None
    movement_score: int | None = None
    catatan: str | None = None

    @field_validator("expression_score", "movement_score")
    @classmethod
    def score_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Score harus antara 1 dan 5")
        return v


class MonitoringResponse(BaseModel):
    monitoring_id: uuid.UUID
    baby_id: uuid.UUID
    recorded_by: uuid.UUID
    recorder_name: str | None = None
    observation_time: datetime
    suhu_bayi: Decimal | None
    suhu_inkubator: Decimal | None
    heart_rate: int | None
    spo2: Decimal | None
    expression_score: int | None
    movement_score: int | None
    catatan: str | None
    foto_url: str | None
    vital_status: str = "normal"  # "normal" | "warning"
    created_at: datetime

    model_config = {"from_attributes": True}


class PhotoUploadResponse(BaseModel):
    monitoring_id: uuid.UUID
    foto_url: str
