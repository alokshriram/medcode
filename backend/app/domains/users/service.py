from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.users.models import User
from app.domains.users.roles import ALL_ROLES, DEFAULT_ROLE
from app.domains.users.schemas import UserCreate, UserUpdate


class UsersService:
    def __init__(self, db: Session):
        self.db = db

    def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def get_user(self, user_id: UUID) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_google_id(self, google_id: str) -> User | None:
        return self.db.query(User).filter(User.google_id == google_id).first()

    def create_user(self, user: UserCreate) -> User:
        db_user = User(**user.model_dump())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: UUID, user: UserUpdate) -> User | None:
        db_user = self.get_user(user_id)
        if not db_user:
            return None
        update_data = user.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_last_login(self, user_id: UUID) -> None:
        db_user = self.get_user(user_id)
        if db_user:
            db_user.last_login = datetime.now(timezone.utc)
            self.db.commit()

    def _is_super_user(self, email: str) -> bool:
        """Check if the email matches the configured super user."""
        return (
            settings.SUPER_USER_EMAIL is not None
            and email.lower() == settings.SUPER_USER_EMAIL.lower()
        )

    def _ensure_super_user_roles(self, user: User) -> None:
        """Ensure super user has all available roles."""
        if self._is_super_user(user.email):
            # Merge all roles with existing roles (in case new roles were added)
            current_roles = set(user.roles or [])
            all_roles = set(ALL_ROLES)
            if not all_roles.issubset(current_roles):
                user.roles = list(current_roles | all_roles)

    def get_or_create_google_user(self, google_id: str, email: str, full_name: str, picture_url: str | None = None) -> User:
        user = self.get_user_by_google_id(google_id)
        if user:
            self._ensure_super_user_roles(user)
            self.update_last_login(user.id)
            self.db.commit()
            self.db.refresh(user)
            return user

        user = self.get_user_by_email(email)
        if user:
            user.google_id = google_id
            if picture_url:
                user.picture_url = picture_url
            user.last_login = datetime.now(timezone.utc)
            self._ensure_super_user_roles(user)
            self.db.commit()
            self.db.refresh(user)
            return user

        # Determine roles for new user
        roles = ALL_ROLES if self._is_super_user(email) else [DEFAULT_ROLE]

        new_user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            picture_url=picture_url,
            roles=roles,
            last_login=datetime.now(timezone.utc),
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user
