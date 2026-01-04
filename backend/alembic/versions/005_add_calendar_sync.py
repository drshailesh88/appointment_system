"""Add calendar_connections and calendar_sync_logs tables for Google Calendar integration

Revision ID: 005_add_calendar_sync
Revises: 004_add_scheduled_reports
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_add_calendar_sync'
down_revision: Union[str, None] = '004_add_scheduled_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Calendar connections table
    op.create_table(
        'calendar_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Relations
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),

        # Google Calendar Info
        sa.Column('google_calendar_id', sa.String(255), nullable=False, default='primary'),
        sa.Column('calendar_name', sa.String(255), nullable=False),
        sa.Column('calendar_timezone', sa.String(100), nullable=False, default='Asia/Kolkata'),

        # OAuth2 Credentials
        sa.Column('access_token', sa.Text, nullable=False),
        sa.Column('refresh_token', sa.Text, nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('token_scope', sa.Text, nullable=True),

        # Sync Settings
        sa.Column('sync_direction', sa.String(30), nullable=False, default='two_way'),
        sa.Column('conflict_resolution', sa.String(20), nullable=False, default='latest_wins'),
        sa.Column('auto_sync_enabled', sa.Boolean, default=True),
        sa.Column('sync_interval_minutes', sa.Integer, default=15),

        # Color mappings (JSON)
        sa.Column('color_mappings', postgresql.JSONB, nullable=True),

        # Sync State
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(20), nullable=True),
        sa.Column('last_sync_error', sa.Text, nullable=True),
        sa.Column('sync_token', sa.Text, nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),
    )

    # Create indexes for calendar_connections
    op.create_index('ix_calendar_connections_user_id', 'calendar_connections', ['user_id'])
    op.create_index('ix_calendar_connections_clinic_id', 'calendar_connections', ['clinic_id'])
    op.create_index('ix_calendar_connections_is_active', 'calendar_connections', ['is_active'])

    # Composite index for finding active connections
    op.create_index(
        'ix_calendar_connections_active_sync',
        'calendar_connections',
        ['is_active', 'auto_sync_enabled']
    )

    # Calendar sync logs table
    op.create_table(
        'calendar_sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Relations
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calendar_connections.id', ondelete='CASCADE'), nullable=False),

        # Sync Info
        sa.Column('sync_direction', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

        # Statistics
        sa.Column('events_synced', sa.Integer, default=0),
        sa.Column('events_created', sa.Integer, default=0),
        sa.Column('events_updated', sa.Integer, default=0),
        sa.Column('events_deleted', sa.Integer, default=0),
        sa.Column('conflicts_found', sa.Integer, default=0),
        sa.Column('conflicts_resolved', sa.Integer, default=0),

        # Error handling
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_details', postgresql.JSONB, nullable=True),

        # Detailed sync info
        sa.Column('sync_details', postgresql.JSONB, nullable=True),
    )

    # Create indexes for calendar_sync_logs
    op.create_index('ix_calendar_sync_logs_connection_id', 'calendar_sync_logs', ['connection_id'])
    op.create_index('ix_calendar_sync_logs_status', 'calendar_sync_logs', ['status'])
    op.create_index('ix_calendar_sync_logs_started_at', 'calendar_sync_logs', ['started_at'])

    # Composite index for recent sync logs
    op.create_index(
        'ix_calendar_sync_logs_recent',
        'calendar_sync_logs',
        ['connection_id', 'started_at']
    )


def downgrade() -> None:
    # Drop calendar sync logs table
    op.drop_index('ix_calendar_sync_logs_recent')
    op.drop_index('ix_calendar_sync_logs_started_at')
    op.drop_index('ix_calendar_sync_logs_status')
    op.drop_index('ix_calendar_sync_logs_connection_id')
    op.drop_table('calendar_sync_logs')

    # Drop calendar connections table
    op.drop_index('ix_calendar_connections_active_sync')
    op.drop_index('ix_calendar_connections_is_active')
    op.drop_index('ix_calendar_connections_clinic_id')
    op.drop_index('ix_calendar_connections_user_id')
    op.drop_table('calendar_connections')
