import uuid
from datetime import datetime

from pydantic import BaseModel


class DoctorNoteCreate(BaseModel):
    observation_time: datetime
    catatan: str


class DoctorNoteResponse(BaseModel):
    note_id: uuid.UUID
    baby_id: uuid.UUID
    recorded_by: uuid.UUID
    recorder_name: str | None = None
    observation_time: datetime
    catatan: str
    created_at: datetime
