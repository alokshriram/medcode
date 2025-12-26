from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenPayload, verify_token
from app.core.tenant import (
    TenantContext,
    get_tenant_context,
    OptionalTenantContext,
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[TokenPayload, Depends(verify_token)]

# Tenant context dependencies
TenantContextDep = Annotated[TenantContext, Depends(get_tenant_context)]
OptionalTenantContextDep = Annotated[TenantContext | None, Depends(OptionalTenantContext.get)]
