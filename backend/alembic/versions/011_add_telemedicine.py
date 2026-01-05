"""add telemedicine tables for video consultations

Revision ID: 011
Revises: 010
Create Date: 2026-01-05

Phase 17: Telemedicine / Video Consultations
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create telemedicine tables for video consultations."""

    # Create consultations table
    op.create_table(
        'consultations',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Core relations
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Jitsi Room Details
        sa.Column('room_name', sa.String(length=255), nullable=False),
        sa.Column('room_url', sa.String(length=500), nullable=True),
        sa.Column('jwt_token', sa.Text(), nullable=True),

        # Status
        sa.Column('status', sa.String(length=50), nullable=False, server_default='scheduled'),

        # Timing
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('patient_joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('doctor_joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),

        # Recording
        sa.Column('recording_consent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recording_url', sa.String(length=500), nullable=True),
        sa.Column('recording_size_mb', sa.Integer(), nullable=True),

        # Quality Metrics
        sa.Column('patient_rating', sa.Integer(), nullable=True),
        sa.Column('doctor_rating', sa.Integer(), nullable=True),
        sa.Column('connection_quality', sa.String(length=20), nullable=True),

        # Metadata
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for consultations
    op.create_index('ix_consultations_appointment_id', 'consultations', ['appointment_id'], unique=True)
    op.create_index('ix_consultations_room_name', 'consultations', ['room_name'], unique=True)
    op.create_index('ix_consultations_status', 'consultations', ['status'], unique=False)

    # Create consultation_participants table
    op.create_table(
        'consultation_participants',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Relations
        sa.Column('consultation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='patient'),

        # Timing
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),

        # Device Info
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('connection_type', sa.String(length=20), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['consultation_id'], ['consultations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for consultation_participants
    op.create_index('ix_consultation_participants_consultation_id', 'consultation_participants', ['consultation_id'], unique=False)
    op.create_index('ix_consultation_participants_user_id', 'consultation_participants', ['user_id'], unique=False)

    # Create consultation_recordings table
    op.create_table(
        'consultation_recordings',
        # Base model fields
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Relations
        sa.Column('consultation_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Consent Tracking
        sa.Column('patient_consent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('doctor_consent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consent_text', sa.Text(), nullable=True),

        # Storage
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size_mb', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('encryption_key', sa.String(length=255), nullable=True),

        # EMR Integration
        sa.Column('uploaded_to_emr', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('emr_document_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Retention Policy
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['consultation_id'], ['consultations.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for consultation_recordings
    op.create_index('ix_consultation_recordings_consultation_id', 'consultation_recordings', ['consultation_id'], unique=True)

    # Add consultation relationship to appointments (back_populates)
    # Note: This is handled in the model definitions via back_populates


def downgrade() -> None:
    """Drop telemedicine tables."""

    # Drop consultation_recordings table
    op.drop_index('ix_consultation_recordings_consultation_id', table_name='consultation_recordings')
    op.drop_table('consultation_recordings')

    # Drop consultation_participants table
    op.drop_index('ix_consultation_participants_user_id', table_name='consultation_participants')
    op.drop_index('ix_consultation_participants_consultation_id', table_name='consultation_participants')
    op.drop_table('consultation_participants')

    # Drop consultations table
    op.drop_index('ix_consultations_status', table_name='consultations')
    op.drop_index('ix_consultations_room_name', table_name='consultations')
    op.drop_index('ix_consultations_appointment_id', table_name='consultations')
    op.drop_table('consultations')
