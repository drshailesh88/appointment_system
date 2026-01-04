"""Add insurance tables for patient insurance verification

Revision ID: 006_add_insurance
Revises: 005_add_calendar_sync
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_add_insurance'
down_revision: Union[str, None] = '005_add_calendar_sync'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Patient insurances table
    op.create_table(
        'patient_insurances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Patient Reference
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),

        # Provider Information
        sa.Column('provider_name', sa.String(200), nullable=False),
        sa.Column('policy_number', sa.String(100), nullable=False),
        sa.Column('group_number', sa.String(100), nullable=True),
        sa.Column('insurance_type', sa.String(50), nullable=False, server_default='health'),
        sa.Column('plan_name', sa.String(200), nullable=True),

        # Coverage Dates
        sa.Column('coverage_start_date', sa.Date, nullable=True),
        sa.Column('coverage_end_date', sa.Date, nullable=True),

        # Policy Priority
        sa.Column('is_primary', sa.Boolean, default=True),

        # Subscriber Information
        sa.Column('subscriber_name', sa.String(200), nullable=True),
        sa.Column('subscriber_relationship', sa.String(50), nullable=True),

        # Indian Insurance - TPA Information
        sa.Column('tpa_name', sa.String(200), nullable=True),
        sa.Column('tpa_id', sa.String(100), nullable=True),
        sa.Column('cashless_enabled', sa.Boolean, default=False),

        # Network and Benefits
        sa.Column('network_type', sa.String(50), nullable=True),
        sa.Column('copay_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('deductible_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('out_of_pocket_max', sa.Numeric(10, 2), nullable=True),

        # Additional Info
        sa.Column('additional_info', postgresql.JSON, nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),
    )

    # Create indexes for patient_insurances
    op.create_index('ix_patient_insurances_patient_id', 'patient_insurances', ['patient_id'])
    op.create_index('ix_patient_insurances_provider_name', 'patient_insurances', ['provider_name'])
    op.create_index('ix_patient_insurances_policy_number', 'patient_insurances', ['policy_number'])
    op.create_index('ix_patient_insurances_is_active', 'patient_insurances', ['is_active'])

    # Composite index for finding active primary insurance
    op.create_index(
        'ix_patient_insurances_active_primary',
        'patient_insurances',
        ['patient_id', 'is_active', 'is_primary']
    )

    # Insurance verifications table
    op.create_table(
        'insurance_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Insurance Reference
        sa.Column('insurance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patient_insurances.id', ondelete='CASCADE'), nullable=False),

        # Verification Metadata
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_by', sa.String(100), nullable=True),

        # Verification Result
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('is_eligible', sa.Boolean, nullable=True),

        # Eligibility Dates
        sa.Column('eligibility_start_date', sa.Date, nullable=True),
        sa.Column('eligibility_end_date', sa.Date, nullable=True),

        # Coverage Information (JSON)
        sa.Column('coverage_details', postgresql.JSON, nullable=True),
        sa.Column('copay_info', postgresql.JSON, nullable=True),
        sa.Column('deductible_info', postgresql.JSON, nullable=True),
        sa.Column('benefits', postgresql.JSON, nullable=True),

        # Limitations and Errors
        sa.Column('limitations', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),

        # Raw Response
        sa.Column('provider_response', postgresql.JSON, nullable=True),

        # Cache Expiry
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for insurance_verifications
    op.create_index('ix_insurance_verifications_insurance_id', 'insurance_verifications', ['insurance_id'])
    op.create_index('ix_insurance_verifications_verified_at', 'insurance_verifications', ['verified_at'])
    op.create_index('ix_insurance_verifications_status', 'insurance_verifications', ['status'])
    op.create_index('ix_insurance_verifications_expires_at', 'insurance_verifications', ['expires_at'])

    # Composite index for finding valid cached verifications
    op.create_index(
        'ix_insurance_verifications_valid_cache',
        'insurance_verifications',
        ['insurance_id', 'status', 'expires_at']
    )

    # Insurance claims table (for future use)
    op.create_table(
        'insurance_claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Insurance Reference
        sa.Column('insurance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patient_insurances.id', ondelete='CASCADE'), nullable=False),

        # Claim Information
        sa.Column('claim_number', sa.String(100), nullable=False, unique=True),
        sa.Column('service_date', sa.Date, nullable=False),
        sa.Column('submission_date', sa.Date, nullable=True),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='submitted'),

        # Amounts
        sa.Column('claimed_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('approved_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('paid_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('patient_responsibility', sa.Numeric(10, 2), nullable=True),

        # Additional Information
        sa.Column('denial_reason', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
    )

    # Create indexes for insurance_claims
    op.create_index('ix_insurance_claims_claim_number', 'insurance_claims', ['claim_number'])
    op.create_index('ix_insurance_claims_status', 'insurance_claims', ['status'])


def downgrade() -> None:
    # Drop insurance_claims table
    op.drop_index('ix_insurance_claims_status')
    op.drop_index('ix_insurance_claims_claim_number')
    op.drop_table('insurance_claims')

    # Drop insurance_verifications table
    op.drop_index('ix_insurance_verifications_valid_cache')
    op.drop_index('ix_insurance_verifications_expires_at')
    op.drop_index('ix_insurance_verifications_status')
    op.drop_index('ix_insurance_verifications_verified_at')
    op.drop_index('ix_insurance_verifications_insurance_id')
    op.drop_table('insurance_verifications')

    # Drop patient_insurances table
    op.drop_index('ix_patient_insurances_active_primary')
    op.drop_index('ix_patient_insurances_is_active')
    op.drop_index('ix_patient_insurances_policy_number')
    op.drop_index('ix_patient_insurances_provider_name')
    op.drop_index('ix_patient_insurances_patient_id')
    op.drop_table('patient_insurances')
