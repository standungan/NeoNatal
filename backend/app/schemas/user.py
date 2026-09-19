import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


UserRole = Literal["admin", "perawat", "dokter"]


class UserCreate(BaseModel):
    role: UserRole
    email: EmailStr
    password: str
    full_name: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None


class PasswordResetRequest(BaseModel):
    new_password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    role: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    # Filled only by the admin list (GET /users): true when the account has never
    # recorded or changed anything, so DELETE /users/{id}/permanent will succeed.
    # Clients show the delete button only then - a button that can only fail is a
    # dead end, not a safeguard. Null everywhere else.
    deletable: bool | None = None

    model_config = {"from_attributes": True}


class UserOption(BaseModel):
    """Minimal user info for dropdowns (e.g. DPJP picker on registration)."""
    id: uuid.UUID
    full_name: str

    model_config = {"from_attributes": True}
