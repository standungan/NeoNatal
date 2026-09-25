import uuid

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyRole, PerawatOrAdmin
from app.core.database import get_db
from app.schemas.monitoring import MonitoringCreate, MonitoringResponse, PhotoUploadResponse
from app.services import monitoring_service

router = APIRouter()


@router.post(
    "/babies/{baby_id}/monitoring",
    response_model=MonitoringResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitoring(
    baby_id: uuid.UUID,
    data: MonitoringCreate,
    request: Request,
    current_user: PerawatOrAdmin,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await monitoring_service.create_monitoring(
        baby_id, data, db, actor_id=current_user.id, ip=ip
    )


@router.get("/babies/{baby_id}/monitoring", response_model=list[MonitoringResponse])
async def list_monitoring(
    baby_id: uuid.UUID,
    current_user: AnyRole,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await monitoring_service.list_monitoring(baby_id, db, skip=skip, limit=limit)


@router.post(
    "/monitoring/{monitoring_id}/photo",
    response_model=PhotoUploadResponse,
)
async def upload_photo(
    monitoring_id: uuid.UUID,
    request: Request,
    current_user: PerawatOrAdmin,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await monitoring_service.upload_photo(
        monitoring_id, file, db, actor_id=current_user.id, ip=ip
    )


@router.get(
    "/monitoring/{monitoring_id}/photo",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}, "description": "The photo itself"}},
)
async def get_photo(
    monitoring_id: uuid.UUID,
    current_user: AnyRole,
    thumb: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """The photo attached to this monitoring record.

    A patient photo is a clinical read like any other, so it is served here —
    behind the same session check — rather than from an open static directory.
    `thumb=true` returns a small JPEG for lists; the default is the file as
    uploaded. 404 when the record has no photo, or its file is missing.
    """
    data, media_type = await monitoring_service.get_photo(monitoring_id, db, thumb=thumb)
    # private: it is a patient photo, so no shared cache may keep a copy.
    return Response(content=data, media_type=media_type,
                    headers={"Cache-Control": "private, max-age=3600"})
