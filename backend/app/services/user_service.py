import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, union
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 - every table must be in the metadata read below
from app.core.database import Base
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    PasswordResetRequest,
    UserCreate,
    UserOption,
    UserResponse,
    UserUpdate,
)
from app.services.audit_service import log_action


# Audit actions that only record a session, not something the user did. Their
# details already carry the email, so they stay readable once user_id is nulled by
# the ON DELETE SET NULL - and "logged in once" is not a record worth keeping an
# account for.
_SESSION_ACTIONS = ("LOGIN", "LOGOUT")


def _columns_referencing_users():
    """Every column that points at users.id, read from the models rather than listed,
    so a table added later counts without anyone remembering to add it here."""
    return [
        fk.parent
        for table in Base.metadata.sorted_tables
        for fk in table.foreign_keys
        if fk.column.table.name == User.__tablename__
    ]


async def _users_with_records(db: AsyncSession) -> set[uuid.UUID]:
    """Ids of every user referenced anywhere - a clinical record, a placement, an
    acknowledged alert, or an audit entry for anything beyond logging in.

    Seven of these references are ON DELETE NO ACTION, so the database would refuse
    the delete anyway. The other two - audit_logs.user_id and
    sensor_alerts.acknowledged_by - are SET NULL, and would silently erase who did
    it. Those are the ones this check exists for.
    """
    parts = []
    for col in _columns_referencing_users():
        q = select(col.label("uid")).where(col.is_not(None))
        if "action" in col.table.c:
            q = q.where(col.table.c.action.not_in(_SESSION_ACTIONS))
        parts.append(q)
    rows = await db.execute(union(*parts))
    return {r.uid for r in rows}


async def get_all_users(db: AsyncSession) -> list[UserResponse]:
    repo = UserRepository(db)
    users = await repo.get_all()
    return [UserResponse.model_validate(u) for u in users]


async def _get_live(repo: UserRepository, user_id: uuid.UUID) -> User:
    """An account that exists and has not been deleted.

    A deleted account's row is kept only so its records keep their author. To every
    admin action it no longer exists - otherwise a deleted account could be edited,
    given a new password, or reactivated through the API."""
    user = await repo.get_by_id(user_id)
    if not user or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")
    return user


async def get_doctors(db: AsyncSession) -> list[UserOption]:
    """Active doctors — for the DPJP dropdown on baby registration."""
    doctors = await UserRepository(db).get_by_role("dokter", active_only=True)
    return [UserOption.model_validate(u) for u in doctors]


async def get_user(user_id: uuid.UUID, db: AsyncSession) -> UserResponse:
    repo = UserRepository(db)
    user = await _get_live(repo, user_id)
    return UserResponse.model_validate(user)


async def create_user(
    data: UserCreate,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> UserResponse:
    repo = UserRepository(db)

    existing = await repo.get_by_email(data.email)
    if existing:
        # A deleted account keeps its email, so one address always means one person
        # in the audit trail and on every record.
        detail = (
            "Email ini milik akun yang sudah dihapus dan tidak dapat dipakai lagi"
            if existing.deleted_at is not None
            else "Email sudah digunakan"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    user = User(
        role=data.role,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
    )
    user = await repo.create(user)

    await log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        table_name="users",
        record_id=user.id,
        ip_address=ip,
        details={"email": user.email, "role": user.role},
    )
    return UserResponse.model_validate(user)


async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> UserResponse:
    repo = UserRepository(db)
    user = await _get_live(repo, user_id)

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role is not None and data.role != user.role:
        # Guard against an admin locking themselves out of admin access.
        if str(user_id) == str(actor_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak dapat mengubah role akun sendiri",
            )
        user.role = data.role

    user = await repo.update(user)

    await log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        table_name="users",
        record_id=user_id,
        ip_address=ip,
    )
    return UserResponse.model_validate(user)


async def reset_password(
    user_id: uuid.UUID,
    data: PasswordResetRequest,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> None:
    repo = UserRepository(db)
    user = await _get_live(repo, user_id)

    user.password_hash = hash_password(data.new_password)
    await repo.update(user)

    await log_action(
        db,
        user_id=actor_id,
        action="RESET_PASSWORD",
        table_name="users",
        record_id=user_id,
        ip_address=ip,
    )


async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> None:
    repo = UserRepository(db)
    user = await _get_live(repo, user_id)

    if str(user_id) == str(actor_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat menonaktifkan akun sendiri",
        )

    user.is_active = False
    await repo.update(user)

    await log_action(
        db,
        user_id=actor_id,
        action="DEACTIVATE",
        table_name="users",
        record_id=user_id,
        ip_address=ip,
    )


async def delete_user_permanently(
    user_id: uuid.UUID,
    db: AsyncSession,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
) -> None:
    """Delete an account. Nothing it ever recorded is deleted with it.

    An account with no records at all - typically one created by mistake - is removed
    outright. An account with records keeps its row, marked deleted and inactive, so
    that every record, placement and audit entry still names whoever wrote it. To the
    app both are simply gone: off every list, unable to sign in, sessions cut.
    """
    repo = UserRepository(db)
    user = await _get_live(repo, user_id)

    if str(user_id) == str(actor_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat menghapus akun sendiri",
        )

    # Kept in the audit entry: for an account removed outright, this is the only
    # place left that says whose account it was.
    snapshot = {"email": user.email, "full_name": user.full_name, "role": user.role}

    removed = False
    if user_id not in await _users_with_records(db):
        try:
            # A savepoint, so that a record written after the check above only undoes
            # the removal - the account is then kept and marked deleted instead.
            async with db.begin_nested():
                await db.delete(user)
                await db.flush()
            removed = True
        except IntegrityError:
            removed = False

    if not removed:
        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        await repo.update(user)

    await log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        table_name="users",
        record_id=user_id,
        ip_address=ip,
        details={**snapshot, "catatan_dipertahankan": not removed},
    )
