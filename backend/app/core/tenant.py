from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenPayload, verify_token


class TenantContext:
    """Request-scoped tenant context extracted from JWT.

    Provides tenant isolation for all data operations.
    """

    def __init__(
        self,
        tenant_id: UUID,
        tenant_roles: list[str],
        user_id: UUID,
        user_email: str | None = None,
        impersonating: UUID | None = None,
    ):
        self.tenant_id = tenant_id
        self.tenant_roles = tenant_roles
        self.user_id = user_id
        self.user_email = user_email
        self.impersonating = impersonating

    def has_role(self, role: str) -> bool:
        """Check if the current user has a specific role in this tenant."""
        return role in self.tenant_roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if the current user has any of the specified roles."""
        return any(role in self.tenant_roles for role in roles)


def get_tenant_context(token: TokenPayload = Depends(verify_token)) -> TenantContext:
    """FastAPI dependency to get tenant context from JWT.

    Requires the token to have tenant_id. For backward compatibility,
    tokens without tenant_id will raise an error prompting re-login.
    """
    if not token.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant context. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TenantContext(
        tenant_id=UUID(token.tenant_id),
        tenant_roles=token.tenant_roles,
        user_id=UUID(token.sub),
        user_email=token.email,
        impersonating=UUID(token.impersonating) if token.impersonating else None,
    )


# Type alias for use in FastAPI route handlers
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]


# Generic type for model classes
T = TypeVar("T")


class TenantScopedService:
    """Base class for services that operate within tenant context.

    Provides automatic tenant filtering for queries. Services extending
    this class should use scoped_query() instead of db.query() to ensure
    tenant isolation.
    """

    def __init__(self, db: Session, tenant_context: TenantContext):
        self.db = db
        self.tenant_context = tenant_context

    @property
    def tenant_id(self) -> UUID:
        """Convenience property to access current tenant ID."""
        return self.tenant_context.tenant_id

    @property
    def user_id(self) -> UUID:
        """Convenience property to access current user ID."""
        return self.tenant_context.user_id

    def scoped_query(self, model: type[T]):
        """Return a query filtered by current tenant.

        Usage:
            query = self.scoped_query(Encounter)
            # Automatically adds: WHERE tenant_id = current_tenant_id
        """
        return self.db.query(model).filter(model.tenant_id == self.tenant_id)

    def set_tenant_id(self, obj) -> None:
        """Set the tenant_id on an object before saving.

        Usage:
            patient = Patient(mrn="123", ...)
            self.set_tenant_id(patient)
            self.db.add(patient)
        """
        obj.tenant_id = self.tenant_id


class OptionalTenantContext:
    """For endpoints that may or may not have tenant context.

    Useful during migration period when some tokens may not have tenant_id.
    """

    @staticmethod
    def get(token: TokenPayload = Depends(verify_token)) -> TenantContext | None:
        """Get tenant context if available, otherwise return None."""
        if not token.tenant_id:
            return None

        return TenantContext(
            tenant_id=UUID(token.tenant_id),
            tenant_roles=token.tenant_roles,
            user_id=UUID(token.sub),
            user_email=token.email,
            impersonating=UUID(token.impersonating) if token.impersonating else None,
        )


# Optional tenant context dependency
OptionalTenantContextDep = Annotated[TenantContext | None, Depends(OptionalTenantContext.get)]
