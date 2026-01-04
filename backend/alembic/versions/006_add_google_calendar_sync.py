"""add google calendar sync support

Revision ID: 006
Revises: 005
Create Date: 2026-01-04

Phase 11: Google Calendar Sync
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Google Calendar sync tables and columns."""

    # Create doctor_calendar_settings table
    op.create_table(
        'doctor_calendar_settings',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Relations
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Google Calendar settings
        sa.Column('google_calendar_id', sa.String(length=255), nullable=False),
        sa.Column('google_refresh_token', sa.Text(), nullable=False),  # Encrypted
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_interval_minutes', sa.Integer(), nullable=False, server_default='15'),

        # Event customization
        sa.Column('event_visibility', sa.String(length=20), nullable=False, server_default='private'),
        sa.Column('event_reminders', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Sync statistics
        sa.Column('total_synced', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_sync_error', sa.Text(), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes
    op.create_index('ix_doctor_calendar_settings_doctor_id', 'doctor_calendar_settings', ['doctor_id'], unique=True)
    op.create_index('ix_doctor_calendar_settings_sync_enabled', 'doctor_calendar_settings', ['sync_enabled'], unique=False)

    # Add calendar sync columns to appointments table
    op.add_column('appointments', sa.Column('google_calendar_event_id', sa.String(length=255), nullable=True))
    op.add_column('appointments', sa.Column('calendar_sync_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('appointments', sa.Column('calendar_sync_error', sa.Text(), nullable=True))
    op.add_column('appointments', sa.Column('last_calendar_sync_at', sa.DateTime(timezone=True), nullable=True))

    # Create index for calendar event lookups
    op.create_index('ix_appointments_google_calendar_event_id', 'appointments', ['google_calendar_event_id'], unique=False)
    op.create_index('ix_appointments_calendar_sync_status', 'appointments', ['calendar_sync_status'], unique=False)


def downgrade() -> None:
    """Remove Google Calendar sync tables and columns."""

    # Drop indexes from appointments
    op.drop_index('ix_appointments_calendar_sync_status', table_name='appointments')
    op.drop_index('ix_appointments_google_calendar_event_id', table_name='appointments')

    # Drop columns from appointments
    op.drop_column('appointments', 'last_calendar_sync_at')
    op.drop_column('appointments', 'calendar_sync_error')
    op.drop_column('appointments', 'calendar_sync_status')
    op.drop_column('appointments', 'google_calendar_event_id')

    # Drop indexes from doctor_calendar_settings
    op.drop_index('ix_doctor_calendar_settings_sync_enabled', table_name='doctor_calendar_settings')
    op.drop_index('ix_doctor_calendar_settings_doctor_id', table_name='doctor_calendar_settings')

    # Drop doctor_calendar_settings table
    op.drop_table('doctor_calendar_settings')
