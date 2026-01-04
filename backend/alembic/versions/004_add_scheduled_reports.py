"""Add scheduled_reports table for automated report generation

Revision ID: 004_add_scheduled_reports
Revises: 003_add_device_tokens
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_scheduled_reports'
down_revision: Union[str, None] = '003_add_device_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Scheduled reports table
    op.create_table(
        'scheduled_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Clinic
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),

        # Report configuration
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('report_format', sa.String(10), nullable=False, default='pdf'),

        # Schedule
        sa.Column('frequency', sa.String(20), nullable=False, default='weekly'),
        sa.Column('cron_expression', sa.String(100), nullable=True),

        # Recipients (JSON array of email addresses)
        sa.Column('recipients', postgresql.JSON, nullable=False, default={}),

        # Report parameters (JSON for flexibility)
        sa.Column('parameters', postgresql.JSON, nullable=True),

        # Execution tracking
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_status', sa.String(20), nullable=True),
        sa.Column('last_error', sa.Text, nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),

        # Metadata
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # Created by
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
    )

    # Create indexes for common queries
    op.create_index('ix_scheduled_reports_clinic_id', 'scheduled_reports', ['clinic_id'])
    op.create_index('ix_scheduled_reports_report_type', 'scheduled_reports', ['report_type'])
    op.create_index('ix_scheduled_reports_is_active', 'scheduled_reports', ['is_active'])
    op.create_index('ix_scheduled_reports_next_run_at', 'scheduled_reports', ['next_run_at'])

    # Composite index for finding due reports
    op.create_index(
        'ix_scheduled_reports_due',
        'scheduled_reports',
        ['is_active', 'next_run_at']
    )


def downgrade() -> None:
    # Drop scheduled reports table
    op.drop_index('ix_scheduled_reports_due')
    op.drop_index('ix_scheduled_reports_next_run_at')
    op.drop_index('ix_scheduled_reports_is_active')
    op.drop_index('ix_scheduled_reports_report_type')
    op.drop_index('ix_scheduled_reports_clinic_id')
    op.drop_table('scheduled_reports')
