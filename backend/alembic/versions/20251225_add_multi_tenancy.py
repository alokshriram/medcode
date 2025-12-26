"""Add multi-tenancy support with tenants, memberships, and tenant_id columns

Revision ID: 20251225_multi_tenancy
Revises: 20251221_test_roles
Create Date: 2025-12-25

Adds:
- users.tenants table for organizations
- users.user_tenant_memberships table for many-to-many user-tenant relationship
- users.tenant_invitations table for tenant invites
- tenant_id columns to all data tables (nullable for backward compatibility)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251225_multi_tenancy'
down_revision: Union[str, None] = '20251221_test_roles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenants table in users schema
    op.create_table(
        'tenants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        schema='users'
    )
    op.create_index('ix_users_tenants_slug', 'tenants', ['slug'], schema='users')

    # Create user_tenant_memberships table
    op.create_table(
        'user_tenant_memberships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('roles', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['users.tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant'),
        schema='users'
    )
    op.create_index('ix_users_user_tenant_memberships_user_id', 'user_tenant_memberships', ['user_id'], schema='users')
    op.create_index('ix_users_user_tenant_memberships_tenant_id', 'user_tenant_memberships', ['tenant_id'], schema='users')

    # Create tenant_invitations table
    op.create_table(
        'tenant_invitations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('roles', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('invited_by_user_id', sa.UUID(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['users.tenants.id'], ),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='users'
    )
    op.create_index('ix_users_tenant_invitations_tenant_id', 'tenant_invitations', ['tenant_id'], schema='users')
    op.create_index('ix_users_tenant_invitations_email', 'tenant_invitations', ['email'], schema='users')

    # Add tenant_id to encounters schema tables
    op.add_column('hl7_messages', sa.Column('tenant_id', sa.UUID(), nullable=True), schema='encounters')
    op.create_index('ix_encounters_hl7_messages_tenant_id', 'hl7_messages', ['tenant_id'], schema='encounters')

    op.add_column('patients', sa.Column('tenant_id', sa.UUID(), nullable=True), schema='encounters')
    op.create_index('ix_encounters_patients_tenant_id', 'patients', ['tenant_id'], schema='encounters')

    op.add_column('encounters', sa.Column('tenant_id', sa.UUID(), nullable=True), schema='encounters')
    op.create_index('ix_encounters_encounters_tenant_id', 'encounters', ['tenant_id'], schema='encounters')

    # Add tenant_id to workflow schema tables
    op.add_column('coding_tasks', sa.Column('tenant_id', sa.UUID(), nullable=True), schema='workflow')
    op.create_index('ix_workflow_coding_tasks_tenant_id', 'coding_tasks', ['tenant_id'], schema='workflow')

    op.add_column('coding_queue_items', sa.Column('tenant_id', sa.UUID(), nullable=True), schema='workflow')
    op.create_index('ix_workflow_coding_queue_items_tenant_id', 'coding_queue_items', ['tenant_id'], schema='workflow')

    op.add_column('encounter_snapshots', sa.Column('tenant_id', sa.UUID(), nullable=True), schema='workflow')
    op.create_index('ix_workflow_encounter_snapshots_tenant_id', 'encounter_snapshots', ['tenant_id'], schema='workflow')

    op.add_column('coding_configuration', sa.Column('tenant_id', sa.UUID(), nullable=True), schema='workflow')
    op.create_index('ix_workflow_coding_configuration_tenant_id', 'coding_configuration', ['tenant_id'], schema='workflow')


def downgrade() -> None:
    # Remove tenant_id from workflow schema tables
    op.drop_index('ix_workflow_coding_configuration_tenant_id', table_name='coding_configuration', schema='workflow')
    op.drop_column('coding_configuration', 'tenant_id', schema='workflow')

    op.drop_index('ix_workflow_encounter_snapshots_tenant_id', table_name='encounter_snapshots', schema='workflow')
    op.drop_column('encounter_snapshots', 'tenant_id', schema='workflow')

    op.drop_index('ix_workflow_coding_queue_items_tenant_id', table_name='coding_queue_items', schema='workflow')
    op.drop_column('coding_queue_items', 'tenant_id', schema='workflow')

    op.drop_index('ix_workflow_coding_tasks_tenant_id', table_name='coding_tasks', schema='workflow')
    op.drop_column('coding_tasks', 'tenant_id', schema='workflow')

    # Remove tenant_id from encounters schema tables
    op.drop_index('ix_encounters_encounters_tenant_id', table_name='encounters', schema='encounters')
    op.drop_column('encounters', 'tenant_id', schema='encounters')

    op.drop_index('ix_encounters_patients_tenant_id', table_name='patients', schema='encounters')
    op.drop_column('patients', 'tenant_id', schema='encounters')

    op.drop_index('ix_encounters_hl7_messages_tenant_id', table_name='hl7_messages', schema='encounters')
    op.drop_column('hl7_messages', 'tenant_id', schema='encounters')

    # Drop tenant tables
    op.drop_index('ix_users_tenant_invitations_email', table_name='tenant_invitations', schema='users')
    op.drop_index('ix_users_tenant_invitations_tenant_id', table_name='tenant_invitations', schema='users')
    op.drop_table('tenant_invitations', schema='users')

    op.drop_index('ix_users_user_tenant_memberships_tenant_id', table_name='user_tenant_memberships', schema='users')
    op.drop_index('ix_users_user_tenant_memberships_user_id', table_name='user_tenant_memberships', schema='users')
    op.drop_table('user_tenant_memberships', schema='users')

    op.drop_index('ix_users_tenants_slug', table_name='tenants', schema='users')
    op.drop_table('tenants', schema='users')
