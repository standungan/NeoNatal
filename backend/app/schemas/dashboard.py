import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total: int
    terisi: int
    kosong: int
    warning: int
    tidak_tersedia: int


class BabySummary(BaseModel):
    baby_id: uuid.UUID
    baby_name: str
    age_in_days: int
    birth_weight: Decimal | None
    assigned_at: datetime


class LatestVitals(BaseModel):
    suhu_bayi: Decimal | None
    heart_rate: int | None
    spo2: Decimal | None
    observation_time: datetime
    vital_status: str   # "normal" | "warning"


class IncubatorDashboardItem(BaseModel):
    incubator_id: uuid.UUID
    incubator_no: str
    location: str | None
    status: str
    current_baby: BabySummary | None = None
    latest_vitals: LatestVitals | None = None

    # IoT sensor unit bound to this incubator. Two fields rather than one
    # nullable timestamp, because "no device installed" and "device installed
    # but never reported" are different problems: the first needs provisioning,
    # the second needs someone to go and look at the rig.
    has_device: bool = False
    device_last_seen_at: datetime | None = None
    # Recent skin-temperature samples, oldest first, for the card's sparkline.
    # Nulls are kept in place so the trace breaks where the sensor said nothing —
    # dropping them would draw a continuous line through a gap.
    sparkline: list[float | None] = []


class DashboardResponse(BaseModel):
    stats: DashboardStats
    incubators: list[IncubatorDashboardItem]
