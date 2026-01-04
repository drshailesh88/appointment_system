"""
Tests for EMR Sync Service (Phase 13).

Tests real-time sync between Practice Manager and DocAssist EMR.
"""

import asyncio
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.procedure import Procedure
from app.services.emr_sync_service import EMRSyncService


@pytest.fixture
def temp_emr_db():
    """Create a temporary EMR SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create EMR database schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Patients table
    cursor.execute("""
        CREATE TABLE patients (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            date_of_birth TEXT,
            gender TEXT,
            blood_group TEXT,
            allergies TEXT,
            address TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Visits table
    cursor.execute("""
        CREATE TABLE visits (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            chief_complaint TEXT,
            diagnosis TEXT,
            notes TEXT,
            vitals TEXT,
            prescriptions TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # Appointments table
    cursor.execute("""
        CREATE TABLE appointments (
            id TEXT PRIMARY KEY,
            external_id TEXT UNIQUE,
            patient_id TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            appointment_type TEXT,
            chief_complaint TEXT,
            status TEXT NOT NULL,
            visit_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (visit_id) REFERENCES visits(id)
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink()


@pytest.fixture
def emr_service(temp_emr_db):
    """Create an EMR sync service with test database."""
    service = EMRSyncService()
    service.emr.db_path = temp_emr_db
    service.emr_async.emr.db_path = temp_emr_db
    return service


@pytest.fixture
def sample_emr_patient(temp_emr_db):
    """Insert a sample patient into EMR database."""
    conn = sqlite3.connect(str(temp_emr_db))
    cursor = conn.cursor()

    patient_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        INSERT INTO patients (
            id, first_name, last_name, phone, email,
            date_of_birth, gender, blood_group, allergies, address,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_id,
            "John",
            "Doe",
            "+919876543210",
            "john@example.com",
            "1990-05-15",
            "M",
            "O+",
            "None",
            "123 Test Street",
            now,
            now,
        ),
    )

    conn.commit()
    conn.close()

    return patient_id


@pytest.fixture
def sample_emr_visit(temp_emr_db, sample_emr_patient):
    """Insert a sample visit into EMR database."""
    conn = sqlite3.connect(str(temp_emr_db))
    cursor = conn.cursor()

    visit_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        INSERT INTO visits (
            id, patient_id, doctor_name, visit_date,
            chief_complaint, diagnosis, notes, vitals, prescriptions, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            visit_id,
            sample_emr_patient,
            "Dr. Test Doctor",
            now,
            "Headache",
            "Tension headache",
            "Patient complains of headache for 2 days",
            '{"bp": "120/80", "pulse": 72}',
            '[{"name": "Paracetamol", "dosage": "500mg", "frequency": "TID"}]',
            now,
        ),
    )

    conn.commit()
    conn.close()

    return visit_id


class TestEMRSyncService:
    """Test EMR Sync Service functionality."""

    def test_is_available(self, emr_service):
        """Test EMR availability check."""
        assert emr_service.is_available()

    def test_get_status(self, emr_service):
        """Test getting sync status."""
        status = emr_service.get_status()

        assert status["enabled"] is True
        assert status["available"] is True
        assert status["database_path"] is not None
        assert "stats" in status

    @pytest.mark.asyncio
    async def test_sync_patient_from_emr_new(
        self,
        emr_service,
        sample_emr_patient,
        db,
        test_clinic,
    ):
        """Test syncing a new patient from EMR."""
        # Convert sync Session to async Session for testing
        # In real usage, this will be an async session
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as async_db:
            patient = await emr_service.sync_patient_from_emr(
                sample_emr_patient,
                async_db,
            )

            assert patient is not None
            assert patient.first_name == "John"
            assert patient.last_name == "Doe"
            assert patient.phone == "+919876543210"
            assert patient.emr_patient_id == sample_emr_patient
            assert patient.emr_synced_at is not None

    @pytest.mark.asyncio
    async def test_sync_patient_from_emr_update(
        self,
        emr_service,
        sample_emr_patient,
        db,
        test_clinic,
    ):
        """Test updating an existing patient from EMR."""
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as async_db:
            # First sync
            patient1 = await emr_service.sync_patient_from_emr(
                sample_emr_patient,
                async_db,
            )
            first_sync_time = patient1.emr_synced_at

            # Update patient in EMR
            conn = emr_service.emr.get_connection()
            conn.execute(
                "UPDATE patients SET email = ? WHERE id = ?",
                ("newemail@example.com", sample_emr_patient),
            )
            conn.commit()
            conn.close()

            # Second sync should update
            await asyncio.sleep(0.1)  # Ensure different timestamp
            patient2 = await emr_service.sync_patient_from_emr(
                sample_emr_patient,
                async_db,
            )

            assert patient2.id == patient1.id
            assert patient2.email == "newemail@example.com"
            assert patient2.emr_synced_at > first_sync_time

    @pytest.mark.asyncio
    async def test_get_patient_visits(
        self,
        emr_service,
        sample_emr_patient,
        sample_emr_visit,
    ):
        """Test fetching patient visits from EMR."""
        visits = await emr_service.emr_async.get_patient_visits(
            sample_emr_patient,
            limit=10,
        )

        assert len(visits) == 1
        assert visits[0].id == sample_emr_visit
        assert visits[0].patient_id == sample_emr_patient
        assert visits[0].doctor_name == "Dr. Test Doctor"
        assert visits[0].chief_complaint == "Headache"
        assert visits[0].diagnosis == "Tension headache"
        assert visits[0].vitals is not None
        assert visits[0].prescriptions is not None

    @pytest.mark.asyncio
    async def test_sync_appointment_to_emr(
        self,
        emr_service,
        test_appointment,
        test_patient,
        db,
    ):
        """Test syncing an appointment to EMR."""
        from app.core.database import AsyncSessionLocal

        # Set EMR patient ID
        test_patient.emr_patient_id = str(uuid4())
        db.add(test_patient)
        db.commit()

        async with AsyncSessionLocal() as async_db:
            # Load appointment with relationships
            stmt = (
                select(Appointment)
                .where(Appointment.id == test_appointment.id)
                .options(
                    selectinload(Appointment.doctor),
                    selectinload(Appointment.patient),
                )
            )
            result = await async_db.execute(stmt)
            appointment = result.scalar_one()

            success = await emr_service.sync_appointment_to_emr(appointment, async_db)

            assert success is True

            # Verify in EMR database
            conn = emr_service.emr.get_connection()
            cursor = conn.execute(
                "SELECT * FROM appointments WHERE external_id = ?",
                (str(test_appointment.id),),
            )
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row["patient_id"] == test_patient.emr_patient_id
            assert row["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_link_appointment_to_visit(
        self,
        emr_service,
        test_appointment,
        sample_emr_visit,
        db,
    ):
        """Test linking an appointment to an EMR visit."""
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as async_db:
            success = await emr_service.link_appointment_to_visit(
                str(test_appointment.id),
                sample_emr_visit,
                async_db,
            )

            assert success is True

            # Verify in PM database
            stmt = select(Appointment).where(Appointment.id == test_appointment.id)
            result = await async_db.execute(stmt)
            appointment = result.scalar_one()

            assert appointment.emr_visit_id == sample_emr_visit

    def test_file_watcher_start_stop(self, emr_service):
        """Test starting and stopping file watcher."""
        # Start watcher
        emr_service.start_file_watcher()
        assert emr_service.emr._running is True

        # Stop watcher
        emr_service.stop_file_watcher()
        assert emr_service.emr._running is False


class TestEMRIntegration:
    """Test EMR Integration module directly."""

    @pytest.mark.asyncio
    async def test_search_patients(self, emr_service, sample_emr_patient):
        """Test patient search in EMR."""
        results = await emr_service.emr_async.search_patients("John", limit=10)

        assert len(results) == 1
        assert results[0].first_name == "John"
        assert results[0].last_name == "Doe"

    @pytest.mark.asyncio
    async def test_search_patients_by_phone(self, emr_service, sample_emr_patient):
        """Test patient search by phone number."""
        results = await emr_service.emr_async.search_patients("9876543210", limit=10)

        assert len(results) == 1
        assert results[0].phone == "+919876543210"

    @pytest.mark.asyncio
    async def test_get_nonexistent_patient(self, emr_service):
        """Test fetching a patient that doesn't exist."""
        patient = await emr_service.emr_async.get_patient("nonexistent-id")

        assert patient is None

    @pytest.mark.asyncio
    async def test_get_nonexistent_visit(self, emr_service):
        """Test fetching a visit that doesn't exist."""
        visit = await emr_service.emr_async.get_patient_visits(
            "nonexistent-patient-id",
            limit=10,
        )

        assert len(visit) == 0


class TestConflictResolution:
    """Test conflict resolution strategies."""

    @pytest.mark.asyncio
    async def test_emr_wins_for_patient_data(
        self,
        emr_service,
        sample_emr_patient,
        test_patient,
        db,
    ):
        """Test that EMR data wins for patient demographics."""
        from app.core.database import AsyncSessionLocal

        # Set EMR patient ID on test patient
        test_patient.emr_patient_id = sample_emr_patient
        test_patient.email = "old@example.com"
        db.add(test_patient)
        db.commit()

        async with AsyncSessionLocal() as async_db:
            # Sync from EMR (which has john@example.com)
            patient = await emr_service.sync_patient_from_emr(
                sample_emr_patient,
                async_db,
            )

            # EMR data should win
            assert patient.email == "john@example.com"
            assert patient.first_name == "John"
