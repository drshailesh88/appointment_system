"""add procedures table for intervention tracking

Revision ID: 004
Revises: 003
Create Date: 2026-01-04

Phase 9: Procedure & Intervention Tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create procedures table for tracking medical procedures across all specialties."""
    op.create_table(
        'procedures',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Core relations
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Procedure classification
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('procedure_type', sa.String(length=100), nullable=False),
        sa.Column('sub_type', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Timing
        sa.Column('performed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),

        # Outcome & Severity
        sa.Column('outcome', sa.String(length=30), nullable=False, server_default='successful'),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='minor'),

        # Clinical details
        sa.Column('findings', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('complications', sa.Text(), nullable=True),

        # Consumables & custom fields (JSONB)
        sa.Column('consumables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Billing
        sa.Column('billing_code', sa.String(length=20), nullable=True),
        sa.Column('cpt_code', sa.String(length=20), nullable=True),
        sa.Column('icd_code', sa.String(length=20), nullable=True),
        sa.Column('is_billable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('billed_amount', sa.Numeric(precision=10, scale=2), nullable=True),

        # Location
        sa.Column('location', sa.String(length=100), nullable=True),

        # Assistants
        sa.Column('assistant_doctors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Follow-up
        sa.Column('requires_followup', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('followup_notes', sa.Text(), nullable=True),

        # EMR integration
        sa.Column('emr_procedure_id', sa.String(length=50), nullable=True),
        sa.Column('synced_to_emr', sa.Boolean(), nullable=False, server_default='false'),

        # Clinic relation (for multi-tenancy)
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for common queries
    op.create_index('ix_procedures_patient_id', 'procedures', ['patient_id'], unique=False)
    op.create_index('ix_procedures_doctor_id', 'procedures', ['doctor_id'], unique=False)
    op.create_index('ix_procedures_appointment_id', 'procedures', ['appointment_id'], unique=False)
    op.create_index('ix_procedures_clinic_id', 'procedures', ['clinic_id'], unique=False)
    op.create_index('ix_procedures_category', 'procedures', ['category'], unique=False)
    op.create_index('ix_procedures_procedure_type', 'procedures', ['procedure_type'], unique=False)
    op.create_index('ix_procedures_performed_at', 'procedures', ['performed_at'], unique=False)
    op.create_index('ix_procedures_emr_procedure_id', 'procedures', ['emr_procedure_id'], unique=False)

    # Composite indexes for analytics queries
    op.create_index(
        'ix_procedures_clinic_category_performed',
        'procedures',
        ['clinic_id', 'category', 'performed_at'],
        unique=False,
    )
    op.create_index(
        'ix_procedures_doctor_performed',
        'procedures',
        ['doctor_id', 'performed_at'],
        unique=False,
    )


def downgrade() -> None:
    """Drop procedures table."""
    # Drop composite indexes
    op.drop_index('ix_procedures_doctor_performed', table_name='procedures')
    op.drop_index('ix_procedures_clinic_category_performed', table_name='procedures')

    # Drop single-column indexes
    op.drop_index('ix_procedures_emr_procedure_id', table_name='procedures')
    op.drop_index('ix_procedures_performed_at', table_name='procedures')
    op.drop_index('ix_procedures_procedure_type', table_name='procedures')
    op.drop_index('ix_procedures_category', table_name='procedures')
    op.drop_index('ix_procedures_clinic_id', table_name='procedures')
    op.drop_index('ix_procedures_appointment_id', table_name='procedures')
    op.drop_index('ix_procedures_doctor_id', table_name='procedures')
    op.drop_index('ix_procedures_patient_id', table_name='procedures')

    # Drop table
    op.drop_table('procedures')
