import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


IncubatorStatus = Literal["kosong", "terisi", "warning", "tidak_tersedia"]


class IncubatorCreate(BaseModel):
    # incubator_no is assigned automatically (next sequential number) — see
    # incubator_service.create_incubator. Only the location is user-provided.
    location: str | None = None


class IncubatorUpdate(BaseModel):
    location: str | None = None
    status: IncubatorStatus | None = None


class CurrentBabySummary(BaseModel):
    baby_id: uuid.UUID
    baby_name: str
    birth_date: datetime | None = None
    assigned_at: datetime


class IncubatorResponse(BaseModel):
    incubator_id: uuid.UUID
    incubator_no: str
    location: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncubatorDetailResponse(IncubatorResponse):
    current_baby: CurrentBabySummary | None = None


# ── Sensor alert thresholds (per-incubator, admin-set) ──────────────────────────
# Metric catalog + default bounds (from the IoT design). These are the sensor
# vitals that map to monitoring_records; the alert engine (future IoT feature)
# reads them per incubator.
THRESHOLD_METRICS: list[dict] = [
    {"key": "suhu_bayi",            "label": "Suhu Bayi (kulit)",      "unit": "°C",    "min": 36.0,  "max": 37.5},
    {"key": "suhu_inkubator",       "label": "Suhu Inkubator (udara)", "unit": "°C",    "min": 34.0,  "max": 36.0},
    {"key": "kelembapan_inkubator", "label": "Kelembapan",             "unit": "%",     "min": 60.0,  "max": 80.0},
    {"key": "spo2",                 "label": "SpO₂",                   "unit": "%",     "min": 90.0,  "max": 100.0},
    {"key": "heart_rate",           "label": "Detak Jantung",          "unit": "bpm",   "min": 100.0, "max": 180.0},
    {"key": "respiratory_rate",     "label": "Laju Napas",             "unit": "x/mnt", "min": 30.0,  "max": 60.0},
]

DEFAULT_THRESHOLDS: dict[str, dict] = {
    m["key"]: {"min": m["min"], "max": m["max"]} for m in THRESHOLD_METRICS
}


class ThresholdBound(BaseModel):
    min: float | None = None
    max: float | None = None


class ThresholdMetric(BaseModel):
    key: str
    label: str
    unit: str
    min: float | None
    max: float | None


class IncubatorThresholdsResponse(BaseModel):
    incubator_id: uuid.UUID
    incubator_no: str
    is_custom: bool                 # False → using code defaults
    metrics: list[ThresholdMetric]  # effective values + labels/units for the form


class IncubatorThresholdsUpdate(BaseModel):
    thresholds: dict[str, ThresholdBound]   # { metric_key: {min, max} }
