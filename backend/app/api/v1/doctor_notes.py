import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyRole, DokterOnly
from app.core.database import get_db
from app.schemas.doctor_note import DoctorNoteCreate, DoctorNoteResponse
from app.services import doctor_note_service

router = APIRouter()


@router.post(
    "/babies/{baby_id}/doctor-notes",
    response_model=DoctorNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_doctor_note(
    baby_id: uuid.UUID,
    data: DoctorNoteCreate,
    request: Request,
    current_user: DokterOnly,
    db: AsyncSession = Depends(get_db),
):
    """Add a doctor's observation note (dokter only)."""
    ip = request.client.host if request.client else None
    return await doctor_note_service.create_note(
        baby_id, data, db, actor_id=current_user.id, ip=ip
    )


@router.get("/babies/{baby_id}/doctor-notes", response_model=list[DoctorNoteResponse])
async def list_doctor_notes(
    baby_id: uuid.UUID,
    current_user: AnyRole,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await doctor_note_service.list_notes(baby_id, db, skip=skip, limit=limit)
