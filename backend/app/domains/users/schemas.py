from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    google_id: str | None = None
    picture_url: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    picture_url: str | None = None
    roles: list[str] | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    id: UUID
    picture_url: str | None
    roles: list[str]
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    credential: str
