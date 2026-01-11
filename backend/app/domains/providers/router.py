"""
Provider API Router - Endpoints for NPI Provider Registry management.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import DbSession, TenantContextDep
from app.domains.providers.models import EmploymentType
from app.domains.providers.nppes_client import (
    NPPESAPIError,
    NPPESProviderNotFound,
    get_nppes_client,
)
from app.domains.providers.schemas import (
    BulkUpdateEmploymentTypeRequest,
    BulkUpdateResponse,
    NPPESLookupResponse,
    NPPESSearchRequest,
    NPPESSearchResponse,
    NPPESSearchResultItem,
    ProviderDetailResponse,
    ProviderListResponse,
    ProviderLookupRequest,
    ProviderResponse,
    SetActiveStatusRequest,
    UpdateEmploymentTypeRequest,
)
from app.domains.providers.service import ProviderService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Provider CRUD Endpoints
# ============================================================================


@router.get("", response_model=ProviderListResponse)
def list_providers(
    db: DbSession,
    tenant_context: TenantContextDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: bool | None = None,
    is_configured: bool | None = None,
    employment_type: EmploymentType | None = None,
    search: str | None = None,
):
    """
    List providers for the current tenant.

    Supports filtering by:
    - is_active: Active status
    - is_configured: Whether employment type has been set
    - employment_type: Specific employment type
    - search: Search by NPI, name, or specialty
    """
    service = ProviderService(db, tenant_context)
    providers, total = service.list_providers(
        skip=skip,
        limit=limit,
        is_active=is_active,
        is_configured=is_configured,
        employment_type=employment_type,
        search=search,
    )

    return ProviderListResponse(
        items=[ProviderResponse.model_validate(p) for p in providers],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/unconfigured", response_model=ProviderListResponse)
def list_unconfigured_providers(
    db: DbSession,
    tenant_context: TenantContextDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    List providers that need employment type configuration.

    These are providers auto-created from HL7 messages that haven't
    been reviewed by an admin yet. ProFee work items are being created
    for these providers by default.
    """
    service = ProviderService(db, tenant_context)
    providers, total = service.list_unconfigured_providers(skip=skip, limit=limit)

    return ProviderListResponse(
        items=[ProviderResponse.model_validate(p) for p in providers],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{provider_id}", response_model=ProviderDetailResponse)
def get_provider(
    provider_id: UUID,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """Get a provider by ID with full details including NPPES data."""
    service = ProviderService(db, tenant_context)
    provider = service.get_provider(provider_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return ProviderDetailResponse.model_validate(provider)


@router.get("/npi/{npi}", response_model=ProviderResponse)
def get_provider_by_npi(
    npi: str,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """Get a provider by NPI number."""
    service = ProviderService(db, tenant_context)
    provider = service.get_provider_by_npi(npi)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with NPI {npi} not found in this tenant",
        )

    return ProviderResponse.model_validate(provider)


# ============================================================================
# Provider Lookup/Creation
# ============================================================================


@router.post("/lookup", response_model=ProviderResponse)
def lookup_or_create_provider(
    request: ProviderLookupRequest,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """
    Look up a provider by NPI, creating from NPPES if not found locally.

    This is the primary endpoint for adding providers to the tenant's registry.
    If the provider doesn't exist locally, it will be fetched from the NPPES API
    and cached with employment_type=NULL (requiring admin configuration).
    """
    service = ProviderService(db, tenant_context)
    provider, created = service.get_or_create_provider(
        npi=request.npi,
        fetch_from_nppes=request.fetch_from_nppes,
        created_by=tenant_context.user_id,
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with NPI {request.npi} not found",
        )

    if created:
        logger.info(f"Created provider {request.npi} for tenant {tenant_context.tenant_id}")

    return ProviderResponse.model_validate(provider)


# ============================================================================
# Provider Configuration
# ============================================================================


@router.patch("/{provider_id}/employment-type", response_model=ProviderResponse)
def update_employment_type(
    provider_id: UUID,
    request: UpdateEmploymentTypeRequest,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """
    Update the employment type for a provider.

    This is the key configuration that determines ProFee routing:
    - HOSPITAL_EMPLOYED / LOCUM_TENENS: Create ProFee work items
    - INDEPENDENT_CONTRACTOR / HOSPITAL_PRIVILEGES_ONLY: Skip ProFee work items
    """
    service = ProviderService(db, tenant_context)
    provider = service.update_employment_type(
        provider_id=provider_id,
        employment_type=request.employment_type,
        updated_by=tenant_context.user_id,
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return ProviderResponse.model_validate(provider)


@router.post("/bulk-employment-type", response_model=BulkUpdateResponse)
def bulk_update_employment_type(
    request: BulkUpdateEmploymentTypeRequest,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """
    Bulk update employment type for multiple providers.

    Useful for configuring multiple providers at once during onboarding.
    """
    service = ProviderService(db, tenant_context)
    count = service.bulk_update_employment_type(
        provider_ids=request.provider_ids,
        employment_type=request.employment_type,
        updated_by=tenant_context.user_id,
    )

    return BulkUpdateResponse(updated_count=count)


@router.patch("/{provider_id}/active", response_model=ProviderResponse)
def set_active_status(
    provider_id: UUID,
    request: SetActiveStatusRequest,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """Activate or deactivate a provider."""
    service = ProviderService(db, tenant_context)
    provider = service.set_active_status(
        provider_id=provider_id,
        is_active=request.is_active,
        updated_by=tenant_context.user_id,
    )

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return ProviderResponse.model_validate(provider)


@router.post("/{provider_id}/refresh", response_model=ProviderResponse)
def refresh_from_nppes(
    provider_id: UUID,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """
    Refresh provider data from NPPES API.

    Use this to update cached data if provider information has changed
    (e.g., new credentials, specialty change).
    """
    service = ProviderService(db, tenant_context)
    provider = service.refresh_from_nppes(provider_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return ProviderResponse.model_validate(provider)


# ============================================================================
# NPPES Direct Lookup (Preview before adding to tenant)
# ============================================================================


@router.get("/nppes/lookup/{npi}", response_model=NPPESLookupResponse)
def nppes_lookup(
    npi: str,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """
    Look up a provider in NPPES without adding to tenant registry.

    Use this to preview provider information before adding them.
    """
    if not npi.isdigit() or len(npi) != 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NPI must be exactly 10 digits",
        )

    # Check if already exists in tenant
    service = ProviderService(db, tenant_context)
    existing = service.get_provider_by_npi(npi)
    exists_in_tenant = existing is not None

    # Fetch from NPPES
    try:
        client = get_nppes_client()
        data = client.lookup_npi(npi)

        return NPPESLookupResponse(
            npi=data.npi,
            enumeration_type=data.enumeration_type,
            first_name=data.first_name,
            last_name=data.last_name,
            middle_name=data.middle_name,
            credential=data.credential,
            gender=data.gender,
            taxonomy_code=data.taxonomy_code,
            specialty=data.specialty,
            status=data.status,
            exists_in_tenant=exists_in_tenant,
        )

    except NPPESProviderNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NPI {npi} not found in NPPES registry",
        )
    except NPPESAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to NPPES API: {str(e)}",
        )


@router.post("/nppes/search", response_model=NPPESSearchResponse)
def nppes_search(
    request: NPPESSearchRequest,
    db: DbSession,
    tenant_context: TenantContextDep,
):
    """
    Search NPPES registry for providers.

    Use this to find providers by name, state, or specialty.
    """
    try:
        client = get_nppes_client()
        results = client.search_providers(
            first_name=request.first_name,
            last_name=request.last_name,
            state=request.state,
            taxonomy_description=request.taxonomy_description,
            limit=request.limit,
        )

        # Check which ones already exist in tenant
        service = ProviderService(db, tenant_context)
        items = []
        for r in results:
            existing = service.get_provider_by_npi(r.npi)
            items.append(
                NPPESSearchResultItem(
                    npi=r.npi,
                    first_name=r.first_name,
                    last_name=r.last_name,
                    credential=r.credential,
                    specialty=r.specialty,
                    exists_in_tenant=existing is not None,
                )
            )

        return NPPESSearchResponse(results=items, count=len(items))

    except NPPESAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to NPPES API: {str(e)}",
        )
