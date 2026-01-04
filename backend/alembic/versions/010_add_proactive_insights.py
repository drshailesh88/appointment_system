"""add proactive insights tables

Revision ID: 010
Revises: 009
Create Date: 2026-01-04

Phase 16c: Practice AI - Proactive Intelligence
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create proactive insights tables."""

    # ========================================================================
    # 1. proactive_insights table
    # ========================================================================
    op.create_table(
        'proactive_insights',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Core relations
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Insight details
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),

        # Suggested action (JSONB)
        sa.Column('suggested_action', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Metadata (JSONB)
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Expiration
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

        # User actions
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dismissed_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acted_by_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dismissed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['acted_by_id'], ['users.id'], ondelete='SET NULL'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for proactive_insights
    op.create_index('ix_proactive_insights_clinic_id', 'proactive_insights', ['clinic_id'], unique=False)
    op.create_index('ix_proactive_insights_patient_id', 'proactive_insights', ['patient_id'], unique=False)
    op.create_index('ix_proactive_insights_doctor_id', 'proactive_insights', ['doctor_id'], unique=False)
    op.create_index('ix_proactive_insights_insight_type', 'proactive_insights', ['insight_type'], unique=False)
    op.create_index('ix_proactive_insights_priority', 'proactive_insights', ['priority'], unique=False)
    op.create_index('ix_proactive_insights_expires_at', 'proactive_insights', ['expires_at'], unique=False)

    # Composite indexes for common queries
    op.create_index(
        'ix_proactive_insights_active',
        'proactive_insights',
        ['clinic_id', 'dismissed_at', 'expires_at'],
        unique=False,
    )

    # ========================================================================
    # 2. followup_schedules table
    # ========================================================================
    op.create_table(
        'followup_schedules',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Core relations
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('procedure_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Follow-up details
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='2'),

        # Notification tracking
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),

        # Completion tracking
        sa.Column('completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scheduled_appointment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['procedure_id'], ['procedures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scheduled_appointment_id'], ['appointments.id'], ondelete='SET NULL'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for followup_schedules
    op.create_index('ix_followup_schedules_clinic_id', 'followup_schedules', ['clinic_id'], unique=False)
    op.create_index('ix_followup_schedules_patient_id', 'followup_schedules', ['patient_id'], unique=False)
    op.create_index('ix_followup_schedules_doctor_id', 'followup_schedules', ['doctor_id'], unique=False)
    op.create_index('ix_followup_schedules_procedure_id', 'followup_schedules', ['procedure_id'], unique=False)
    op.create_index('ix_followup_schedules_due_date', 'followup_schedules', ['due_date'], unique=False)
    op.create_index('ix_followup_schedules_completed', 'followup_schedules', ['completed'], unique=False)

    # Composite indexes for common queries
    op.create_index(
        'ix_followup_schedules_pending',
        'followup_schedules',
        ['clinic_id', 'completed', 'due_date'],
        unique=False,
    )

    # ========================================================================
    # 3. user_digest_preferences table
    # ========================================================================
    op.create_table(
        'user_digest_preferences',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Core relations
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Preferences
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('delivery_hour', sa.Integer(), nullable=False, server_default='8'),
        sa.Column('delivery_minute', sa.Integer(), nullable=False, server_default='0'),

        # Channels (JSONB array)
        sa.Column(
            'channels',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='["push"]',
        ),

        # Content filters
        sa.Column('include_revenue', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('include_appointments', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('include_followups', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('include_schedule_gaps', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('include_waitlist', sa.Boolean(), nullable=False, server_default='true'),

        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for user_digest_preferences
    op.create_index('ix_user_digest_preferences_user_id', 'user_digest_preferences', ['user_id'], unique=True)
    op.create_index('ix_user_digest_preferences_clinic_id', 'user_digest_preferences', ['clinic_id'], unique=False)


def downgrade() -> None:
    """Drop proactive insights tables."""

    # Drop user_digest_preferences table
    op.drop_index('ix_user_digest_preferences_clinic_id', table_name='user_digest_preferences')
    op.drop_index('ix_user_digest_preferences_user_id', table_name='user_digest_preferences')
    op.drop_table('user_digest_preferences')

    # Drop followup_schedules table
    op.drop_index('ix_followup_schedules_pending', table_name='followup_schedules')
    op.drop_index('ix_followup_schedules_completed', table_name='followup_schedules')
    op.drop_index('ix_followup_schedules_due_date', table_name='followup_schedules')
    op.drop_index('ix_followup_schedules_procedure_id', table_name='followup_schedules')
    op.drop_index('ix_followup_schedules_doctor_id', table_name='followup_schedules')
    op.drop_index('ix_followup_schedules_patient_id', table_name='followup_schedules')
    op.drop_index('ix_followup_schedules_clinic_id', table_name='followup_schedules')
    op.drop_table('followup_schedules')

    # Drop proactive_insights table
    op.drop_index('ix_proactive_insights_active', table_name='proactive_insights')
    op.drop_index('ix_proactive_insights_expires_at', table_name='proactive_insights')
    op.drop_index('ix_proactive_insights_priority', table_name='proactive_insights')
    op.drop_index('ix_proactive_insights_insight_type', table_name='proactive_insights')
    op.drop_index('ix_proactive_insights_doctor_id', table_name='proactive_insights')
    op.drop_index('ix_proactive_insights_patient_id', table_name='proactive_insights')
    op.drop_index('ix_proactive_insights_clinic_id', table_name='proactive_insights')
    op.drop_table('proactive_insights')
