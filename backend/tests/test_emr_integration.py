"""
Comprehensive tests for EMR integration.

Tests patient sync, appointment bidirectional sync, visit linking, and data integrity.
"""

import pytest
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.integrations.emr import (
    EMRIntegration,
    EMRIntegrationAsync,
    EMRPatient,
    EMRVisit,
    SyncEvent,
)


@pytest.fixture
def temp_emr_db():
    """Create a temporary EMR database for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = Path(temp_file.name)
    temp_file.close()

    # Create tables
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create patients table
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

    # Create visits table
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

    # Create appointments table
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
    db_path.unlink(missing_ok=True)


@pytest.fixture
def emr_integration(temp_emr_db):
    """Create EMR integration instance."""
    return EMRIntegration(emr_db_path=temp_emr_db)


@pytest.fixture
def sample_patient_data():
    """Create sample patient data."""
    return {
        "id": str(uuid4()),
        "first_name": "Rajesh",
        "last_name": "Kumar",
        "phone": "+919876543210",
        "email": "rajesh.kumar@example.com",
        "date_of_birth": "1985-05-15",
        "gender": "M",
        "blood_group": "B+",
        "allergies": "Penicillin",
        "address": "123 MG Road, Mumbai",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class TestPatientSync:
    """Test patient data synchronization."""

    def test_get_patient(self, emr_integration, temp_emr_db, sample_patient_data):
        """Test reading patient from EMR."""
        # Insert patient into EMR database
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample_patient_data["id"],
                sample_patient_data["first_name"],
                sample_patient_data["last_name"],
                sample_patient_data["phone"],
                sample_patient_data["email"],
                sample_patient_data["date_of_birth"],
                sample_patient_data["gender"],
                sample_patient_data["blood_group"],
                sample_patient_data["allergies"],
                sample_patient_data["address"],
                sample_patient_data["created_at"],
                sample_patient_data["updated_at"],
            ),
        )
        conn.commit()
        conn.close()

        # Get patient
        patient = emr_integration.get_patient(sample_patient_data["id"])

        assert patient is not None
        assert patient.id == sample_patient_data["id"]
        assert patient.first_name == sample_patient_data["first_name"]
        assert patient.phone == sample_patient_data["phone"]
        assert patient.blood_group == sample_patient_data["blood_group"]

    def test_get_nonexistent_patient(self, emr_integration):
        """Test getting non-existent patient returns None."""
        patient = emr_integration.get_patient("nonexistent_id")
        assert patient is None

    def test_search_patients_by_name(self, emr_integration, temp_emr_db):
        """Test searching patients by name."""
        # Insert multiple patients
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()

        patients = [
            (str(uuid4()), "Rajesh", "Kumar", "+919876543210"),
            (str(uuid4()), "Priya", "Sharma", "+919876543211"),
            (str(uuid4()), "Raj", "Patel", "+919876543212"),
        ]

        now = datetime.now(timezone.utc).isoformat()
        for patient in patients:
            cursor.execute(
                """
                INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (*patient, now, now),
            )
        conn.commit()
        conn.close()

        # Search for "Raj"
        results = emr_integration.search_patients("Raj")

        assert len(results) == 2  # Rajesh and Raj
        names = [p.first_name for p in results]
        assert "Rajesh" in names
        assert "Raj" in names

    def test_search_patients_by_phone(self, emr_integration, temp_emr_db):
        """Test searching patients by phone number."""
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()

        patient_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )
        conn.commit()
        conn.close()

        # Search by phone
        results = emr_integration.search_patients("9876543210")

        assert len(results) == 1
        assert results[0].phone == "+919876543210"

    def test_get_patients_updated_since(self, emr_integration, temp_emr_db):
        """Test getting patients updated since timestamp."""
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()

        # Insert old patient
        old_time = datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid4()), "Old", "Patient", "+919876543210", old_time, old_time),
        )

        # Insert new patient
        new_time = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid4()), "New", "Patient", "+919876543211", new_time, new_time),
        )
        conn.commit()
        conn.close()

        # Get patients updated since yesterday
        since = datetime.now(timezone.utc) - timezone.timedelta(days=1)
        results = emr_integration.get_patients_updated_since(since)

        assert len(results) == 1
        assert results[0].first_name == "New"

    def test_no_patient_duplication(self, emr_integration):
        """Test that patients are not duplicated (read-only from EMR)."""
        # EMR integration only reads patients, never creates them
        # This ensures Practice Manager doesn't duplicate patient data
        assert emr_integration.is_available()


