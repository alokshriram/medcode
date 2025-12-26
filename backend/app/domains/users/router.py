import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.security import create_access_token, require_super_user, TokenPayload
from app.domains.users.schemas import (
    GoogleAuthRequest,
    TenantCreate,
    TenantInvitationCreate,
    TenantInvitationResponse,
    TenantMembershipResponse,
    TenantResponse,
    TokenResponse,
    UserResponse,
    UserUpdate,
    UserWithTenantsResponse,
)
from app.domains.users.service import UsersService
from app.domains.users.tenant_service import TenantService

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_tenant_token(user, tenant_membership, all_memberships, impersonating: str | None = None) -> str:
    """Build a JWT with tenant context."""
    available_tenants = [
        {"id": str(m.tenant.id), "name": m.tenant.name, "slug": m.tenant.slug}
        for m in all_memberships
    ]

    return create_access_token(
        subject=str(user.id),
        email=user.email,
        roles=user.roles,  # Legacy field
        tenant_id=str(tenant_membership.tenant.id),
        tenant_roles=tenant_membership.roles,
        available_tenants=available_tenants,
        impersonating=impersonating,
    )


@router.post("/auth/google", response_model=TokenResponse)
def google_auth(auth_request: GoogleAuthRequest, db: DbSession):
    logger.info("=== Google Auth Request Started ===")
    logger.info(f"Credential length: {len(auth_request.credential) if auth_request.credential else 0}")
    logger.info(f"Using GOOGLE_CLIENT_ID: {settings.GOOGLE_CLIENT_ID[:20]}...")

    try:
        logger.info("Step 1: Verifying OAuth2 token with Google...")
        idinfo = id_token.verify_oauth2_token(
            auth_request.credential,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        logger.info("Step 1: Token verified successfully")

        google_id = idinfo["sub"]
        email = idinfo["email"]
        full_name = idinfo.get("name", email.split("@")[0])
        picture_url = idinfo.get("picture")

        logger.info(f"Step 2: Extracted user info - email: {email}, google_id: {google_id[:10]}...")

        users_service = UsersService(db)
        tenant_service = TenantService(db)

        logger.info("Step 3: Getting or creating user in database...")
        user = users_service.get_or_create_google_user(
            google_id=google_id,
            email=email,
            full_name=full_name,
            picture_url=picture_url,
        )
        logger.info(f"Step 3: User retrieved/created - id: {user.id}, email: {user.email}")

        # Step 4: Auto-accept any pending invitations
        logger.info("Step 4: Checking for pending invitations...")
        accepted = tenant_service.auto_accept_pending_invitations(user)
        if accepted:
            logger.info(f"Step 4: Auto-accepted {len(accepted)} invitation(s)")
        else:
            logger.info("Step 4: No pending invitations")

        # Step 5: Ensure user has a default tenant (lazy migration)
        logger.info("Step 5: Ensuring user has a default tenant...")
        default_tenant = tenant_service.ensure_default_tenant(user)
        logger.info(f"Step 5: Default tenant: {default_tenant.name} ({default_tenant.id})")

        # Get the default membership for tenant roles
        default_membership = tenant_service.get_user_default_tenant(user.id)
        all_memberships = tenant_service.get_user_tenants(user.id)

        logger.info("Step 6: Creating JWT access token with tenant context...")
        access_token = _build_tenant_token(user, default_membership, all_memberships)
        logger.info("Step 6: JWT token created successfully")

        logger.info("=== Google Auth Request Completed Successfully ===")
        return TokenResponse(access_token=access_token)

    except ValueError as e:
        logger.error(f"=== Google Auth FAILED ===")
        logger.error(f"ValueError during token verification: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}",
        )
    except Exception as e:
        logger.error(f"=== Google Auth FAILED (Unexpected) ===")
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}",
        )


@router.post("/auth/switch-tenant/{tenant_id}", response_model=TokenResponse)
def switch_tenant(tenant_id: UUID, db: DbSession, current_user: CurrentUser):
    """Switch to a different tenant and get a new JWT."""
    users_service = UsersService(db)
    tenant_service = TenantService(db)

    user = users_service.get_user(UUID(current_user.sub))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify user has access to this tenant
    membership = tenant_service.get_membership(user.id, tenant_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tenant",
        )

    all_memberships = tenant_service.get_user_tenants(user.id)

    # Preserve impersonation state if present
    impersonating = current_user.impersonating

    access_token = _build_tenant_token(user, membership, all_memberships, impersonating)
    return TokenResponse(access_token=access_token)


class ImpersonateRequest(BaseModel):
    email: EmailStr


@router.post("/auth/impersonate", response_model=TokenResponse)
def impersonate_user(
    request: ImpersonateRequest,
    db: DbSession,
    _: TokenPayload = Depends(require_super_user()),
    current_user: CurrentUser = None,
):
    """Impersonate another user (super user only)."""
    users_service = UsersService(db)
    tenant_service = TenantService(db)

    # Find target user
    target_user = users_service.get_user_by_email(request.email)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Ensure target user has a tenant
    default_tenant = tenant_service.ensure_default_tenant(target_user)
    default_membership = tenant_service.get_user_default_tenant(target_user.id)
    all_memberships = tenant_service.get_user_tenants(target_user.id)

    # Get original user ID (either current impersonator or current user)
    original_user_id = current_user.impersonating or current_user.sub

    logger.info(f"Super user {current_user.email} impersonating {target_user.email}")

    access_token = _build_tenant_token(
        target_user,
        default_membership,
        all_memberships,
        impersonating=original_user_id,
    )
    return TokenResponse(access_token=access_token)


@router.post("/auth/stop-impersonation", response_model=TokenResponse)
def stop_impersonation(db: DbSession, current_user: CurrentUser):
    """Stop impersonating and return to original user."""
    if not current_user.impersonating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not currently impersonating anyone",
        )

    users_service = UsersService(db)
    tenant_service = TenantService(db)

    # Get original user
    original_user = users_service.get_user(UUID(current_user.impersonating))
    if not original_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original user not found")

    default_membership = tenant_service.get_user_default_tenant(original_user.id)
    all_memberships = tenant_service.get_user_tenants(original_user.id)

    logger.info(f"Stopping impersonation, returning to {original_user.email}")

    access_token = _build_tenant_token(original_user, default_membership, all_memberships)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_current_user(db: DbSession, current_user: CurrentUser):
    service = UsersService(db)
    user = service.get_user(UUID(current_user.sub))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(db: DbSession, current_user: CurrentUser, skip: int = 0, limit: int = 100):
    service = UsersService(db)
    return service.get_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: DbSession, current_user: CurrentUser):
    service = UsersService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, user: UserUpdate, db: DbSession, current_user: CurrentUser):
    service = UsersService(db)
    updated_user = service.update_user(user_id, user)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user
