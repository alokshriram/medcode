"""Add coding_queue_items table for encounter-based work items

Revision ID: 20251221_queue_items
Revises: 20251221_encounters
Create Date: 2025-12-21

See: docs/pdd/PDD-001-hl7-ingestion-and-codable-encounters.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251221_queue_items'
down_revision: Union[str, None] = '20251221_encounters'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # coding_queue_items - Work items linked to encounters
    op.create_table(
        'coding_queue_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('billing_component', sa.String(length=20), nullable=False),  # facility, professional
        sa.Column('queue_type', sa.String(length=50), nullable=True),
        sa.Column('service_line', sa.String(length=100), nullable=True),
        sa.Column('payer_identifier', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('assigned_to', sa.UUID(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        # Note: No FK to encounters schema to maintain bounded context separation (reference by ID only)
        sa.PrimaryKeyConstraint('id'),
        schema='workflow'
    )
    op.create_index('ix_workflow_coding_queue_items_encounter_id', 'coding_queue_items', ['encounter_id'], schema='workflow')
    op.create_index('ix_workflow_coding_queue_items_status', 'coding_queue_items', ['status'], schema='workflow')
    op.create_index('ix_workflow_coding_queue_items_billing_component', 'coding_queue_items', ['billing_component'], schema='workflow')
    op.create_index('ix_workflow_coding_queue_items_service_line', 'coding_queue_items', ['service_line'], schema='workflow')
    op.create_index('ix_workflow_coding_queue_items_assigned_to', 'coding_queue_items', ['assigned_to'], schema='workflow')

    # encounter_snapshots - Point-in-time snapshot of encounter data for coding
    op.create_table(
        'encounter_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('queue_item_id', sa.UUID(), nullable=False),
        sa.Column('snapshot_data', sa.JSON(), nullable=False),  # Full encounter data as JSON
        sa.Column('snapshot_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),  # User who triggered the snapshot (or null for auto)
        sa.ForeignKeyConstraint(['queue_item_id'], ['workflow.coding_queue_items.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='workflow'
    )
    op.create_index('ix_workflow_encounter_snapshots_encounter_id', 'encounter_snapshots', ['encounter_id'], schema='workflow')
    op.create_index('ix_workflow_encounter_snapshots_queue_item_id', 'encounter_snapshots', ['queue_item_id'], schema='workflow')

    # coding_configuration - System configuration for coding workflow
    op.create_table(
        'coding_configuration',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
        schema='workflow'
    )

    # Insert default configuration
    op.execute("""
        INSERT INTO workflow.coding_configuration (id, key, value, description) VALUES
        (gen_random_uuid(), 'always_create_facility', 'true', 'Always create facility work item for encounters'),
        (gen_random_uuid(), 'always_create_professional', 'false', 'Always create professional work item regardless of conditions'),
        (gen_random_uuid(), 'professional_component_services', '["radiology", "pathology", "cardiology", "surgery"]', 'Service lines that trigger professional component'),
        (gen_random_uuid(), 'encounter_timeout_hours', '72', 'Hours before flagging stale encounter')
    """)


def downgrade() -> None:
    op.drop_table('coding_configuration', schema='workflow')

    op.drop_index('ix_workflow_encounter_snapshots_queue_item_id', table_name='encounter_snapshots', schema='workflow')
    op.drop_index('ix_workflow_encounter_snapshots_encounter_id', table_name='encounter_snapshots', schema='workflow')
    op.drop_table('encounter_snapshots', schema='workflow')

    op.drop_index('ix_workflow_coding_queue_items_assigned_to', table_name='coding_queue_items', schema='workflow')
    op.drop_index('ix_workflow_coding_queue_items_service_line', table_name='coding_queue_items', schema='workflow')
    op.drop_index('ix_workflow_coding_queue_items_billing_component', table_name='coding_queue_items', schema='workflow')
    op.drop_index('ix_workflow_coding_queue_items_status', table_name='coding_queue_items', schema='workflow')
    op.drop_index('ix_workflow_coding_queue_items_encounter_id', table_name='coding_queue_items', schema='workflow')
    op.drop_table('coding_queue_items', schema='workflow')
