from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.security import create_access_token
from app.domains.users.schemas import GoogleAuthRequest, TokenResponse, UserResponse, UserUpdate
from app.domains.users.service import UsersService

router = APIRouter()


@router.post("/auth/google", response_model=TokenResponse)
def google_auth(auth_request: GoogleAuthRequest, db: DbSession):
    try:
        idinfo = id_token.verify_oauth2_token(
            auth_request.credential,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

        google_id = idinfo["sub"]
        email = idinfo["email"]
        full_name = idinfo.get("name", email.split("@")[0])
        picture_url = idinfo.get("picture")

        service = UsersService(db)
        user = service.get_or_create_google_user(
            google_id=google_id,
            email=email,
            full_name=full_name,
            picture_url=picture_url,
        )

        access_token = create_access_token(
            subject=str(user.id),
            email=user.email,
            roles=user.roles,
        )

        return TokenResponse(access_token=access_token)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
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
