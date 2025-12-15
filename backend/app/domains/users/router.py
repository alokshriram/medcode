import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.security import create_access_token
from app.domains.users.schemas import GoogleAuthRequest, TokenResponse, UserResponse, UserUpdate
from app.domains.users.service import UsersService

logger = logging.getLogger(__name__)

router = APIRouter()


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

        service = UsersService(db)
        logger.info("Step 3: Getting or creating user in database...")
        user = service.get_or_create_google_user(
            google_id=google_id,
            email=email,
            full_name=full_name,
            picture_url=picture_url,
        )
        logger.info(f"Step 3: User retrieved/created - id: {user.id}, email: {user.email}")

        logger.info("Step 4: Creating JWT access token...")
        access_token = create_access_token(
            subject=str(user.id),
            email=user.email,
            roles=user.roles,
        )
        logger.info("Step 4: JWT token created successfully")

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
