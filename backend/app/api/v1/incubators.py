import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminOnly, AnyRole
from app.core.database import get_db
from app.schemas.incubator import (
    IncubatorCreate,
    IncubatorDetailResponse,
    IncubatorResponse,
    IncubatorThresholdsResponse,
    IncubatorThresholdsUpdate,
    IncubatorUpdate,
)
from app.services import incubator_service

router = APIRouter()


@router.get("", response_model=list[IncubatorDetailResponse])
async def list_incubators(
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    return await incubator_service.get_all_incubators(db)


@router.get("/available", response_model=list[IncubatorResponse])
async def list_available_incubators(
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    """Returns only 'kosong' incubators — used when assigning a baby."""
    return await incubator_service.get_available_incubators(db)


@router.get("/{incubator_id}", response_model=IncubatorDetailResponse)
async def get_incubator(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    return await incubator_service.get_incubator(incubator_id, db)


@router.post("", response_model=IncubatorResponse, status_code=status.HTTP_201_CREATED)
async def create_incubator(
    data: IncubatorCreate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await incubator_service.create_incubator(data, db, actor_id=current_user.id, ip=ip)


@router.put("/{incubator_id}", response_model=IncubatorResponse)
async def update_incubator(
    incubator_id: uuid.UUID,
    data: IncubatorUpdate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await incubator_service.update_incubator(
        incubator_id, data, db, actor_id=current_user.id, ip=ip
    )


@router.delete("/{incubator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incubator(
    incubator_id: uuid.UUID,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Delete an empty/unavailable incubator (admin only)."""
    ip = request.client.host if request.client else None
    await incubator_service.delete_incubator(
        incubator_id, db, actor_id=current_user.id, ip=ip
    )


@router.get("/{incubator_id}/thresholds", response_model=IncubatorThresholdsResponse)
async def get_incubator_thresholds(
    incubator_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    """Effective sensor alert thresholds (stored overrides merged with defaults)."""
    return await incubator_service.get_thresholds(incubator_id, db)


@router.put("/{incubator_id}/thresholds", response_model=IncubatorThresholdsResponse)
async def update_incubator_thresholds(
    incubator_id: uuid.UUID,
    data: IncubatorThresholdsUpdate,
    request: Request,
    current_user: AdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Set per-incubator sensor alert thresholds (admin only)."""
    ip = request.client.host if request.client else None
    return await incubator_service.update_thresholds(
        incubator_id, data, db, actor_id=current_user.id, ip=ip
    )