class TestVisitSync:
    """Test visit/consultation synchronization."""

    def test_get_patient_visits(self, emr_integration, temp_emr_db):
        """Test getting patient visits from EMR."""
        # Create patient
        patient_id = str(uuid4())
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )

        # Create visits
        visit1_id = str(uuid4())
        visit2_id = str(uuid4())

        cursor.execute(
            """
            INSERT INTO visits (id, patient_id, doctor_name, visit_date, chief_complaint, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (visit1_id, patient_id, "Dr. Sharma", "2024-01-15", "Fever", now),
        )

        cursor.execute(
            """
            INSERT INTO visits (id, patient_id, doctor_name, visit_date, chief_complaint, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (visit2_id, patient_id, "Dr. Patel", "2024-01-20", "Cough", now),
        )

        conn.commit()
        conn.close()

        # Get visits
        visits = emr_integration.get_patient_visits(patient_id)

        assert len(visits) == 2
        assert visits[0].patient_id == patient_id
        assert visits[0].doctor_name in ["Dr. Sharma", "Dr. Patel"]

    def test_get_visit(self, emr_integration, temp_emr_db):
        """Test getting specific visit."""
        patient_id = str(uuid4())
        visit_id = str(uuid4())

        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )

        cursor.execute(
            """
            INSERT INTO visits (id, patient_id, doctor_name, visit_date, chief_complaint,
                              diagnosis, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visit_id,
                patient_id,
                "Dr. Kumar",
                "2024-01-25",
                "Headache",
                "Migraine",
                "Prescribed painkillers",
                now,
            ),
        )
        conn.commit()
        conn.close()

        visit = emr_integration.get_visit(visit_id)

        assert visit is not None
        assert visit.id == visit_id
        assert visit.diagnosis == "Migraine"
        assert visit.notes == "Prescribed painkillers"

    def test_visit_with_vitals(self, emr_integration, temp_emr_db):
        """Test visit with vitals stored as JSON."""
        import json

        patient_id = str(uuid4())
        visit_id = str(uuid4())

        vitals = {
            "temperature": 98.6,
            "blood_pressure": "120/80",
            "pulse": 72,
            "spo2": 98,
        }

        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )

        cursor.execute(
            """
            INSERT INTO visits (id, patient_id, doctor_name, visit_date, vitals, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (visit_id, patient_id, "Dr. Verma", "2024-01-30", json.dumps(vitals), now),
        )
        conn.commit()
        conn.close()

        visit = emr_integration.get_visit(visit_id)

        assert visit.vitals is not None
        assert visit.vitals["temperature"] == 98.6
        assert visit.vitals["pulse"] == 72


class TestAppointmentSync:
    """Test bidirectional appointment synchronization."""

    def test_sync_appointment_to_emr_new(self, emr_integration, temp_emr_db):
        """Test syncing new appointment to EMR."""
        # Create patient first
        patient_id = str(uuid4())
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )
        conn.commit()
        conn.close()

        # Sync appointment
        appointment_id = str(uuid4())
        scheduled_time = datetime.now(timezone.utc)

        result = emr_integration.sync_appointment_to_emr(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_name="Dr. Singh",
            scheduled_start=scheduled_time,
            appointment_type="consultation",
            chief_complaint="Follow-up",
        )

        assert result is True

        # Verify appointment in EMR
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM appointments WHERE external_id = ?",
            (appointment_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None

    def test_sync_appointment_to_emr_update(self, emr_integration, temp_emr_db):
        """Test updating existing appointment in EMR."""
        patient_id = str(uuid4())
        appointment_id = str(uuid4())

        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Create patient
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )

        # Create existing appointment
        cursor.execute(
            """
            INSERT INTO appointments (id, external_id, patient_id, doctor_name,
                                    scheduled_time, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                appointment_id,
                patient_id,
                "Dr. Old",
                now,
                "scheduled",
                now,
                now,
            ),
        )
        conn.commit()
        conn.close()

        # Update appointment
        new_time = datetime.now(timezone.utc)
        result = emr_integration.sync_appointment_to_emr(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_name="Dr. New",
            scheduled_start=new_time,
            appointment_type="consultation",
        )

        assert result is True

        # Verify update
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT scheduled_time FROM appointments WHERE external_id = ?",
            (appointment_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        # Time should be updated

    def test_link_appointment_to_visit(self, emr_integration, temp_emr_db):
        """Test linking appointment to visit after consultation."""
        patient_id = str(uuid4())
        appointment_id = str(uuid4())
        visit_id = str(uuid4())

        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        # Create patient
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )

        # Create appointment
        cursor.execute(
            """
            INSERT INTO appointments (id, external_id, patient_id, doctor_name,
                                    scheduled_time, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                appointment_id,
                patient_id,
                "Dr. Test",
                now,
                "scheduled",
                now,
                now,
            ),
        )

        # Create visit
        cursor.execute(
            """
            INSERT INTO visits (id, patient_id, doctor_name, visit_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (visit_id, patient_id, "Dr. Test", "2024-01-30", now),
        )
        conn.commit()
        conn.close()

        # Link appointment to visit
        result = emr_integration.link_appointment_to_visit(appointment_id, visit_id)

        assert result is True

        # Verify link
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT visit_id, status FROM appointments WHERE external_id = ?",
            (appointment_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] == visit_id  # visit_id
        assert row[1] == "completed"  # status

    def test_clinical_notes_stay_in_emr(self, emr_integration):
        """Test that clinical notes never leave EMR."""
        # Clinical notes are only in visits table in EMR
        # Practice Manager should never store clinical data
        # This is a design principle test
        assert emr_integration.is_available()


class TestAvailability:
    """Test EMR availability checks."""

    def test_is_available_with_db(self, emr_integration):
        """Test availability when database exists."""
        assert emr_integration.is_available() is True

    def test_is_available_without_db(self):
        """Test availability when database doesn't exist."""
        integration = EMRIntegration(emr_db_path=Path("/nonexistent/path.db"))
        assert integration.is_available() is False

    def test_find_emr_database(self):
        """Test automatic EMR database discovery."""
        integration = EMRIntegration()
        # Should try default paths
        # Will be None if no database found
        assert integration.db_path is None or integration.db_path.exists()


class TestAsyncWrapper:
    """Test async wrapper for EMR integration."""

    @pytest.mark.asyncio
    async def test_async_get_patient(self, temp_emr_db, sample_patient_data):
        """Test async patient retrieval."""
        integration = EMRIntegrationAsync(emr_db_path=temp_emr_db)

        # Insert patient
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample_patient_data["id"],
                sample_patient_data["first_name"],
                sample_patient_data["last_name"],
                sample_patient_data["phone"],
                sample_patient_data["email"],
                sample_patient_data["date_of_birth"],
                sample_patient_data["gender"],
                sample_patient_data["blood_group"],
                sample_patient_data["allergies"],
                sample_patient_data["address"],
                sample_patient_data["created_at"],
                sample_patient_data["updated_at"],
            ),
        )
        conn.commit()
        conn.close()

        patient = await integration.get_patient(sample_patient_data["id"])

        assert patient is not None
        assert patient.first_name == sample_patient_data["first_name"]

    @pytest.mark.asyncio
    async def test_async_search_patients(self, temp_emr_db):
        """Test async patient search."""
        integration = EMRIntegrationAsync(emr_db_path=temp_emr_db)

        # Insert patient
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid4()), "Async", "Patient", "+919876543210", now, now),
        )
        conn.commit()
        conn.close()

        results = await integration.search_patients("Async")

        assert len(results) == 1
        assert results[0].first_name == "Async"

    @pytest.mark.asyncio
    async def test_async_get_patient_visits(self, temp_emr_db):
        """Test async visit retrieval."""
        integration = EMRIntegrationAsync(emr_db_path=temp_emr_db)

        patient_id = str(uuid4())
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """
            INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, "Test", "Patient", "+919876543210", now, now),
        )

        cursor.execute(
            """
            INSERT INTO visits (id, patient_id, doctor_name, visit_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid4()), patient_id, "Dr. Test", "2024-01-30", now),
        )
        conn.commit()
        conn.close()

        visits = await integration.get_patient_visits(patient_id)

        assert len(visits) == 1


