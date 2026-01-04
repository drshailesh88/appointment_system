"""Add waitlist table for queue management

Revision ID: 002_add_waitlist
Revises: 001_initial
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_waitlist'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add clinic_id to appointments for easier querying
    op.add_column(
        'appointments',
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_appointments_clinic_id',
        'appointments',
        'clinics',
        ['clinic_id'],
        ['id']
    )
    op.create_index('ix_appointments_clinic_id', 'appointments', ['clinic_id'])

    # Waitlist table
    op.create_table(
        'waitlist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Clinic and doctor
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=True),

        # Patient info
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id'), nullable=True),
        sa.Column('patient_name', sa.String(200), nullable=False),
        sa.Column('patient_phone', sa.String(20), nullable=False),

        # Preferred dates
        sa.Column('preferred_date', sa.Date, nullable=False),
        sa.Column('alternate_date', sa.Date, nullable=True),
        sa.Column('preferred_time_slot', sa.String(50), nullable=True),

        # Priority and status
        sa.Column('priority', sa.String(20), default='normal'),
        sa.Column('status', sa.String(20), default='waiting'),
        sa.Column('queue_position', sa.Integer, default=0),

        # Reason for visit
        sa.Column('chief_complaint', sa.Text, nullable=True),
        sa.Column('is_emergency', sa.Boolean, default=False),

        # Notification preferences
        sa.Column('notification_channel', sa.String(20), default='sms'),
        sa.Column('notification_count', sa.Integer, default=0),
        sa.Column('last_notified_at', sa.DateTime(timezone=True), nullable=True),

        # Booking tracking
        sa.Column('offered_slot_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('slot_offer_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('booked_appointment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.id'), nullable=True),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),
    )

    # Create indexes for common queries
    op.create_index('ix_waitlist_clinic_id', 'waitlist', ['clinic_id'])
    op.create_index('ix_waitlist_doctor_id', 'waitlist', ['doctor_id'])
    op.create_index('ix_waitlist_patient_phone', 'waitlist', ['patient_phone'])
    op.create_index('ix_waitlist_preferred_date', 'waitlist', ['preferred_date'])
    op.create_index('ix_waitlist_status', 'waitlist', ['status'])
    op.create_index('ix_waitlist_priority', 'waitlist', ['priority'])

    # Composite index for queue ordering
    op.create_index(
        'ix_waitlist_queue_order',
        'waitlist',
        ['clinic_id', 'preferred_date', 'is_emergency', 'priority', 'queue_position']
    )


def downgrade() -> None:
    # Drop waitlist table
    op.drop_index('ix_waitlist_queue_order')
    op.drop_index('ix_waitlist_priority')
    op.drop_index('ix_waitlist_status')
    op.drop_index('ix_waitlist_preferred_date')
    op.drop_index('ix_waitlist_patient_phone')
    op.drop_index('ix_waitlist_doctor_id')
    op.drop_index('ix_waitlist_clinic_id')
    op.drop_table('waitlist')

    # Remove clinic_id from appointments
    op.drop_index('ix_appointments_clinic_id')
    op.drop_constraint('fk_appointments_clinic_id', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'clinic_id')
