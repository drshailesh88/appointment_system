"""
Pytest configuration and fixtures for the test suite.
All fixtures use async SQLAlchemy to match the application's async architecture.
"""
import os
import sys
from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio

# Set test environment BEFORE importing app modules
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"

# Now we can import app modules
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from httpx import AsyncClient, ASGITransport

from app.core.security import get_password_hash, create_access_token
from app.models.base import Base
from app.models.user import User
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.service import Service
from app.models.invoice import Invoice
from app.models.payment import Payment


# Create async test engine with SQLite (in-memory)
ASYNC_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async_engine = create_async_engine(
    ASYNC_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True for SQL debugging
)

# Async session maker
AsyncTestingSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh async database session for each test.

    This fixture:
    1. Creates all tables in memory
    2. Provides an async session
    3. Cleans up tables after the test
    """
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with AsyncTestingSessionLocal() as session:
        yield session

    # Drop tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client with database override.

    Args:
        db: Async database session

    Yields:
        AsyncClient: HTTP client for testing API endpoints
    """
    from app.main import app
    from app.core.database import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_clinic(db: AsyncSession) -> Clinic:
    """Create a test clinic."""
    clinic = Clinic(
        id=str(uuid4()),
        name="Test Clinic",
        slug="test-clinic",
        address="123 Test Street",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        phone="+919876543210",
        email="test@clinic.com",
        subscription_tier="professional",
    )
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)
    return clinic


@pytest_asyncio.fixture
async def test_user(db: AsyncSession, test_clinic: Clinic) -> User:
    """Create a test admin user."""
    user = User(
        id=str(uuid4()),
        email="admin@test.com",
        phone="+919876543210",
        password_hash=get_password_hash("testpassword123"),
        name="Test Admin",
        role="admin",
        clinic_id=test_clinic.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_doctor(db: AsyncSession, test_clinic: Clinic) -> Doctor:
    """Create a test doctor."""
    # Create a user for the doctor
    user = User(
        id=str(uuid4()),
        email="doctor@test.com",
        phone="+919876543211",
        password_hash=get_password_hash("doctorpass123"),
        name="Dr. Test Doctor",
        role="doctor",
        clinic_id=test_clinic.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()

    doctor = Doctor(
        id=str(uuid4()),
        clinic_id=test_clinic.id,
        name="Dr. Test Doctor",
        specialization="General Medicine",
        qualification="MBBS, MD",
        registration_number="MH12345",
        consultation_fee=500.0,
        followup_fee=300.0,
        slot_duration=15,
        working_hours={
            "monday": [{"start": "09:00", "end": "17:00"}],
            "tuesday": [{"start": "09:00", "end": "17:00"}],
            "wednesday": [{"start": "09:00", "end": "17:00"}],
            "thursday": [{"start": "09:00", "end": "17:00"}],
            "friday": [{"start": "09:00", "end": "17:00"}],
        },
        is_active=True,
    )
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)

    # Link user to doctor
    user.doctor_id = doctor.id
    await db.commit()

    return doctor


@pytest_asyncio.fixture
async def test_patient(db: AsyncSession, test_clinic: Clinic) -> Patient:
    """Create a test patient."""
    patient = Patient(
        id=str(uuid4()),
        clinic_id=test_clinic.id,
        first_name="Test",
        last_name="Patient",
        phone="+919876543212",
        email="patient@test.com",
        gender="male",
        date_of_birth=datetime(1990, 1, 15).date(),
        address="456 Patient Road",
        city="Mumbai",
        blood_group="O+",
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def test_service(db: AsyncSession, test_clinic: Clinic) -> Service:
    """Create a test service."""
    service = Service(
        id=str(uuid4()),
        clinic_id=test_clinic.id,
        name="General Consultation",
        description="Standard doctor consultation",
        price=500.0,
        duration_minutes=15,
        is_active=True,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@pytest_asyncio.fixture
async def test_appointment(
    db: AsyncSession,
    test_clinic: Clinic,
    test_doctor: Doctor,
    test_patient: Patient,
) -> Appointment:
    """Create a test appointment."""
    now = datetime.now()
    scheduled_start = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if scheduled_start < now:
        scheduled_start += timedelta(days=1)

    appointment = Appointment(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        patient_id=test_patient.id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_start + timedelta(minutes=15),
        status="scheduled",
        appointment_type="new_consultation",
        chief_complaint="General checkup",
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for the test user."""
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def doctor_auth_headers(db: AsyncSession, test_doctor: Doctor) -> dict:
    """Generate authentication headers for the test doctor."""
    from sqlalchemy import select

    result = await db.execute(
        select(User).filter(User.doctor_id == test_doctor.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError(f"No user found for doctor {test_doctor.id}")

    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Create sample image bytes for testing file uploads."""
    # Minimal valid JPEG bytes
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
        0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
        0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
        0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
        0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
        0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
        0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
        0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
        0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
        0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x6D, 0xB4, 0xD9, 0xED, 0xB6,
        0xDB, 0x6D, 0xB6, 0xDB, 0x6D, 0xB6, 0xDB, 0x6D, 0xB6, 0xDB, 0x6D, 0xB6,
        0xDB, 0x6D, 0xB6, 0xDB, 0x6D, 0xB6, 0xDB, 0x6D, 0xB6, 0xFF, 0xD9
    ])
