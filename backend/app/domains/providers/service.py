"""
Provider Service - Business logic for NPI Provider Registry.

Handles provider lookups, NPPES integration, and employment type management.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.tenant import TenantContext, TenantScopedService
from app.domains.providers.models import EmploymentType, NPIProvider
from app.domains.providers.nppes_client import (
    NPPESClient,
    NPPESProviderData,
    NPPESProviderNotFound,
    NPPESAPIError,
    get_nppes_client,
)

logger = logging.getLogger(__name__)


class ProviderService(TenantScopedService):
    """
    Service for managing NPI providers within a tenant context.

    Combines local database cache with NPPES API lookups for provider data.
    Employment type configuration is tenant-specific.
    """

    def __init__(
        self,
        db: Session,
        tenant_context: TenantContext,
        nppes_client: NPPESClient | None = None,
    ):
        super().__init__(db, tenant_context)
        self._nppes_client = nppes_client

    @property
    def nppes_client(self) -> NPPESClient:
        """Lazy-load NPPES client."""
        if self._nppes_client is None:
            self._nppes_client = get_nppes_client()
        return self._nppes_client

    def get_provider(self, provider_id: UUID) -> NPIProvider | None:
        """Get a provider by ID."""
        return self.scoped_query(NPIProvider).filter(NPIProvider.id == provider_id).first()

    def get_provider_by_npi(self, npi: str) -> NPIProvider | None:
        """
        Get a provider by NPI for the current tenant.

        Returns None if the provider doesn't exist in this tenant's registry.
        """
        return self.scoped_query(NPIProvider).filter(NPIProvider.npi == npi).first()

    def get_or_create_provider(
        self,
        npi: str,
        fetch_from_nppes: bool = True,
        created_by: UUID | None = None,
    ) -> tuple[NPIProvider, bool]:
        """
        Get existing provider or create from NPPES lookup.

        This is the primary method for handling NPIs from HL7 messages.
        If the provider doesn't exist locally, it will be fetched from NPPES
        and cached with employment_type=NULL (requiring admin configuration).

        Args:
            npi: 10-digit NPI number
            fetch_from_nppes: If True, fetch from NPPES when not found locally
            created_by: User ID creating the record (for audit)

        Returns:
            Tuple of (provider, created) where created is True if new record
        """
        # Check local cache first
        provider = self.get_provider_by_npi(npi)
        if provider:
            return provider, False

        if not fetch_from_nppes:
            return None, False

        # Fetch from NPPES API
        try:
            nppes_data = self.nppes_client.lookup_npi(npi)
            provider = self._create_provider_from_nppes(nppes_data, created_by)
            logger.info(f"Created provider {npi} from NPPES for tenant {self.tenant_id}")
            return provider, True

        except NPPESProviderNotFound:
            logger.warning(f"NPI {npi} not found in NPPES registry")
            # Create minimal record without NPPES data
            provider = self._create_minimal_provider(npi, created_by)
            return provider, True

        except NPPESAPIError as e:
            logger.error(f"Failed to fetch NPI {npi} from NPPES: {e}")
            # Create minimal record - can be updated later
            provider = self._create_minimal_provider(npi, created_by)
            return provider, True

    def _create_provider_from_nppes(
        self,
        nppes_data: NPPESProviderData,
        created_by: UUID | None = None,
    ) -> NPIProvider:
        """Create a provider record from NPPES data."""
        provider = NPIProvider(
            tenant_id=self.tenant_id,
            npi=nppes_data.npi,
            first_name=nppes_data.first_name,
            last_name=nppes_data.last_name,
            middle_name=nppes_data.middle_name,
            credential=nppes_data.credential,
            gender=nppes_data.gender,
            taxonomy_code=nppes_data.taxonomy_code,
            specialty=nppes_data.specialty,
            enumeration_type=nppes_data.enumeration_type,
            nppes_data=nppes_data.raw_response,
            nppes_last_fetched=datetime.now(timezone.utc),
            employment_type=None,  # Requires admin configuration
            is_active=True,
            created_by=created_by,
        )
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def _create_minimal_provider(
        self,
        npi: str,
        created_by: UUID | None = None,
    ) -> NPIProvider:
        """Create a minimal provider record when NPPES lookup fails."""
        provider = NPIProvider(
            tenant_id=self.tenant_id,
            npi=npi,
            employment_type=None,
            is_active=True,
            created_by=created_by,
        )
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def refresh_from_nppes(self, provider_id: UUID) -> NPIProvider | None:
        """
        Refresh provider data from NPPES API.

        Use this to update cached data if provider information has changed.
        """
        provider = self.get_provider(provider_id)
        if not provider:
            return None

        try:
            nppes_data = self.nppes_client.lookup_npi(provider.npi)
            provider.first_name = nppes_data.first_name
            provider.last_name = nppes_data.last_name
            provider.middle_name = nppes_data.middle_name
            provider.credential = nppes_data.credential
            provider.gender = nppes_data.gender
            provider.taxonomy_code = nppes_data.taxonomy_code
            provider.specialty = nppes_data.specialty
            provider.enumeration_type = nppes_data.enumeration_type
            provider.nppes_data = nppes_data.raw_response
            provider.nppes_last_fetched = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(provider)
            logger.info(f"Refreshed provider {provider.npi} from NPPES")
            return provider

        except (NPPESProviderNotFound, NPPESAPIError) as e:
            logger.error(f"Failed to refresh provider {provider.npi} from NPPES: {e}")
            return provider  # Return existing data

    def update_employment_type(
        self,
        provider_id: UUID,
        employment_type: EmploymentType,
        updated_by: UUID | None = None,
    ) -> NPIProvider | None:
        """
        Set the employment type for a provider.

        This is the key configuration that determines ProFee routing.
        """
        provider = self.get_provider(provider_id)
        if not provider:
            return None

        provider.employment_type = employment_type.value
        provider.updated_by = updated_by
        self.db.commit()
        self.db.refresh(provider)

        logger.info(
            f"Updated provider {provider.npi} employment_type to {employment_type.value}"
        )
        return provider

    def set_active_status(
        self,
        provider_id: UUID,
        is_active: bool,
        updated_by: UUID | None = None,
    ) -> NPIProvider | None:
        """Activate or deactivate a provider."""
        provider = self.get_provider(provider_id)
        if not provider:
            return None

        provider.is_active = is_active
        provider.updated_by = updated_by
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def list_providers(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        is_configured: bool | None = None,
        employment_type: EmploymentType | None = None,
        search: str | None = None,
    ) -> tuple[list[NPIProvider], int]:
        """
        List providers with filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            is_active: Filter by active status
            is_configured: Filter by whether employment_type is set
            employment_type: Filter by specific employment type
            search: Search by NPI, name, or specialty

        Returns:
            Tuple of (providers, total_count)
        """
        query = self.scoped_query(NPIProvider)

        if is_active is not None:
            query = query.filter(NPIProvider.is_active == is_active)

        if is_configured is not None:
            if is_configured:
                query = query.filter(NPIProvider.employment_type.isnot(None))
            else:
                query = query.filter(NPIProvider.employment_type.is_(None))

        if employment_type is not None:
            query = query.filter(NPIProvider.employment_type == employment_type.value)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (NPIProvider.npi.ilike(search_term))
                | (NPIProvider.first_name.ilike(search_term))
                | (NPIProvider.last_name.ilike(search_term))
                | (NPIProvider.specialty.ilike(search_term))
            )

        total = query.count()
        providers = query.order_by(NPIProvider.last_name, NPIProvider.first_name).offset(skip).limit(limit).all()

        return providers, total

    def list_unconfigured_providers(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[NPIProvider], int]:
        """
        List providers that need employment type configuration.

        These are providers auto-created from HL7 messages that haven't
        been configured by an admin yet.
        """
        return self.list_providers(
            skip=skip,
            limit=limit,
            is_active=True,
            is_configured=False,
        )

    def should_create_profee_work(self, npi: str) -> bool:
        """
        Determine if encounters for this provider should create ProFee work items.

        Business rule:
        - If provider not found: True (default to creating work)
        - If provider unconfigured (employment_type=NULL): True
        - If HOSPITAL_EMPLOYED or LOCUM_TENENS: True
        - If INDEPENDENT_CONTRACTOR or HOSPITAL_PRIVILEGES_ONLY: False
        """
        provider = self.get_provider_by_npi(npi)
        if not provider:
            return True  # Unknown provider - default to creating work

        return provider.creates_profee_work

    def bulk_update_employment_type(
        self,
        provider_ids: list[UUID],
        employment_type: EmploymentType,
        updated_by: UUID | None = None,
    ) -> int:
        """
        Bulk update employment type for multiple providers.

        Returns count of updated records.
        """
        count = (
            self.scoped_query(NPIProvider)
            .filter(NPIProvider.id.in_(provider_ids))
            .update(
                {
                    NPIProvider.employment_type: employment_type.value,
                    NPIProvider.updated_by: updated_by,
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return count
