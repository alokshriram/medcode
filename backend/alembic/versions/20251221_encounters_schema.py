"""Add encounters schema for HL7 ingestion and clinical data aggregation

Revision ID: 20251221_encounters
Revises: 224ba6bb447d
Create Date: 2025-12-21

See: docs/pdd/PDD-001-hl7-ingestion-and-codable-encounters.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251221_encounters'
down_revision: Union[str, None] = '224ba6bb447d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create encounters schema
    op.execute('CREATE SCHEMA IF NOT EXISTS encounters')

    # hl7_messages - Raw message storage for audit
    op.create_table(
        'hl7_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('message_control_id', sa.String(length=100), nullable=False),
        sa.Column('message_type', sa.String(length=10), nullable=False),
        sa.Column('event_type', sa.String(length=10), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=False),
        sa.Column('file_source', sa.String(length=500), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='encounters'
    )
    op.create_index('ix_encounters_hl7_messages_message_control_id', 'hl7_messages', ['message_control_id'], schema='encounters')
    op.create_index('ix_encounters_hl7_messages_message_type', 'hl7_messages', ['message_type'], schema='encounters')
    op.create_index('ix_encounters_hl7_messages_processing_status', 'hl7_messages', ['processing_status'], schema='encounters')

    # patients - Patient demographics
    op.create_table(
        'patients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('mrn', sa.String(length=100), nullable=False),
        sa.Column('name_family', sa.String(length=255), nullable=True),
        sa.Column('name_given', sa.String(length=255), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mrn'),
        schema='encounters'
    )
    op.create_index('ix_encounters_patients_mrn', 'patients', ['mrn'], schema='encounters')

    # encounters - Core linking entity
    op.create_table(
        'encounters',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('visit_number', sa.String(length=100), nullable=False),
        sa.Column('encounter_type', sa.String(length=50), nullable=True),
        sa.Column('service_line', sa.String(length=100), nullable=True),
        sa.Column('payer_identifier', sa.String(length=100), nullable=True),
        sa.Column('admit_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('discharge_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admitting_diagnosis', sa.Text(), nullable=True),
        sa.Column('discharge_disposition', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('ready_to_code_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ready_to_code_reason', sa.String(length=50), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['encounters.patients.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('visit_number'),
        schema='encounters'
    )
    op.create_index('ix_encounters_encounters_patient_id', 'encounters', ['patient_id'], schema='encounters')
    op.create_index('ix_encounters_encounters_visit_number', 'encounters', ['visit_number'], schema='encounters')
    op.create_index('ix_encounters_encounters_status', 'encounters', ['status'], schema='encounters')
    op.create_index('ix_encounters_encounters_service_line', 'encounters', ['service_line'], schema='encounters')

    # diagnoses - DG1 segment data
    op.create_table(
        'diagnoses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('hl7_message_id', sa.UUID(), nullable=True),
        sa.Column('set_id', sa.Integer(), nullable=True),
        sa.Column('diagnosis_code', sa.String(length=20), nullable=True),
        sa.Column('diagnosis_description', sa.Text(), nullable=True),
        sa.Column('diagnosis_type', sa.String(length=50), nullable=True),
        sa.Column('coding_method', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.encounters.id'], ),
        sa.ForeignKeyConstraint(['hl7_message_id'], ['encounters.hl7_messages.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='encounters'
    )
    op.create_index('ix_encounters_diagnoses_encounter_id', 'diagnoses', ['encounter_id'], schema='encounters')
    op.create_index('ix_encounters_diagnoses_diagnosis_code', 'diagnoses', ['diagnosis_code'], schema='encounters')

    # procedures - PR1 segment data
    op.create_table(
        'procedures',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('hl7_message_id', sa.UUID(), nullable=True),
        sa.Column('set_id', sa.Integer(), nullable=True),
        sa.Column('procedure_code', sa.String(length=20), nullable=True),
        sa.Column('procedure_description', sa.Text(), nullable=True),
        sa.Column('procedure_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('performing_physician', sa.String(length=255), nullable=True),
        sa.Column('performing_physician_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.encounters.id'], ),
        sa.ForeignKeyConstraint(['hl7_message_id'], ['encounters.hl7_messages.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='encounters'
    )
    op.create_index('ix_encounters_procedures_encounter_id', 'procedures', ['encounter_id'], schema='encounters')
    op.create_index('ix_encounters_procedures_procedure_code', 'procedures', ['procedure_code'], schema='encounters')

    # observations - OBX segment data
    op.create_table(
        'observations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('hl7_message_id', sa.UUID(), nullable=True),
        sa.Column('set_id', sa.Integer(), nullable=True),
        sa.Column('observation_identifier', sa.String(length=100), nullable=True),
        sa.Column('observation_value', sa.Text(), nullable=True),
        sa.Column('units', sa.String(length=50), nullable=True),
        sa.Column('reference_range', sa.String(length=100), nullable=True),
        sa.Column('abnormal_flags', sa.String(length=20), nullable=True),
        sa.Column('observation_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_status', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.encounters.id'], ),
        sa.ForeignKeyConstraint(['hl7_message_id'], ['encounters.hl7_messages.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='encounters'
    )
    op.create_index('ix_encounters_observations_encounter_id', 'observations', ['encounter_id'], schema='encounters')
    op.create_index('ix_encounters_observations_observation_identifier', 'observations', ['observation_identifier'], schema='encounters')

    # orders - ORC/OBR segment data
    op.create_table(
        'orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('hl7_message_id', sa.UUID(), nullable=True),
        sa.Column('order_control', sa.String(length=10), nullable=True),
        sa.Column('placer_order_number', sa.String(length=100), nullable=True),
        sa.Column('filler_order_number', sa.String(length=100), nullable=True),
        sa.Column('order_status', sa.String(length=20), nullable=True),
        sa.Column('order_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ordering_provider', sa.String(length=255), nullable=True),
        sa.Column('order_type', sa.String(length=100), nullable=True),
        sa.Column('diagnostic_service_section', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.encounters.id'], ),
        sa.ForeignKeyConstraint(['hl7_message_id'], ['encounters.hl7_messages.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='encounters'
    )
    op.create_index('ix_encounters_orders_encounter_id', 'orders', ['encounter_id'], schema='encounters')
    op.create_index('ix_encounters_orders_placer_order_number', 'orders', ['placer_order_number'], schema='encounters')
    op.create_index('ix_encounters_orders_filler_order_number', 'orders', ['filler_order_number'], schema='encounters')

    # documents - MDM message data
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('hl7_message_id', sa.UUID(), nullable=True),
        sa.Column('document_type', sa.String(length=100), nullable=True),
        sa.Column('document_status', sa.String(length=50), nullable=True),
        sa.Column('origination_datetime', sa.DateTime(timezone=True), nullable=True),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.encounters.id'], ),
        sa.ForeignKeyConstraint(['hl7_message_id'], ['encounters.hl7_messages.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='encounters'
    )
    op.create_index('ix_encounters_documents_encounter_id', 'documents', ['encounter_id'], schema='encounters')
    op.create_index('ix_encounters_documents_document_type', 'documents', ['document_type'], schema='encounters')

    # service_line_rules - Configurable rules for service line derivation
    op.create_table(
        'service_line_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('match_pattern', sa.String(length=255), nullable=False),
        sa.Column('service_line', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='encounters'
    )

    # Insert default service line rules
    op.execute("""
        INSERT INTO encounters.service_line_rules (id, rule_type, match_pattern, service_line, priority) VALUES
        (gen_random_uuid(), 'diagnostic_section', 'RAD', 'Radiology', 1),
        (gen_random_uuid(), 'diagnostic_section', 'LAB', 'Laboratory', 1),
        (gen_random_uuid(), 'diagnostic_section', 'CARD', 'Cardiology', 1),
        (gen_random_uuid(), 'diagnostic_section', 'PATH', 'Pathology', 1),
        (gen_random_uuid(), 'procedure_range', '70000-79999', 'Radiology', 2),
        (gen_random_uuid(), 'procedure_range', '80000-89999', 'Laboratory', 2),
        (gen_random_uuid(), 'procedure_range', '90000-99999', 'E&M/Medicine', 2),
        (gen_random_uuid(), 'procedure_range', '10000-69999', 'Surgery', 2),
        (gen_random_uuid(), 'default', '*', 'Unassigned', 100)
    """)


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting foreign keys)
    op.drop_index('ix_encounters_documents_document_type', table_name='documents', schema='encounters')
    op.drop_index('ix_encounters_documents_encounter_id', table_name='documents', schema='encounters')
    op.drop_table('documents', schema='encounters')

    op.drop_index('ix_encounters_orders_filler_order_number', table_name='orders', schema='encounters')
    op.drop_index('ix_encounters_orders_placer_order_number', table_name='orders', schema='encounters')
    op.drop_index('ix_encounters_orders_encounter_id', table_name='orders', schema='encounters')
    op.drop_table('orders', schema='encounters')

    op.drop_index('ix_encounters_observations_observation_identifier', table_name='observations', schema='encounters')
    op.drop_index('ix_encounters_observations_encounter_id', table_name='observations', schema='encounters')
    op.drop_table('observations', schema='encounters')

    op.drop_index('ix_encounters_procedures_procedure_code', table_name='procedures', schema='encounters')
    op.drop_index('ix_encounters_procedures_encounter_id', table_name='procedures', schema='encounters')
    op.drop_table('procedures', schema='encounters')

    op.drop_index('ix_encounters_diagnoses_diagnosis_code', table_name='diagnoses', schema='encounters')
    op.drop_index('ix_encounters_diagnoses_encounter_id', table_name='diagnoses', schema='encounters')
    op.drop_table('diagnoses', schema='encounters')

    op.drop_table('service_line_rules', schema='encounters')

    op.drop_index('ix_encounters_encounters_service_line', table_name='encounters', schema='encounters')
    op.drop_index('ix_encounters_encounters_status', table_name='encounters', schema='encounters')
    op.drop_index('ix_encounters_encounters_visit_number', table_name='encounters', schema='encounters')
    op.drop_index('ix_encounters_encounters_patient_id', table_name='encounters', schema='encounters')
    op.drop_table('encounters', schema='encounters')

    op.drop_index('ix_encounters_patients_mrn', table_name='patients', schema='encounters')
    op.drop_table('patients', schema='encounters')

    op.drop_index('ix_encounters_hl7_messages_processing_status', table_name='hl7_messages', schema='encounters')
    op.drop_index('ix_encounters_hl7_messages_message_type', table_name='hl7_messages', schema='encounters')
    op.drop_index('ix_encounters_hl7_messages_message_control_id', table_name='hl7_messages', schema='encounters')
    op.drop_table('hl7_messages', schema='encounters')

    # Drop schema
    op.execute('DROP SCHEMA IF EXISTS encounters')
