"""
Provider Schemas - Pydantic models for API request/response validation.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.providers.models import EmploymentType


# ============================================================================
# Response Schemas
# ============================================================================


class ProviderResponse(BaseModel):
    """Standard provider response."""
    id: UUID
    npi: str
    tenant_id: UUID

    # Name and credentials
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    credential: str | None
    full_name: str
    gender: str | None

    # Specialty
    taxonomy_code: str | None
    specialty: str | None
    enumeration_type: str | None

    # Employment configuration
    employment_type: EmploymentType | None
    is_configured: bool
    is_active: bool
    creates_profee_work: bool

    # Billing
    billing_npi: str | None

    # Timestamps
    nppes_last_fetched: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProviderListResponse(BaseModel):
    """Paginated list of providers."""
    items: list[ProviderResponse]
    total: int
    skip: int
    limit: int


class ProviderDetailResponse(ProviderResponse):
    """Provider with full NPPES data."""
    nppes_data: dict | None
    created_by: UUID | None
    updated_by: UUID | None

    class Config:
        from_attributes = True


# ============================================================================
# Request Schemas
# ============================================================================


class ProviderLookupRequest(BaseModel):
    """Request to look up a provider by NPI."""
    npi: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    fetch_from_nppes: bool = True


class UpdateEmploymentTypeRequest(BaseModel):
    """Request to update provider employment type."""
    employment_type: EmploymentType


class BulkUpdateEmploymentTypeRequest(BaseModel):
    """Request to bulk update employment type for multiple providers."""
    provider_ids: list[UUID]
    employment_type: EmploymentType


class BulkUpdateResponse(BaseModel):
    """Response for bulk update operations."""
    updated_count: int


class SetActiveStatusRequest(BaseModel):
    """Request to activate/deactivate a provider."""
    is_active: bool


# ============================================================================
# Query Schemas
# ============================================================================


class ProviderFilters(BaseModel):
    """Filter parameters for listing providers."""
    is_active: bool | None = None
    is_configured: bool | None = None
    employment_type: EmploymentType | None = None
    search: str | None = None


# ============================================================================
# NPPES Schemas
# ============================================================================


class NPPESLookupResponse(BaseModel):
    """Response from NPPES lookup (before creating local record)."""
    npi: str
    enumeration_type: str
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    credential: str | None
    gender: str | None
    taxonomy_code: str | None
    specialty: str | None
    status: str
    exists_in_tenant: bool  # Whether we already have this provider


class NPPESSearchRequest(BaseModel):
    """Request to search NPPES registry."""
    first_name: str | None = None
    last_name: str | None = None
    state: str | None = Field(None, min_length=2, max_length=2)
    taxonomy_description: str | None = None
    limit: int = Field(10, ge=1, le=200)


class NPPESSearchResultItem(BaseModel):
    """Single result from NPPES search."""
    npi: str
    first_name: str | None
    last_name: str | None
    credential: str | None
    specialty: str | None
    exists_in_tenant: bool


class NPPESSearchResponse(BaseModel):
    """Response from NPPES search."""
    results: list[NPPESSearchResultItem]
    count: int
