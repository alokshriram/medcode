import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.domains.users.models import Tenant, TenantInvitation, User, UserTenantMembership
from app.domains.users.roles import DEFAULT_ROLE


class TenantService:
    def __init__(self, db: Session):
        self.db = db

    def get_tenant(self, tenant_id: UUID) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_user_tenants(self, user_id: UUID) -> list[UserTenantMembership]:
        return (
            self.db.query(UserTenantMembership)
            .filter(UserTenantMembership.user_id == user_id)
            .options(joinedload(UserTenantMembership.tenant))
            .all()
        )

    def get_user_default_tenant(self, user_id: UUID) -> UserTenantMembership | None:
        """Get the user's default tenant membership."""
        return (
            self.db.query(UserTenantMembership)
            .filter(
                UserTenantMembership.user_id == user_id,
                UserTenantMembership.is_default == True,
            )
            .options(joinedload(UserTenantMembership.tenant))
            .first()
        )

    def get_membership(self, user_id: UUID, tenant_id: UUID) -> UserTenantMembership | None:
        """Get a specific user-tenant membership."""
        return (
            self.db.query(UserTenantMembership)
            .filter(
                UserTenantMembership.user_id == user_id,
                UserTenantMembership.tenant_id == tenant_id,
            )
            .options(joinedload(UserTenantMembership.tenant))
            .first()
        )

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-friendly slug from name."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

        # Ensure uniqueness by appending a number if needed
        base_slug = slug
        counter = 1
        while self.get_tenant_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def create_tenant(self, name: str, owner_user_id: UUID, owner_roles: list[str] | None = None) -> Tenant:
        """Create a new tenant and add the owner as a member with tenant-admin role."""
        slug = self._generate_slug(name)

        tenant = Tenant(
            name=name,
            slug=slug,
        )
        self.db.add(tenant)
        self.db.flush()  # Get the tenant ID

        # Add owner as member with tenant-admin role (plus any additional roles)
        roles = ["tenant-admin"]
        if owner_roles:
            roles.extend([r for r in owner_roles if r not in roles])

        self.add_user_to_tenant(
            user_id=owner_user_id,
            tenant_id=tenant.id,
            roles=roles,
            is_default=True,
        )

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def add_user_to_tenant(
        self,
        user_id: UUID,
        tenant_id: UUID,
        roles: list[str],
        is_default: bool = False,
    ) -> UserTenantMembership:
        """Add a user to a tenant with specified roles."""
        # Check if membership already exists
        existing = self.get_membership(user_id, tenant_id)
        if existing:
            return existing

        # If this will be the default, unset any existing default
        if is_default:
            self.db.query(UserTenantMembership).filter(
                UserTenantMembership.user_id == user_id,
                UserTenantMembership.is_default == True,
            ).update({"is_default": False})

        membership = UserTenantMembership(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            is_default=is_default,
        )
        self.db.add(membership)
        return membership

    def remove_user_from_tenant(self, user_id: UUID, tenant_id: UUID) -> bool:
        """Remove a user from a tenant."""
        result = (
            self.db.query(UserTenantMembership)
            .filter(
                UserTenantMembership.user_id == user_id,
                UserTenantMembership.tenant_id == tenant_id,
            )
            .delete()
        )
        self.db.commit()
        return result > 0

    def update_user_tenant_roles(
        self, user_id: UUID, tenant_id: UUID, roles: list[str]
    ) -> UserTenantMembership | None:
        """Update a user's roles within a tenant."""
        membership = self.get_membership(user_id, tenant_id)
        if not membership:
            return None

        membership.roles = roles
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def get_tenant_members(self, tenant_id: UUID) -> list[UserTenantMembership]:
        """Get all members of a tenant."""
        return (
            self.db.query(UserTenantMembership)
            .filter(UserTenantMembership.tenant_id == tenant_id)
            .options(joinedload(UserTenantMembership.user))
            .all()
        )

    # Invitation methods
    def create_invitation(
        self,
        tenant_id: UUID,
        email: str,
        roles: list[str],
        invited_by: UUID,
        expires_in_days: int = 7,
    ) -> TenantInvitation:
        """Create an invitation to join a tenant."""
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            email=email.lower(),
            roles=roles,
            invited_by_user_id=invited_by,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        )
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        return invitation

    def get_pending_invitations_for_email(self, email: str) -> list[TenantInvitation]:
        """Get all pending (non-expired, non-accepted) invitations for an email."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(TenantInvitation)
            .filter(
                TenantInvitation.email == email.lower(),
                TenantInvitation.accepted_at.is_(None),
                TenantInvitation.expires_at > now,
            )
            .options(joinedload(TenantInvitation.tenant))
            .all()
        )

    def accept_invitation(self, invitation_id: UUID, user_id: UUID) -> UserTenantMembership | None:
        """Accept an invitation and add the user to the tenant."""
        invitation = (
            self.db.query(TenantInvitation)
            .filter(TenantInvitation.id == invitation_id)
            .first()
        )

        if not invitation:
            return None

        # Check if already accepted or expired
        now = datetime.now(timezone.utc)
        if invitation.accepted_at is not None or invitation.expires_at < now:
            return None

        # Mark invitation as accepted
        invitation.accepted_at = now

        # Add user to tenant
        membership = self.add_user_to_tenant(
            user_id=user_id,
            tenant_id=invitation.tenant_id,
            roles=invitation.roles,
            is_default=False,
        )

        self.db.commit()
        return membership

    def auto_accept_pending_invitations(self, user: User) -> list[UserTenantMembership]:
        """Automatically accept all pending invitations for a user's email."""
        invitations = self.get_pending_invitations_for_email(user.email)
        memberships = []

        for invitation in invitations:
            membership = self.accept_invitation(invitation.id, user.id)
            if membership:
                memberships.append(membership)

        return memberships

    def ensure_default_tenant(self, user: User) -> Tenant:
        """Ensure user has a default tenant (lazy migration for existing users).

        If user has no tenant memberships:
        1. Create a personal tenant named "{user.full_name}'s Organization"
        2. Add user as tenant-admin with their current roles

        Returns the user's default tenant.
        """
        # Check if user already has any tenants
        memberships = self.get_user_tenants(user.id)

        if memberships:
            # Return existing default, or first tenant if no default set
            default = next((m for m in memberships if m.is_default), None)
            if default:
                return default.tenant

            # Set first tenant as default if none is set
            memberships[0].is_default = True
            self.db.commit()
            return memberships[0].tenant

        # No tenants - create a personal tenant
        tenant_name = f"{user.full_name}'s Organization"

        # Use user's existing roles (from legacy system) as their tenant roles
        # If no roles, use default role
        user_roles = user.roles if user.roles else [DEFAULT_ROLE]

        tenant = self.create_tenant(
            name=tenant_name,
            owner_user_id=user.id,
            owner_roles=user_roles,
        )

        return tenant

    def set_default_tenant(self, user_id: UUID, tenant_id: UUID) -> bool:
        """Set a user's default tenant."""
        membership = self.get_membership(user_id, tenant_id)
        if not membership:
            return False

        # Unset any existing default
        self.db.query(UserTenantMembership).filter(
            UserTenantMembership.user_id == user_id,
            UserTenantMembership.is_default == True,
        ).update({"is_default": False})

        # Set new default
        membership.is_default = True
        self.db.commit()
        return True
