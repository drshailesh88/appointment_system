"""
Tests for SQLAlchemy models.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.service import Service
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.core.security import get_password_hash


class TestClinicModel:
    """Clinic model tests."""

    def test_create_clinic(self, db: Session):
        """Test creating a clinic."""
        clinic = Clinic(
            id=str(uuid4()),
            name="Test Clinic",
            address="123 Test Street",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            phone="+919876543210",
            subscription_tier="free",
        )
        db.add(clinic)
        db.commit()
        db.refresh(clinic)

        assert clinic.id is not None
        assert clinic.name == "Test Clinic"
        assert clinic.subscription_tier == "free"
        assert clinic.created_at is not None

    def test_clinic_relationships(self, db: Session, test_clinic, test_doctor, test_patient):
        """Test clinic relationships."""
        assert test_clinic.id is not None

        # Verify relationships can be accessed
        doctors = db.query(Doctor).filter(Doctor.clinic_id == test_clinic.id).all()
        patients = db.query(Patient).filter(Patient.clinic_id == test_clinic.id).all()

        assert len(doctors) >= 1
        assert len(patients) >= 1


class TestUserModel:
    """User model tests."""

    def test_create_user(self, db: Session, test_clinic):
        """Test creating a user."""
        user = User(
            id=str(uuid4()),
            email="testuser@test.com",
            phone="+919876543299",
            hashed_password=get_password_hash("testpass123"),
            name="Test User",
            role="staff",
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.email == "testuser@test.com"
        assert user.is_active == True

    def test_user_password_hash(self, db: Session, test_clinic):
        """Test that password is hashed."""
        password = "mypassword123"
        user = User(
            id=str(uuid4()),
            email="hashtest@test.com",
            hashed_password=get_password_hash(password),
            name="Hash Test",
            role="staff",
            clinic_id=test_clinic.id,
        )
        db.add(user)
        db.commit()

        assert user.hashed_password != password
        assert len(user.hashed_password) > 20


class TestDoctorModel:
    """Doctor model tests."""

    def test_doctor_working_hours(self, test_doctor):
        """Test doctor working hours JSON field."""
        assert test_doctor.working_hours is not None
        assert "monday" in test_doctor.working_hours
        assert test_doctor.working_hours["monday"]["start"] == "09:00"

    def test_doctor_fees(self, test_doctor):
        """Test doctor fee fields."""
        assert test_doctor.consultation_fee == 500.0
        assert test_doctor.followup_fee == 300.0


class TestPatientModel:
    """Patient model tests."""

    def test_patient_age_calculation(self, test_patient):
        """Test patient date of birth."""
        assert test_patient.date_of_birth is not None
        age = (datetime.now().date() - test_patient.date_of_birth).days // 365
        assert age > 0

    def test_patient_gender(self, test_patient):
        """Test patient gender field."""
        assert test_patient.gender in ["male", "female", "other"]


class TestAppointmentModel:
    """Appointment model tests."""

    def test_appointment_creation(self, test_appointment):
        """Test appointment creation."""
        assert test_appointment.id is not None
        assert test_appointment.status == "scheduled"
        assert test_appointment.start_time < test_appointment.end_time

    def test_appointment_duration(self, test_appointment):
        """Test appointment duration."""
        duration = test_appointment.end_time - test_appointment.start_time
        assert duration == timedelta(minutes=15)

    def test_appointment_status_values(self, db: Session, test_appointment):
        """Test appointment status transitions."""
        valid_statuses = [
            "scheduled",
            "checked_in",
            "in_progress",
            "completed",
            "cancelled",
            "no_show",
        ]
        for status in valid_statuses:
            test_appointment.status = status
            db.commit()
            assert test_appointment.status == status


class TestServiceModel:
    """Service model tests."""

    def test_service_creation(self, test_service):
        """Test service creation."""
        assert test_service.id is not None
        assert test_service.name == "General Consultation"
        assert test_service.price == 500.0
        assert test_service.duration_minutes == 15


class TestInvoiceModel:
    """Invoice model tests."""

    def test_create_invoice(self, db: Session, test_clinic, test_patient, test_appointment):
        """Test creating an invoice."""
        invoice = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            appointment_id=test_appointment.id,
            invoice_number="INV-001",
            subtotal=500.0,
            tax_amount=90.0,
            discount_amount=0.0,
            total_amount=590.0,
            status="pending",
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        assert invoice.id is not None
        assert invoice.total_amount == 590.0
        assert invoice.status == "pending"

    def test_invoice_calculations(self, db: Session, test_clinic, test_patient, test_appointment):
        """Test invoice amount calculations."""
        subtotal = 1000.0
        tax = subtotal * 0.18  # 18% GST
        discount = 100.0
        total = subtotal + tax - discount

        invoice = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            appointment_id=test_appointment.id,
            invoice_number="INV-002",
            subtotal=subtotal,
            tax_amount=tax,
            discount_amount=discount,
            total_amount=total,
            status="pending",
        )
        db.add(invoice)
        db.commit()

        assert invoice.total_amount == 1080.0


class TestPaymentModel:
    """Payment model tests."""

    def test_create_payment(self, db: Session, test_clinic, test_patient, test_appointment):
        """Test creating a payment."""
        # First create an invoice
        invoice = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            appointment_id=test_appointment.id,
            invoice_number="INV-003",
            subtotal=500.0,
            total_amount=500.0,
            status="pending",
        )
        db.add(invoice)
        db.commit()

        payment = Payment(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=500.0,
            payment_method="cash",
            status="completed",
            transaction_id="TXN-001",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        assert payment.id is not None
        assert payment.amount == 500.0
        assert payment.status == "completed"
