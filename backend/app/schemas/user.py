import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None
    storage_limit_bytes: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    role: UserRole
    is_active: bool
    storage_limit_bytes: int | None
    created_at: datetime
    last_login_at: datetime | None
