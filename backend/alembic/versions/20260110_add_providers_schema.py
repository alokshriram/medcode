"""Add providers schema with NPI provider registry

Revision ID: 20260110_providers
Revises: 20251225_multi_tenancy
Create Date: 2026-01-10

Adds:
- providers schema
- providers.npi_providers table for provider registry with NPPES data caching
- Employment type enum for ProFee routing decisions

See: .plans/gaps.md GAP-001 NPI Provider Registry
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260110_providers'
down_revision: Union[str, None] = '20251225_multi_tenancy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create providers schema
    op.execute("CREATE SCHEMA IF NOT EXISTS providers")

    # Create npi_providers table
    op.create_table(
        'npi_providers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('npi', sa.String(length=10), nullable=False),

        # From NPPES API (cached)
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('credential', sa.String(length=50), nullable=True),
        sa.Column('gender', sa.String(length=10), nullable=True),

        # Primary taxonomy/specialty
        sa.Column('taxonomy_code', sa.String(length=20), nullable=True),
        sa.Column('specialty', sa.String(length=200), nullable=True),

        # NPPES enumeration type (NPI-1 = Individual, NPI-2 = Organization)
        sa.Column('enumeration_type', sa.String(length=10), nullable=True),

        # Full NPPES response cached as JSON
        sa.Column('nppes_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('nppes_last_fetched', sa.DateTime(timezone=True), nullable=True),

        # Hospital-specific configuration (uses String to avoid enum creation issues)
        # Valid values: HOSPITAL_EMPLOYED, INDEPENDENT_CONTRACTOR, HOSPITAL_PRIVILEGES_ONLY, LOCUM_TENENS
        sa.Column('employment_type', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Billing NPI (if different from individual NPI)
        sa.Column('billing_npi', sa.String(length=10), nullable=True),

        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'npi', name='uq_tenant_npi'),
        schema='providers'
    )

    # Create indexes
    op.create_index(
        'ix_providers_npi_providers_tenant_id',
        'npi_providers',
        ['tenant_id'],
        schema='providers'
    )
    op.create_index(
        'ix_providers_npi_providers_npi',
        'npi_providers',
        ['npi'],
        schema='providers'
    )
    op.create_index(
        'ix_providers_npi_providers_employment_type',
        'npi_providers',
        ['employment_type'],
        schema='providers'
    )
    op.create_index(
        'ix_providers_npi_providers_is_active',
        'npi_providers',
        ['is_active'],
        schema='providers'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_providers_npi_providers_is_active', table_name='npi_providers', schema='providers')
    op.drop_index('ix_providers_npi_providers_npi', table_name='npi_providers', schema='providers')
    op.drop_index('ix_providers_npi_providers_tenant_id', table_name='npi_providers', schema='providers')

    # Drop table
    op.drop_table('npi_providers', schema='providers')

    # Drop schema (only if empty)
    op.execute("DROP SCHEMA IF EXISTS providers")
