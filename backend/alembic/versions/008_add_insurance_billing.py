"""add insurance and billing tables

Revision ID: 008
Revises: 007
Create Date: 2026-01-04 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create insurance_companies table
    op.create_table(
        'insurance_companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('contact_address', sa.Text(), nullable=True),
        sa.Column('tpa_name', sa.String(length=200), nullable=True),
        sa.Column('tpa_email', sa.String(length=255), nullable=True),
        sa.Column('tpa_phone', sa.String(length=20), nullable=True),
        sa.Column('claim_submission_url', sa.String(length=500), nullable=True),
        sa.Column('claim_submission_email', sa.String(length=255), nullable=True),
        sa.Column('cashless_available', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('preauth_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('preauth_threshold', sa.Numeric(10, 2), nullable=True),
        sa.Column('network_type', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('claim_process_notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_insurance_companies_code', 'insurance_companies', ['code'])
    op.create_index('ix_insurance_companies_is_active', 'insurance_companies', ['is_active'])
    op.create_index('ix_insurance_companies_name', 'insurance_companies', ['name'])

    # Create patient_insurances table
    op.create_table(
        'patient_insurances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insurance_company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_number', sa.String(length=100), nullable=False),
        sa.Column('group_number', sa.String(length=100), nullable=True),
        sa.Column('member_id', sa.String(length=100), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_to', sa.Date(), nullable=False),
        sa.Column('coverage_type', sa.String(length=50), nullable=False, server_default='individual'),
        sa.Column('sum_insured', sa.Numeric(12, 2), nullable=False),
        sa.Column('copay_percentage', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
        sa.Column('deductible_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('policyholder_name', sa.String(length=200), nullable=True),
        sa.Column('policyholder_relationship', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('verification_status', sa.String(length=20), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['insurance_company_id'], ['insurance_companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_patient_insurances_patient_id', 'patient_insurances', ['patient_id'])
    op.create_index('ix_patient_insurances_insurance_company_id', 'patient_insurances', ['insurance_company_id'])
    op.create_index('ix_patient_insurances_policy_number', 'patient_insurances', ['policy_number'])
    op.create_index('ix_patient_insurances_is_active', 'patient_insurances', ['is_active'])

    # Create preauthorizations table
    op.create_table(
        'preauthorizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_insurance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insurance_company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('procedure_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('auth_number', sa.String(length=100), nullable=True),
        sa.Column('internal_ref_number', sa.String(length=100), nullable=False),
        sa.Column('procedure_name', sa.String(length=500), nullable=False),
        sa.Column('procedure_code', sa.String(length=50), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('requested_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('approved_amount', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('requested_date', sa.Date(), nullable=False),
        sa.Column('planned_procedure_date', sa.Date(), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('rejection_code', sa.String(length=50), nullable=True),
        sa.Column('documents_submitted', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tpa_notes', sa.Text(), nullable=True),
        sa.Column('requested_by', sa.String(length=200), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['patient_insurance_id'], ['patient_insurances.id'], ),
        sa.ForeignKeyConstraint(['insurance_company_id'], ['insurance_companies.id'], ),
        sa.ForeignKeyConstraint(['procedure_id'], ['procedures.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('internal_ref_number')
    )
    op.create_index('ix_preauthorizations_patient_id', 'preauthorizations', ['patient_id'])
    op.create_index('ix_preauthorizations_patient_insurance_id', 'preauthorizations', ['patient_insurance_id'])
    op.create_index('ix_preauthorizations_insurance_company_id', 'preauthorizations', ['insurance_company_id'])
    op.create_index('ix_preauthorizations_auth_number', 'preauthorizations', ['auth_number'])
    op.create_index('ix_preauthorizations_internal_ref_number', 'preauthorizations', ['internal_ref_number'])
    op.create_index('ix_preauthorizations_status', 'preauthorizations', ['status'])

    # Create insurance_claims table
    op.create_table(
        'insurance_claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_insurance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insurance_company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('preauthorization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('claim_number', sa.String(length=100), nullable=True),
        sa.Column('internal_claim_number', sa.String(length=100), nullable=False),
        sa.Column('claimed_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('approved_amount', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('settled_amount', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('patient_liability', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('rejection_code', sa.String(length=50), nullable=True),
        sa.Column('appeal_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('appeal_notes', sa.Text(), nullable=True),
        sa.Column('documents_submitted', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tpa_reference_number', sa.String(length=100), nullable=True),
        sa.Column('processing_notes', sa.Text(), nullable=True),
        sa.Column('submitted_by', sa.String(length=200), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['patient_insurance_id'], ['patient_insurances.id'], ),
        sa.ForeignKeyConstraint(['insurance_company_id'], ['insurance_companies.id'], ),
        sa.ForeignKeyConstraint(['preauthorization_id'], ['preauthorizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('internal_claim_number')
    )
    op.create_index('ix_insurance_claims_patient_id', 'insurance_claims', ['patient_id'])
    op.create_index('ix_insurance_claims_invoice_id', 'insurance_claims', ['invoice_id'])
    op.create_index('ix_insurance_claims_patient_insurance_id', 'insurance_claims', ['patient_insurance_id'])
    op.create_index('ix_insurance_claims_insurance_company_id', 'insurance_claims', ['insurance_company_id'])
    op.create_index('ix_insurance_claims_claim_number', 'insurance_claims', ['claim_number'])
    op.create_index('ix_insurance_claims_internal_claim_number', 'insurance_claims', ['internal_claim_number'])
    op.create_index('ix_insurance_claims_status', 'insurance_claims', ['status'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('ix_insurance_claims_status', table_name='insurance_claims')
    op.drop_index('ix_insurance_claims_internal_claim_number', table_name='insurance_claims')
    op.drop_index('ix_insurance_claims_claim_number', table_name='insurance_claims')
    op.drop_index('ix_insurance_claims_insurance_company_id', table_name='insurance_claims')
    op.drop_index('ix_insurance_claims_patient_insurance_id', table_name='insurance_claims')
    op.drop_index('ix_insurance_claims_invoice_id', table_name='insurance_claims')
    op.drop_index('ix_insurance_claims_patient_id', table_name='insurance_claims')
    op.drop_table('insurance_claims')

    op.drop_index('ix_preauthorizations_status', table_name='preauthorizations')
    op.drop_index('ix_preauthorizations_internal_ref_number', table_name='preauthorizations')
    op.drop_index('ix_preauthorizations_auth_number', table_name='preauthorizations')
    op.drop_index('ix_preauthorizations_insurance_company_id', table_name='preauthorizations')
    op.drop_index('ix_preauthorizations_patient_insurance_id', table_name='preauthorizations')
    op.drop_index('ix_preauthorizations_patient_id', table_name='preauthorizations')
    op.drop_table('preauthorizations')

    op.drop_index('ix_patient_insurances_is_active', table_name='patient_insurances')
    op.drop_index('ix_patient_insurances_policy_number', table_name='patient_insurances')
    op.drop_index('ix_patient_insurances_insurance_company_id', table_name='patient_insurances')
    op.drop_index('ix_patient_insurances_patient_id', table_name='patient_insurances')
    op.drop_table('patient_insurances')

    op.drop_index('ix_insurance_companies_name', table_name='insurance_companies')
    op.drop_index('ix_insurance_companies_is_active', table_name='insurance_companies')
    op.drop_index('ix_insurance_companies_code', table_name='insurance_companies')
    op.drop_table('insurance_companies')
