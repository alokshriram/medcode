"""Add coding_results table for storing entered codes

Revision ID: 20260117_coding_results
Revises: 20260110_providers
Create Date: 2026-01-17

Stores diagnosis and procedure codes entered by coders for each queue item.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260117_coding_results'
down_revision: Union[str, None] = '20260110_providers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # coding_results - Codes entered by coders
    op.create_table(
        'coding_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.Column('queue_item_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('code_type', sa.String(length=20), nullable=False),  # ICD-10-CM, ICD-10-PCS, CPT
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('code_category', sa.String(length=20), nullable=False),  # diagnosis, procedure
        sa.Column('is_principal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('poa_indicator', sa.String(length=5), nullable=True),  # Y, N, U, W, 1 (exempt)
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('procedure_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('coded_by', sa.UUID(), nullable=False),
        sa.Column('coded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['queue_item_id'], ['workflow.coding_queue_items.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='workflow'
    )
    op.create_index('ix_workflow_coding_results_tenant_id', 'coding_results', ['tenant_id'], schema='workflow')
    op.create_index('ix_workflow_coding_results_queue_item_id', 'coding_results', ['queue_item_id'], schema='workflow')
    op.create_index('ix_workflow_coding_results_coded_by', 'coding_results', ['coded_by'], schema='workflow')
    op.create_index('ix_workflow_coding_results_code_category', 'coding_results', ['code_category'], schema='workflow')


def downgrade() -> None:
    op.drop_index('ix_workflow_coding_results_code_category', table_name='coding_results', schema='workflow')
    op.drop_index('ix_workflow_coding_results_coded_by', table_name='coding_results', schema='workflow')
    op.drop_index('ix_workflow_coding_results_queue_item_id', table_name='coding_results', schema='workflow')
    op.drop_index('ix_workflow_coding_results_tenant_id', table_name='coding_results', schema='workflow')
    op.drop_table('coding_results', schema='workflow')
