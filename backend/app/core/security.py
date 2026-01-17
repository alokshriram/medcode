from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

security = HTTPBearer()


class TenantInfo:
    """Basic tenant information included in JWT."""
    def __init__(self, id: str, name: str, slug: str):
        self.id = id
        self.name = name
        self.slug = slug


class TokenPayload:
    def __init__(
        self,
        sub: str,
        exp: datetime,
        email: str | None = None,
        roles: list[str] | None = None,
        tenant_id: str | None = None,
        tenant_roles: list[str] | None = None,
        available_tenants: list[dict[str, str]] | None = None,
        impersonating: str | None = None,
    ):
        self.sub = sub
        self.exp = exp
        self.email = email
        self.roles = roles or []  # Legacy user-level roles (deprecated)
        self.tenant_id = tenant_id
        self.tenant_roles = tenant_roles or []  # Roles within current tenant
        self.available_tenants = available_tenants or []
        self.impersonating = impersonating  # Original user ID if impersonating


def create_access_token(
    subject: str,
    email: str,
    roles: list[str],
    expires_delta: timedelta | None = None,
    tenant_id: str | None = None,
    tenant_roles: list[str] | None = None,
    available_tenants: list[dict[str, Any]] | None = None,
    impersonating: str | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "email": email,
        "roles": roles,  # Legacy field for backward compatibility
        "exp": expire,
    }

    # Add tenant context if provided
    if tenant_id:
        to_encode["tenant_id"] = tenant_id
    if tenant_roles:
        to_encode["tenant_roles"] = tenant_roles
    if available_tenants:
        to_encode["available_tenants"] = available_tenants
    if impersonating:
        to_encode["impersonating"] = impersonating

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenPayload:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_data = TokenPayload(
            sub=payload.get("sub"),
            exp=payload.get("exp"),
            email=payload.get("email"),
            roles=payload.get("roles", []),
            tenant_id=payload.get("tenant_id"),
            tenant_roles=payload.get("tenant_roles", []),
            available_tenants=payload.get("available_tenants", []),
            impersonating=payload.get("impersonating"),
        )
        return token_data
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_roles: list[str]):
    """Check if user has any of the required roles.

    First checks tenant_roles (preferred), then falls back to legacy roles field.
    """
    def role_checker(token: TokenPayload = Depends(verify_token)) -> TokenPayload:
        # Prefer tenant_roles if available
        effective_roles = token.tenant_roles if token.tenant_roles else token.roles

        for role in required_roles:
            if role in effective_roles:
                return token
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return role_checker


def require_super_user():
    """Require the current user to be the configured super user."""
    def super_user_checker(token: TokenPayload = Depends(verify_token)) -> TokenPayload:
        if not settings.SUPER_USER_EMAIL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super user not configured",
            )
        if token.email and token.email.lower() == settings.SUPER_USER_EMAIL.lower():
            return token
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super user access required",
        )
    return super_user_checker
