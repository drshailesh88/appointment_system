"""
Pytest fixtures for DocAssist Practice Manager tests.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base
from src.models.appointment import Appointment, AppointmentStatus, AppointmentType
from src.models.doctor import Doctor
from src.models.patient import Patient
from src.models.service import Service


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_patient(session: Session) -> Patient:
    """Create a sample patient for testing."""
    patient = Patient(
        first_name="Rahul",
        last_name="Sharma",
        phone="9876543210",
        email="rahul.sharma@example.com",
        gender="M",
        city="Mumbai",
        pincode="400001",
    )
    session.add(patient)
    session.commit()
    return patient


@pytest.fixture
def sample_doctor(session: Session) -> Doctor:
    """Create a sample doctor for testing."""
    doctor = Doctor(
        name="Dr. Priya Patel",
        specialization="General Medicine",
        qualification="MBBS, MD",
        registration_number="MH-12345",
        phone="9876543211",
        consultation_fee=Decimal("500.00"),
        slot_duration=15,
        working_hours={
            "monday": {"start": "09:00", "end": "17:00", "break_start": "13:00", "break_end": "14:00"},
            "tuesday": {"start": "09:00", "end": "17:00", "break_start": "13:00", "break_end": "14:00"},
            "wednesday": {"start": "09:00", "end": "17:00", "break_start": "13:00", "break_end": "14:00"},
            "thursday": {"start": "09:00", "end": "17:00", "break_start": "13:00", "break_end": "14:00"},
            "friday": {"start": "09:00", "end": "17:00", "break_start": "13:00", "break_end": "14:00"},
            "saturday": {"start": "09:00", "end": "13:00"},
        },
    )
    session.add(doctor)
    session.commit()
    return doctor


@pytest.fixture
def sample_service(session: Session) -> Service:
    """Create a sample service for testing."""
    service = Service(
        name="General Consultation",
        category="consultation",
        duration=15,
        price=Decimal("500.00"),
        tax_rate=Decimal("18.00"),
    )
    session.add(service)
    session.commit()
    return service


@pytest.fixture
def sample_appointment(
    session: Session,
    sample_patient: Patient,
    sample_doctor: Doctor,
    sample_service: Service,
) -> Appointment:
    """Create a sample appointment for testing."""
    start_time = datetime.utcnow() + timedelta(days=1)
    start_time = start_time.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(minutes=15)

    appointment = Appointment(
        patient_id=sample_patient.id,
        doctor_id=sample_doctor.id,
        service_id=sample_service.id,
        start_time=start_time,
        end_time=end_time,
        status=AppointmentStatus.SCHEDULED.value,
        type=AppointmentType.CONSULTATION.value,
    )
    session.add(appointment)
    session.commit()
    return appointment