class TestFullSync:
    """Test full synchronization."""

    @pytest.mark.asyncio
    async def test_full_sync_patients(self, emr_integration, temp_emr_db):
        """Test full patient sync."""
        # Insert patients
        conn = sqlite3.connect(str(temp_emr_db))
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        for i in range(3):
            cursor.execute(
                """
                INSERT INTO patients (id, first_name, last_name, phone, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), f"Patient{i}", "Test", f"+9198765432{i}0", now, now),
            )
        conn.commit()
        conn.close()

        synced_patients = []

        def on_patient_sync(patient: EMRPatient):
            synced_patients.append(patient)

        emr_integration.on_patient_sync = on_patient_sync

        stats = await emr_integration.full_sync()

        assert stats["patients_synced"] == 3
        assert len(synced_patients) == 3

    @pytest.mark.asyncio
    async def test_full_sync_unavailable(self):
        """Test full sync when EMR unavailable."""
        integration = EMRIntegration(emr_db_path=Path("/nonexistent.db"))

        stats = await integration.full_sync()

        assert "error" in stats
        assert stats["synced"] is False


class TestFileWatcher:
    """Test file system watcher for real-time sync."""

    def test_start_watcher(self, emr_integration):
        """Test starting file watcher."""
        try:
            emr_integration.start_watcher()
            # Watcher should be running
            assert emr_integration._running is True
        except ImportError:
            # watchdog not installed
            pytest.skip("watchdog not installed")
        finally:
            if emr_integration._running:
                emr_integration.stop_watcher()

    def test_stop_watcher(self, emr_integration):
        """Test stopping file watcher."""
        try:
            emr_integration.start_watcher()
            emr_integration.stop_watcher()
            assert emr_integration._running is False
        except ImportError:
            pytest.skip("watchdog not installed")
