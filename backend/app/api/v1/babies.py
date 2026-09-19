import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnyRole, PerawatOrAdmin
from app.core.database import get_db
from app.schemas.baby import BabyCreate, BabyDetailResponse, BabyListItem, BabyUpdate
from app.services import baby_service

router = APIRouter()


@router.get("", response_model=list[BabyListItem])
async def list_babies(
    current_user: AnyRole,
    status_filter: Literal["aktif", "pulang", "semua"] = Query("aktif", alias="status"),
    q: str | None = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Babies with their most recent placement, newest first.

    `status` defaults to "aktif" (still in an incubator) — what this endpoint has
    always returned. "pulang" lists discharged babies and "semua" both, so records
    stay reachable after the incubator is reused or archived. `q` matches name,
    No. RM, or NICU registration number.
    """
    return await baby_service.get_all_babies(db, status=status_filter, q=q, limit=limit)


@router.post("", response_model=BabyDetailResponse, status_code=status.HTTP_201_CREATED)
async def register_baby(
    data: BabyCreate,
    request: Request,
    current_user: PerawatOrAdmin,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await baby_service.register_baby(data, db, actor_id=current_user.id, ip=ip)


@router.get("/{baby_id}", response_model=BabyDetailResponse)
async def get_baby(
    baby_id: uuid.UUID,
    current_user: AnyRole,
    db: AsyncSession = Depends(get_db),
):
    return await baby_service.get_baby(baby_id, db)


@router.put("/{baby_id}", response_model=BabyDetailResponse)
async def update_baby(
    baby_id: uuid.UUID,
    data: BabyUpdate,
    request: Request,
    current_user: PerawatOrAdmin,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    return await baby_service.update_baby(baby_id, data, db, actor_id=current_user.id, ip=ip)


@router.post("/{baby_id}/discharge", status_code=status.HTTP_204_NO_CONTENT)
async def discharge_baby(
    baby_id: uuid.UUID,
    request: Request,
    current_user: PerawatOrAdmin,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    await baby_service.discharge_baby(baby_id, db, actor_id=current_user.id, ip=ip)
