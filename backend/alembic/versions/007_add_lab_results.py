"""Add lab results tables for lab integration

Revision ID: 007_add_lab_results
Revises: 006_add_insurance
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_add_lab_results'
down_revision: Union[str, None] = '006_add_insurance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Lab Orders table
    op.create_table(
        'lab_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Relations
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.id'), nullable=True),

        # Order details
        sa.Column('order_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tests_ordered', postgresql.JSONB, nullable=False),  # Array of test names
        sa.Column('priority', sa.String(20), default='routine'),  # routine, urgent, stat
        sa.Column('status', sa.String(20), default='ordered'),  # ordered, sample_collected, in_progress, completed, cancelled

        # Clinical information
        sa.Column('clinical_notes', sa.Text, nullable=True),
        sa.Column('diagnosis_codes', postgresql.JSONB, nullable=True),  # Array of ICD-10 codes

        # Sample & timing
        sa.Column('sample_collected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expected_completion', sa.DateTime(timezone=True), nullable=True),

        # External lab integration
        sa.Column('lab_provider', sa.String(100), nullable=True),
        sa.Column('lab_order_id', sa.String(100), nullable=True),

        # Metadata
        sa.Column('metadata', postgresql.JSONB, nullable=True),
    )

    # Indexes for lab_orders
    op.create_index('ix_lab_orders_patient_id', 'lab_orders', ['patient_id'])
    op.create_index('ix_lab_orders_doctor_id', 'lab_orders', ['doctor_id'])
    op.create_index('ix_lab_orders_appointment_id', 'lab_orders', ['appointment_id'])
    op.create_index('ix_lab_orders_order_date', 'lab_orders', ['order_date'])
    op.create_index('ix_lab_orders_status', 'lab_orders', ['status'])
    op.create_index('ix_lab_orders_lab_order_id', 'lab_orders', ['lab_order_id'])

    # Lab Results table
    op.create_table(
        'lab_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Relation
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_orders.id'), nullable=False),

        # Test identification
        sa.Column('test_name', sa.String(200), nullable=False),
        sa.Column('test_code', sa.String(50), nullable=True),
        sa.Column('test_category', sa.String(100), nullable=True),  # CBC, LFT, KFT, etc.

        # Result value
        sa.Column('value', sa.Text, nullable=False),  # Can be text or numeric
        sa.Column('value_numeric', sa.Float, nullable=True),  # For trending
        sa.Column('unit', sa.String(50), nullable=True),

        # Reference ranges
        sa.Column('reference_range_min', sa.Float, nullable=True),
        sa.Column('reference_range_max', sa.Float, nullable=True),
        sa.Column('reference_range_text', sa.String(200), nullable=True),

        # Abnormality flags
        sa.Column('is_abnormal', sa.Boolean, default=False),
        sa.Column('abnormal_flag', sa.String(10), nullable=True),  # H, L, HH, LL, A

        # Status & timing
        sa.Column('status', sa.String(20), default='final'),  # pending, preliminary, final, corrected
        sa.Column('result_date', sa.DateTime(timezone=True), nullable=True),

        # Additional info
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('performed_by', sa.String(100), nullable=True),
        sa.Column('methodology', sa.String(100), nullable=True),

        # Metadata
        sa.Column('metadata', postgresql.JSONB, nullable=True),
    )

    # Indexes for lab_results
    op.create_index('ix_lab_results_order_id', 'lab_results', ['order_id'])
    op.create_index('ix_lab_results_test_name', 'lab_results', ['test_name'])
    op.create_index('ix_lab_results_is_abnormal', 'lab_results', ['is_abnormal'])

    # Composite index for patient result history
    op.create_index(
        'ix_lab_results_patient_history',
        'lab_results',
        ['order_id', 'test_name', 'result_date']
    )

    # Lab Reports table
    op.create_table(
        'lab_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Relation
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lab_orders.id'), nullable=False),

        # Report details
        sa.Column('report_type', sa.String(20), nullable=False),  # pdf, hl7, text
        sa.Column('file_path', sa.Text, nullable=True),
        sa.Column('file_url', sa.Text, nullable=True),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),

        # Parsed content
        sa.Column('parsed_data', postgresql.JSONB, nullable=True),
        sa.Column('raw_content', sa.Text, nullable=True),

        # Timing
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Indexes for lab_reports
    op.create_index('ix_lab_reports_order_id', 'lab_reports', ['order_id'])


def downgrade() -> None:
    # Drop lab_reports
    op.drop_index('ix_lab_reports_order_id')
    op.drop_table('lab_reports')

    # Drop lab_results
    op.drop_index('ix_lab_results_patient_history')
    op.drop_index('ix_lab_results_is_abnormal')
    op.drop_index('ix_lab_results_test_name')
    op.drop_index('ix_lab_results_order_id')
    op.drop_table('lab_results')

    # Drop lab_orders
    op.drop_index('ix_lab_orders_lab_order_id')
    op.drop_index('ix_lab_orders_status')
    op.drop_index('ix_lab_orders_order_date')
    op.drop_index('ix_lab_orders_appointment_id')
    op.drop_index('ix_lab_orders_doctor_id')
    op.drop_index('ix_lab_orders_patient_id')
    op.drop_table('lab_orders')
