import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmploymentType(str, Enum):
    """
    Provider relationship to hospital - determines ProFee billing routing.

    HOSPITAL_EMPLOYED: Hospital bills ProFee under hospital NPI or provider's individual NPI
    INDEPENDENT_CONTRACTOR: External group bills ProFee (not in our system)
    HOSPITAL_PRIVILEGES_ONLY: Surgeon with privileges, bills own ProFee
    LOCUM_TENENS: Temporary provider, typically hospital-employed for billing
    """
    HOSPITAL_EMPLOYED = "HOSPITAL_EMPLOYED"
    INDEPENDENT_CONTRACTOR = "INDEPENDENT_CONTRACTOR"
    HOSPITAL_PRIVILEGES_ONLY = "HOSPITAL_PRIVILEGES_ONLY"
    LOCUM_TENENS = "LOCUM_TENENS"


class NPIProvider(Base):
    """
    National Provider Identifier registry with employment metadata.

    Combines data from two sources:
    1. NPPES API (public): name, credentials, specialty, taxonomy
    2. Hospital configuration (private): employment type, active status

    Each tenant (hospital) maintains its own provider records. The same NPI
    can exist in multiple tenants with different employment statuses.
    """
    __tablename__ = "npi_providers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "npi", name="uq_tenant_npi"),
        {"schema": "providers"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    npi: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # From NPPES API (cached)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    credential: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Primary taxonomy/specialty
    taxonomy_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Full NPPES response cached as JSON for reference
    nppes_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    nppes_last_fetched: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Enumeration type from NPPES (NPI-1 = Individual, NPI-2 = Organization)
    enumeration_type: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Hospital-specific configuration (admin sets this)
    # Stored as String, validated at application level via EmploymentType enum
    employment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True  # NULL = unconfigured, needs admin review
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Billing NPIs (if different from individual NPI)
    billing_npi: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    @property
    def full_name(self) -> str:
        """Return formatted full name."""
        parts = [self.first_name, self.middle_name, self.last_name]
        name = " ".join(p for p in parts if p)
        if self.credential:
            name = f"{name}, {self.credential}"
        return name

    @property
    def is_configured(self) -> bool:
        """Check if employment type has been set by admin."""
        return self.employment_type is not None

    @property
    def creates_profee_work(self) -> bool:
        """
        Determine if this provider's encounters should create ProFee work items.

        Returns True if:
        - Employment type is not set (unconfigured - default to creating work)
        - Employment type is HOSPITAL_EMPLOYED or LOCUM_TENENS

        Returns False if:
        - Employment type is INDEPENDENT_CONTRACTOR or HOSPITAL_PRIVILEGES_ONLY
        """
        if self.employment_type is None:
            return True  # Default to creating work for unconfigured providers
        return self.employment_type in (
            EmploymentType.HOSPITAL_EMPLOYED.value,
            EmploymentType.LOCUM_TENENS.value,
        )
