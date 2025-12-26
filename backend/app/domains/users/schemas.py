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


# Tenant schemas
class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantMembershipResponse(BaseModel):
    tenant: TenantResponse
    roles: list[str]
    is_default: bool

    class Config:
        from_attributes = True


class UserWithTenantsResponse(UserResponse):
    tenants: list[TenantMembershipResponse] = []


class TenantInvitationCreate(BaseModel):
    email: EmailStr
    roles: list[str]


class TenantInvitationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    roles: list[str]
    invited_by_user_id: UUID
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
