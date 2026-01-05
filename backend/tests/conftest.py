"""
Pytest configuration and fixtures for the test suite.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment BEFORE importing app modules
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_123456"
os.environ["RAZORPAY_KEY_SECRET"] = "test_secret_key_12345678"

# Now we can import app modules
from fastapi.testclient import TestClient

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


# Synchronous engine for simple tests
TEST_DATABASE_URL = "sqlite:///:memory:"
sync_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Async engine for async tests
ASYNC_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
async_engine = create_async_engine(
    ASYNC_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AsyncTestingSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def override_get_db():
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def override_get_async_db():
    """Override async database dependency for tests."""
    async with AsyncTestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test (sync)."""
    Base.metadata.create_all(bind=sync_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_engine)


@pytest_asyncio.fixture(scope="function")
async def async_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database for each test (async)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncTestingSessionLocal() as session:
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override (sync)."""
    # Import app here to avoid circular imports
    from app.main import app
    from app.api.deps import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client(async_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database override."""
    from app.main import app
    from app.api.deps import get_db

    async def override_db():
        yield async_db

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def test_clinic(db: Session) -> Clinic:
    """Create a test clinic."""
    clinic = Clinic(
        id=uuid4(),
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
    db.commit()
    db.refresh(clinic)
    return clinic


@pytest.fixture
def test_user(db: Session, test_clinic: Clinic) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid4(),
        email="admin@test.com",
        phone="+919876543210",
        hashed_password=get_password_hash("testpassword123"),
        name="Test Admin",
        role="admin",
        clinic_id=test_clinic.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_doctor(db: Session, test_clinic: Clinic) -> Doctor:
    """Create a test doctor."""
    # Create a user for the doctor
    user = User(
        id=uuid4(),
        email="doctor@test.com",
        phone="+919876543211",
        hashed_password=get_password_hash("doctorpass123"),
        name="Dr. Test Doctor",
        role="doctor",
        clinic_id=test_clinic.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    doctor = Doctor(
        id=uuid4(),
        user_id=user.id,
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
    db.commit()
    db.refresh(doctor)
    return doctor


@pytest.fixture
def test_patient(db: Session, test_clinic: Clinic) -> Patient:
    """Create a test patient."""
    patient = Patient(
        id=uuid4(),
        clinic_id=test_clinic.id,
        name="Test Patient",
        phone="+919876543212",
        email="patient@test.com",
        gender="male",
        date_of_birth=datetime(1990, 1, 15).date(),
        address="456 Patient Road",
        city="Mumbai",
        blood_group="O+",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@pytest.fixture
def test_service(db: Session, test_clinic: Clinic) -> Service:
    """Create a test service."""
    service = Service(
        id=uuid4(),
        clinic_id=test_clinic.id,
        name="General Consultation",
        description="Standard doctor consultation",
        price=500.0,
        duration_minutes=15,
        is_active=True,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@pytest.fixture
def test_appointment(
    db: Session,
    test_doctor: Doctor,
    test_patient: Patient,
) -> Appointment:
    """Create a test appointment."""
    now = datetime.now(timezone.utc)
    start_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if start_time < now:
        start_time += timedelta(days=1)

    appointment = Appointment(
        doctor_id=test_doctor.id,
        patient_id=test_patient.id,
        scheduled_start=start_time,
        scheduled_end=start_time + timedelta(minutes=15),
        duration_minutes=15,
        status="scheduled",
        appointment_type="new_consultation",
        chief_complaint="General checkup",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for the test user."""
    token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def doctor_auth_headers(db: Session, test_doctor: Doctor) -> dict:
    """Generate authentication headers for the test doctor."""
    user = db.query(User).filter(User.id == test_doctor.user_id).first()
    token = create_access_token(data={"sub": user.id})
    return {"Authorization": f"Bearer {token}"}
