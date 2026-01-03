"""Initial database migration

Revision ID: 001
Revises:
Create Date: 2026-01-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clinics table
    op.create_table(
        'clinics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('pincode', sa.String(10), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('gst_number', sa.String(20), nullable=True),
        sa.Column('registration_number', sa.String(50), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(10), default='#1976D2'),
        sa.Column('subscription_tier', sa.String(20), default='free'),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(50), default='Asia/Kolkata'),
        sa.Column('currency', sa.String(3), default='INR'),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    op.create_index('ix_clinics_slug', 'clinics', ['slug'])

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('phone', sa.String(20), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('role', sa.String(20), default='receptionist'),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refresh_token', sa.String(500), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_phone', 'users', ['phone'])
    op.create_index('ix_users_clinic_id', 'users', ['clinic_id'])

    # Doctors table
    op.create_table(
        'doctors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('specialization', sa.String(100), nullable=True),
        sa.Column('qualification', sa.String(500), nullable=True),
        sa.Column('registration_number', sa.String(50), nullable=True),
        sa.Column('experience_years', sa.Integer, nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('consultation_fee', sa.Numeric(10, 2), default=500.00),
        sa.Column('followup_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('slot_duration', sa.Integer, default=15),
        sa.Column('working_hours', postgresql.JSONB, nullable=True),
        sa.Column('break_slots', postgresql.JSONB, nullable=True),
        sa.Column('bio', sa.Text, nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('languages', postgresql.JSONB, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('accepting_new_patients', sa.Boolean, default=True),
    )
    op.create_index('ix_doctors_clinic_id', 'doctors', ['clinic_id'])

    # Patients table
    op.create_table(
        'patients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('date_of_birth', sa.Date, nullable=True),
        sa.Column('gender', sa.String(1), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('pincode', sa.String(10), nullable=True),
        sa.Column('aadhaar_last_four', sa.String(4), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('emr_patient_id', sa.String(50), nullable=True),
        sa.Column('blood_group', sa.String(5), nullable=True),
        sa.Column('allergies', sa.Text, nullable=True),
        sa.Column('emergency_contact_name', sa.String(200), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(20), nullable=True),
        sa.Column('preferred_language', sa.String(10), default='en'),
        sa.Column('sms_consent', sa.Boolean, default=True),
        sa.Column('whatsapp_consent', sa.Boolean, default=True),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    op.create_index('ix_patients_clinic_id', 'patients', ['clinic_id'])
    op.create_index('ix_patients_phone', 'patients', ['phone'])
    op.create_index('ix_patients_emr_patient_id', 'patients', ['emr_patient_id'])

    # Services table
    op.create_table(
        'services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(20), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=0.00),
        sa.Column('duration_minutes', sa.Integer, default=30),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    op.create_index('ix_services_clinic_id', 'services', ['clinic_id'])
    op.create_index('ix_services_code', 'services', ['code'])

    # Appointments table
    op.create_table(
        'appointments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer, default=15),
        sa.Column('status', sa.String(20), default='scheduled'),
        sa.Column('appointment_type', sa.String(20), default='new_consultation'),
        sa.Column('booking_source', sa.String(20), default='walk_in'),
        sa.Column('chief_complaint', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('token_number', sa.Integer, nullable=True),
        sa.Column('check_in_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text, nullable=True),
        sa.Column('cancelled_by', sa.String(50), nullable=True),
        sa.Column('rescheduled_from_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.id'), nullable=True),
        sa.Column('reminder_sent', sa.Boolean, default=False),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id'), nullable=True),
        sa.Column('voice_booking_metadata', postgresql.JSONB, nullable=True),
        sa.Column('emr_visit_id', sa.String(50), nullable=True),
    )
    op.create_index('ix_appointments_patient_id', 'appointments', ['patient_id'])
    op.create_index('ix_appointments_doctor_id', 'appointments', ['doctor_id'])
    op.create_index('ix_appointments_scheduled_start', 'appointments', ['scheduled_start'])
    op.create_index('ix_appointments_status', 'appointments', ['status'])
    op.create_index('ix_appointments_emr_visit_id', 'appointments', ['emr_visit_id'])

    # Invoices table
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('invoice_number', sa.String(50), unique=True, nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=True),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), default=0.00),
        sa.Column('tax_amount', sa.Numeric(10, 2), default=0.00),
        sa.Column('discount_amount', sa.Numeric(10, 2), default=0.00),
        sa.Column('discount_reason', sa.String(200), nullable=True),
        sa.Column('total_amount', sa.Numeric(12, 2), default=0.00),
        sa.Column('paid_amount', sa.Numeric(12, 2), default=0.00),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('invoice_date', sa.Date, nullable=False),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('gstin', sa.String(20), nullable=True),
        sa.Column('cgst_amount', sa.Numeric(10, 2), default=0.00),
        sa.Column('sgst_amount', sa.Numeric(10, 2), default=0.00),
        sa.Column('igst_amount', sa.Numeric(10, 2), default=0.00),
        sa.Column('is_cancelled', sa.Boolean, default=False),
        sa.Column('cancellation_reason', sa.Text, nullable=True),
    )
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('ix_invoices_patient_id', 'invoices', ['patient_id'])
    op.create_index('ix_invoices_clinic_id', 'invoices', ['clinic_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])

    # Invoice Items table
    op.create_table(
        'invoice_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('services.id'), nullable=True),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Integer, default=1),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_rate', sa.Numeric(5, 2), default=0.00),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(10, 2), default=0.00),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('hsn_code', sa.String(10), nullable=True),
    )
    op.create_index('ix_invoice_items_invoice_id', 'invoice_items', ['invoice_id'])

    # Payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_method', sa.String(20), default='cash'),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('payment_gateway', sa.String(50), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(100), nullable=True),
        sa.Column('razorpay_order_id', sa.String(100), nullable=True),
        sa.Column('razorpay_signature', sa.String(255), nullable=True),
        sa.Column('upi_transaction_id', sa.String(100), nullable=True),
        sa.Column('upi_vpa', sa.String(100), nullable=True),
        sa.Column('payment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('receipt_number', sa.String(50), nullable=True),
        sa.Column('refund_amount', sa.Numeric(12, 2), default=0.00),
        sa.Column('refund_reason', sa.Text, nullable=True),
        sa.Column('refund_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refund_transaction_id', sa.String(100), nullable=True),
        sa.Column('gateway_response', postgresql.JSONB, nullable=True),
        sa.Column('collected_by', sa.String(200), nullable=True),
    )
    op.create_index('ix_payments_invoice_id', 'payments', ['invoice_id'])
    op.create_index('ix_payments_transaction_id', 'payments', ['transaction_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])


def downgrade() -> None:
    op.drop_table('payments')
    op.drop_table('invoice_items')
    op.drop_table('invoices')
    op.drop_table('appointments')
    op.drop_table('services')
    op.drop_table('patients')
    op.drop_table('doctors')
    op.drop_table('users')
    op.drop_table('clinics')
