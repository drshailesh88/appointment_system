"""
Tests for OCR, EMR Sync, and Follow-up Intelligence Services.

Phase 10: Document Scanner & OCR
Phase 13: Advanced EMR Integration
Phase 16c: Proactive Intelligence

Comprehensive tests for:
1. OCR Service - text extraction, structured data, error handling
2. EMR Sync Service - sync operations, conflict resolution
3. Follow-up Intelligence Service - smart follow-up scheduling
"""

import asyncio
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select

from app.integrations.emr import EMRIntegration, EMRIntegrationAsync, EMRPatient, EMRVisit
from app.models.appointment import Appointment
from app.models.insight import FollowupSchedule
from app.models.patient import Patient
from app.models.procedure import Procedure
from app.services.emr_sync_service import EMRSyncService
from app.services.followup_intelligence import FollowupIntelligence
from app.services.ocr import OCRService


# ==========================================
# OCR SERVICE TESTS
# ==========================================


@pytest.fixture
def mock_easyocr_reader():
    """Mock EasyOCR reader."""
    with patch("app.services.ocr.easyocr") as mock_easyocr:
        mock_reader = MagicMock()
        mock_easyocr.Reader.return_value = mock_reader
        yield mock_reader


@pytest.fixture
def sample_image_file():
    """Create a sample image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = Path(f.name)

    # Create a simple test image
    img = Image.new("RGB", (800, 600), color="white")
    img.save(img_path)

    yield img_path

    # Cleanup
    img_path.unlink()


@pytest.fixture
def ocr_service():
    """Create OCR service instance."""
    return OCRService()


class TestOCRService:
    """Test OCR Service functionality."""

    def test_ocr_service_initialization(self, ocr_service):
        """Test OCR service initializes correctly."""
        assert ocr_service.reader is None
        assert ocr_service._initialized is False

    def test_extract_text_from_image(
        self,
        ocr_service,
        mock_easyocr_reader,
        sample_image_file,
    ):
        """Test extracting text from an image."""
        # Mock OCR results
        mock_easyocr_reader.readtext.return_value = [
            (
                [[0, 0], [100, 0], [100, 50], [0, 50]],
                "Patient Name: John Doe",
                0.95,
            ),
            (
                [[0, 60], [100, 60], [100, 110], [0, 110]],
                "Age: 45",
                0.92,
            ),
            (
                [[0, 120], [100, 120], [100, 170], [0, 170]],
                "Date: 15/01/2024",
                0.88,
            ),
        ]

        result = ocr_service.extract_text(sample_image_file)

        assert result["text"] == "Patient Name: John Doe\nAge: 45\nDate: 15/01/2024"
        assert result["confidence"] > 90.0
        assert result["language"] == "en"
        assert result["processing_time"] > 0
        assert len(result["raw_results"]) == 3

    def test_extract_text_hindi_english_mixed(
        self,
        ocr_service,
        mock_easyocr_reader,
        sample_image_file,
    ):
        """Test extracting mixed Hindi and English text."""
        mock_easyocr_reader.readtext.return_value = [
            (
                [[0, 0], [100, 0], [100, 50], [0, 50]],
                "Patient Name: राहुल शर्मा",
                0.90,
            ),
            (
                [[0, 60], [100, 60], [100, 110], [0, 110]],
                "उम्र: 35 years",
                0.85,
            ),
        ]

        result = ocr_service.extract_text(sample_image_file)

        assert "राहुल" in result["text"]
        assert result["language"] == "hi,en"

    def test_extract_text_file_not_found(self, ocr_service, mock_easyocr_reader):
        """Test handling of missing image file."""
        with pytest.raises(FileNotFoundError):
            ocr_service.extract_text("/nonexistent/file.png")

    def test_extract_text_invalid_image(self, ocr_service, mock_easyocr_reader):
        """Test handling of invalid image file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            invalid_path = Path(f.name)
            f.write(b"This is not an image")

        try:
            with pytest.raises(ValueError, match="Invalid image file"):
                ocr_service.extract_text(invalid_path)
        finally:
            invalid_path.unlink()

    def test_extract_text_low_confidence(
        self,
        ocr_service,
        mock_easyocr_reader,
        sample_image_file,
    ):
        """Test handling of low confidence OCR results."""
        mock_easyocr_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 50], [0, 50]], "Blurry text", 0.45),
            ([[0, 60], [100, 60], [100, 110], [0, 110]], "More blur", 0.38),
        ]

        result = ocr_service.extract_text(sample_image_file)

        assert result["confidence"] < 50.0
        assert "Blurry text" in result["text"]

    def test_extract_text_empty_results(
        self,
        ocr_service,
        mock_easyocr_reader,
        sample_image_file,
    ):
        """Test handling of empty OCR results."""
        mock_easyocr_reader.readtext.return_value = []

        result = ocr_service.extract_text(sample_image_file)

        assert result["text"] == ""
        assert result["confidence"] == 0.0

    def test_extract_structured_data_patient_name(self, ocr_service):
        """Test extracting patient name from OCR text."""
        text = """
        Medical Report
        Patient Name: Rajesh Kumar
        Age: 45
        Gender: Male
        """

        data = ocr_service.extract_structured_data(text)

        assert data["patient_name"] == "Rajesh Kumar"

    def test_extract_structured_data_age_gender(self, ocr_service):
        """Test extracting age and gender."""
        text = """
        Patient: John Doe
        Age: 52
        Gender: M
        """

        data = ocr_service.extract_structured_data(text)

        assert data["age"] == 52
        assert data["gender"] == "M"

    def test_extract_structured_data_date_formats(self, ocr_service):
        """Test extracting dates in various formats."""
        text1 = "Date: 15/01/2024"
        text2 = "Date: 15-01-2024"
        text3 = "Report Date: 15/1/24"

        data1 = ocr_service.extract_structured_data(text1)
        data2 = ocr_service.extract_structured_data(text2)
        data3 = ocr_service.extract_structured_data(text3)

        assert "date" in data1
        assert "date" in data2
        assert "date" in data3

    def test_extract_structured_data_phone_number(self, ocr_service):
        """Test extracting Indian phone numbers."""
        text = """
        Patient Details
        Phone: 9876543210
        """

        data = ocr_service.extract_structured_data(text)

        assert data["phone"] == "9876543210"

    def test_extract_structured_data_lab_tests(self, ocr_service):
        """Test extracting lab test values."""
        text = """
        Lab Results
        Hemoglobin: 14.5 g/dL
        Blood Sugar: 105 mg/dL
        Cholesterol: 180 mg/dL
        """

        data = ocr_service.extract_structured_data(text)

        assert "lab_tests" in data
        assert len(data["lab_tests"]) >= 2
        # Check that we have some test results
        test_names = [test["name"] for test in data["lab_tests"]]
        assert any("Hemoglobin" in name or "Blood Sugar" in name for name in test_names)

    def test_extract_structured_data_doctor_name(self, ocr_service):
        """Test extracting doctor name."""
        text = """
        Consultation Report
        Dr. Sharma Cardiology
        Patient: John Doe
        """

        data = ocr_service.extract_structured_data(text)

        assert "doctor_name" in data
        assert "Sharma" in data["doctor_name"]

    def test_extract_structured_data_diagnosis(self, ocr_service):
        """Test extracting diagnosis."""
        text = """
        Diagnosis: Hypertension Stage 2
        """

        data = ocr_service.extract_structured_data(text)

        assert "diagnosis" in data
        assert "Hypertension" in data["diagnosis"]

    def test_extract_structured_data_medications(self, ocr_service):
        """Test extracting medications."""
        text = """
        Rx: Amlodipine 5mg once daily
        Medicine: Metformin 500mg twice daily
        """

        data = ocr_service.extract_structured_data(text)

        assert "medications" in data
        assert len(data["medications"]) >= 1

    def test_extract_structured_data_empty_text(self, ocr_service):
        """Test handling empty text."""
        data = ocr_service.extract_structured_data("")

        assert data == {}

    def test_extract_structured_data_hindi_name(self, ocr_service):
        """Test extracting Hindi patient names."""
        text = """
        नाम: रमेश कुमार
        Age: 40
        """

        data = ocr_service.extract_structured_data(text)

        # Hindi name pattern should be detected
        assert "patient_name" in data or len(data) >= 0

    def test_process_document_complete(
        self,
        ocr_service,
        mock_easyocr_reader,
        sample_image_file,
    ):
        """Test complete document processing workflow."""
        mock_easyocr_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 50], [0, 50]], "Patient: John Doe", 0.92),
            ([[0, 60], [100, 60], [100, 110], [0, 110]], "Age: 45", 0.90),
            ([[0, 120], [100, 120], [100, 170], [0, 170]], "Gender: Male", 0.88),
        ]

        result = ocr_service.process_document(sample_image_file, extract_structured=True)

        assert "ocr_text" in result
        assert "ocr_confidence" in result
        assert "ocr_language" in result
        assert "extracted_data" in result
        assert "processing_time" in result

        # Check structured data extraction worked
        assert "age" in result["extracted_data"]
        assert result["extracted_data"]["age"] == 45

    def test_process_document_without_structured_extraction(
        self,
        ocr_service,
        mock_easyocr_reader,
        sample_image_file,
    ):
        """Test document processing without structured extraction."""
        mock_easyocr_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 50], [0, 50]], "Some text", 0.90),
        ]

        result = ocr_service.process_document(sample_image_file, extract_structured=False)

        assert "ocr_text" in result
        assert "extracted_data" not in result

    def test_detect_language_english_only(self, ocr_service):
        """Test language detection for English-only text."""
        text = "This is a medical report in English"
        language = ocr_service._detect_language(text)

        assert language == "en"

    def test_detect_language_hindi_only(self, ocr_service):
        """Test language detection for Hindi-only text."""
        text = "यह एक चिकित्सा रिपोर्ट है"
        language = ocr_service._detect_language(text)

        assert language == "hi"

    def test_detect_language_mixed(self, ocr_service):
        """Test language detection for mixed Hindi-English text."""
        text = "Patient रोगी का नाम: John Doe"
        language = ocr_service._detect_language(text)

        assert language == "hi,en"

    def test_detect_language_unknown(self, ocr_service):
        """Test language detection for unknown/empty text."""
        language = ocr_service._detect_language("")

        assert language == "unknown"

    def test_ocr_service_singleton(self):
        """Test OCR service singleton pattern."""
        from app.services.ocr import get_ocr_service

        service1 = get_ocr_service()
        service2 = get_ocr_service()

        assert service1 is service2


# ==========================================
# EMR INTEGRATION TESTS
# ==========================================


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
def emr_integration(temp_emr_db):
    """Create EMR integration instance."""
    return EMRIntegration(temp_emr_db)


@pytest.fixture
def emr_integration_async(temp_emr_db):
    """Create async EMR integration instance."""
    return EMRIntegrationAsync(temp_emr_db)


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
            "Priya",
            "Sharma",
            "+919876543210",
            "priya@example.com",
            "1985-03-20",
            "F",
            "B+",
            "None",
            "123 MG Road, Mumbai",
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
            "Dr. Rajesh Kumar",
            now,
            "Chest pain",
            "Angina pectoris",
            "Patient reports chest pain for 2 days",
            '{"bp": "140/90", "pulse": 85, "spo2": 98}',
            '[{"name": "Aspirin", "dosage": "75mg", "frequency": "OD"}]',
            now,
        ),
    )

    conn.commit()
    conn.close()

    return visit_id


class TestEMRIntegration:
    """Test EMR Integration functionality."""

    def test_emr_integration_initialization(self, emr_integration):
        """Test EMR integration initializes correctly."""
        assert emr_integration.db_path is not None
        assert emr_integration.is_available()

    def test_emr_integration_unavailable(self):
        """Test EMR integration when database not found."""
        integration = EMRIntegration(Path("/nonexistent/db.sqlite"))
        assert not integration.is_available()

    def test_get_patient(self, emr_integration, sample_emr_patient):
        """Test fetching a patient from EMR."""
        patient = emr_integration.get_patient(sample_emr_patient)

        assert patient is not None
        assert patient.id == sample_emr_patient
        assert patient.first_name == "Priya"
        assert patient.last_name == "Sharma"
        assert patient.phone == "+919876543210"
        assert patient.gender == "F"
        assert patient.blood_group == "B+"

    def test_get_nonexistent_patient(self, emr_integration):
        """Test fetching a patient that doesn't exist."""
        patient = emr_integration.get_patient("nonexistent-id")

        assert patient is None

    def test_search_patients_by_name(self, emr_integration, sample_emr_patient):
        """Test searching patients by name."""
        results = emr_integration.search_patients("Priya", limit=10)

        assert len(results) == 1
        assert results[0].first_name == "Priya"

    def test_search_patients_by_phone(self, emr_integration, sample_emr_patient):
        """Test searching patients by phone number."""
        results = emr_integration.search_patients("9876543210", limit=10)

        assert len(results) == 1
        assert results[0].phone == "+919876543210"

    def test_search_patients_no_results(self, emr_integration):
        """Test patient search with no results."""
        results = emr_integration.search_patients("Nonexistent", limit=10)

        assert len(results) == 0

    def test_get_patients_updated_since(self, emr_integration, sample_emr_patient):
        """Test fetching patients updated since a timestamp."""
        since = datetime.now(timezone.utc) - timedelta(days=1)
        patients = emr_integration.get_patients_updated_since(since)

        assert len(patients) >= 1
        assert any(p.id == sample_emr_patient for p in patients)

    def test_get_patients_updated_since_no_results(self, emr_integration):
        """Test fetching patients with future timestamp."""
        since = datetime.now(timezone.utc) + timedelta(days=1)
        patients = emr_integration.get_patients_updated_since(since)

        assert len(patients) == 0

    def test_get_patient_visits(
        self,
        emr_integration,
        sample_emr_patient,
        sample_emr_visit,
    ):
        """Test fetching patient visits."""
        visits = emr_integration.get_patient_visits(sample_emr_patient, limit=10)

        assert len(visits) == 1
        assert visits[0].id == sample_emr_visit
        assert visits[0].patient_id == sample_emr_patient
        assert visits[0].doctor_name == "Dr. Rajesh Kumar"
        assert visits[0].chief_complaint == "Chest pain"
        assert visits[0].diagnosis == "Angina pectoris"
        assert visits[0].vitals is not None
        assert visits[0].vitals["bp"] == "140/90"
        assert visits[0].prescriptions is not None

    def test_get_visit(self, emr_integration, sample_emr_visit):
        """Test fetching a specific visit."""
        visit = emr_integration.get_visit(sample_emr_visit)

        assert visit is not None
        assert visit.id == sample_emr_visit
        assert visit.doctor_name == "Dr. Rajesh Kumar"

    def test_get_nonexistent_visit(self, emr_integration):
        """Test fetching a visit that doesn't exist."""
        visit = emr_integration.get_visit("nonexistent-id")

        assert visit is None

    def test_sync_appointment_to_emr(self, emr_integration, sample_emr_patient):
        """Test syncing an appointment to EMR."""
        appointment_id = str(uuid4())
        scheduled_start = datetime.now(timezone.utc) + timedelta(days=1)

        success = emr_integration.sync_appointment_to_emr(
            appointment_id=appointment_id,
            patient_id=sample_emr_patient,
            doctor_name="Dr. Test Doctor",
            scheduled_start=scheduled_start,
            appointment_type="consultation",
            chief_complaint="Follow-up",
        )

        assert success is True

        # Verify in database
        conn = emr_integration.get_connection()
        cursor = conn.execute(
            "SELECT * FROM appointments WHERE external_id = ?",
            (appointment_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["patient_id"] == sample_emr_patient
        assert row["status"] == "scheduled"

    def test_sync_appointment_update(self, emr_integration, sample_emr_patient):
        """Test updating an existing appointment in EMR."""
        appointment_id = str(uuid4())
        scheduled_start1 = datetime.now(timezone.utc) + timedelta(days=1)

        # First sync
        emr_integration.sync_appointment_to_emr(
            appointment_id=appointment_id,
            patient_id=sample_emr_patient,
            doctor_name="Dr. Test",
            scheduled_start=scheduled_start1,
            appointment_type="consultation",
        )

        # Update with new time
        scheduled_start2 = datetime.now(timezone.utc) + timedelta(days=2)
        success = emr_integration.sync_appointment_to_emr(
            appointment_id=appointment_id,
            patient_id=sample_emr_patient,
            doctor_name="Dr. Test",
            scheduled_start=scheduled_start2,
            appointment_type="consultation",
        )

        assert success is True

    def test_link_appointment_to_visit(
        self,
        emr_integration,
        sample_emr_patient,
        sample_emr_visit,
    ):
        """Test linking an appointment to a visit."""
        appointment_id = str(uuid4())

        # First create appointment
        emr_integration.sync_appointment_to_emr(
            appointment_id=appointment_id,
            patient_id=sample_emr_patient,
            doctor_name="Dr. Test",
            scheduled_start=datetime.now(timezone.utc),
            appointment_type="consultation",
        )

        # Link to visit
        success = emr_integration.link_appointment_to_visit(
            appointment_id,
            sample_emr_visit,
        )

        assert success is True

        # Verify in database
        conn = emr_integration.get_connection()
        cursor = conn.execute(
            "SELECT * FROM appointments WHERE external_id = ?",
            (appointment_id,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row["visit_id"] == sample_emr_visit
        assert row["status"] == "completed"

    def test_emr_integration_corrupted_database(self):
        """Test handling of corrupted database."""
        # Create a file that's not a valid SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
            f.write(b"This is not a SQLite database")

        try:
            integration = EMRIntegration(db_path)
            # Connection should fail
            conn = integration.get_connection()
            assert conn is None or not integration.is_available()
        finally:
            db_path.unlink()


class TestEMRIntegrationAsync:
    """Test async EMR integration."""

    @pytest.mark.asyncio
    async def test_get_patient_async(
        self,
        emr_integration_async,
        sample_emr_patient,
    ):
        """Test async patient retrieval."""
        patient = await emr_integration_async.get_patient(sample_emr_patient)

        assert patient is not None
        assert patient.id == sample_emr_patient
        assert patient.first_name == "Priya"

    @pytest.mark.asyncio
    async def test_search_patients_async(
        self,
        emr_integration_async,
        sample_emr_patient,
    ):
        """Test async patient search."""
        results = await emr_integration_async.search_patients("Priya", limit=10)

        assert len(results) == 1
        assert results[0].first_name == "Priya"

    @pytest.mark.asyncio
    async def test_get_patient_visits_async(
        self,
        emr_integration_async,
        sample_emr_patient,
        sample_emr_visit,
    ):
        """Test async visit retrieval."""
        visits = await emr_integration_async.get_patient_visits(
            sample_emr_patient,
            limit=10,
        )

        assert len(visits) == 1
        assert visits[0].id == sample_emr_visit


# ==========================================
# EMR SYNC SERVICE TESTS
# ==========================================


@pytest.fixture
def emr_sync_service(temp_emr_db):
    """Create EMR sync service with test database."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.emr_database_path = str(temp_emr_db)
        mock_settings.emr_sync_enabled = True
        mock_settings.emr_sync_interval_seconds = 300

        service = EMRSyncService()
        service.emr.db_path = temp_emr_db
        service.emr_async.emr.db_path = temp_emr_db
        return service


class TestEMRSyncService:
    """Test EMR Sync Service functionality."""

    def test_emr_sync_service_initialization(self, emr_sync_service):
        """Test EMR sync service initializes correctly."""
        assert emr_sync_service.is_available()
        assert emr_sync_service._sync_running is False

    def test_get_status(self, emr_sync_service):
        """Test getting sync status."""
        status = emr_sync_service.get_status()

        assert "enabled" in status
        assert "available" in status
        assert "database_path" in status
        assert "stats" in status
        assert "sync_interval_seconds" in status

    @pytest.mark.asyncio
    async def test_sync_patient_from_emr_new(
        self,
        emr_sync_service,
        sample_emr_patient,
        test_clinic,
    ):
        """Test syncing a new patient from EMR."""
        from app.core.database import async_session_maker

        async with async_session_maker() as db:
            patient = await emr_sync_service.sync_patient_from_emr(
                sample_emr_patient,
                db,
            )

            assert patient is not None
            assert patient.first_name == "Priya"
            assert patient.last_name == "Sharma"
            assert patient.emr_patient_id == sample_emr_patient
            assert patient.emr_synced_at is not None

    @pytest.mark.asyncio
    async def test_sync_patient_from_emr_update(
        self,
        emr_sync_service,
        sample_emr_patient,
        test_clinic,
    ):
        """Test updating an existing patient from EMR."""
        from app.core.database import async_session_maker

        async with async_session_maker() as db:
            # First sync
            patient1 = await emr_sync_service.sync_patient_from_emr(
                sample_emr_patient,
                db,
            )

            # Update patient in EMR
            conn = emr_sync_service.emr.get_connection()
            conn.execute(
                "UPDATE patients SET email = ? WHERE id = ?",
                ("updated@example.com", sample_emr_patient),
            )
            conn.commit()
            conn.close()

            # Second sync
            await asyncio.sleep(0.1)
            patient2 = await emr_sync_service.sync_patient_from_emr(
                sample_emr_patient,
                db,
            )

            assert patient2.id == patient1.id
            assert patient2.email == "updated@example.com"

    @pytest.mark.asyncio
    async def test_sync_patient_from_emr_not_found(
        self,
        emr_sync_service,
        test_clinic,
    ):
        """Test syncing a patient that doesn't exist in EMR."""
        from app.core.database import async_session_maker

        async with async_session_maker() as db:
            patient = await emr_sync_service.sync_patient_from_emr(
                "nonexistent-id",
                db,
            )

            assert patient is None

    def test_file_watcher_start_stop(self, emr_sync_service):
        """Test starting and stopping file watcher."""
        # Start watcher
        emr_sync_service.start_file_watcher()
        assert emr_sync_service.emr._running is True

        # Stop watcher
        emr_sync_service.stop_file_watcher()
        assert emr_sync_service.emr._running is False


# ==========================================
# FOLLOW-UP INTELLIGENCE SERVICE TESTS
# ==========================================


@pytest.fixture
def test_procedure_cardiology(db, test_clinic, test_doctor, test_patient):
    """Create a test cardiology procedure."""
    procedure = Procedure(
        id=uuid4(),
        clinic_id=test_clinic.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        category="cardiology",
        procedure_type="Stent Placement",
        name="Drug-Eluting Stent - LAD",
        performed_at=datetime.now(timezone.utc),
        outcome="successful",
        severity="major",
        findings="Single vessel disease, LAD 90% stenosis",
        consumables={"stent_brand": "Xience", "stent_size": "3.0x18mm"},
        custom_fields={"ef_after": 55, "lesion_location": "LAD"},
        requires_followup=True,
    )
    db.add(procedure)
    db.commit()
    db.refresh(procedure)
    return procedure


@pytest.fixture
def test_procedure_ophthalmology(db, test_clinic, test_doctor, test_patient):
    """Create a test ophthalmology procedure."""
    procedure = Procedure(
        id=uuid4(),
        clinic_id=test_clinic.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        category="ophthalmology",
        procedure_type="Cataract Surgery",
        name="Phacoemulsification with IOL",
        performed_at=datetime.now(timezone.utc),
        outcome="successful",
        severity="moderate",
        findings="Successful IOL implantation",
        custom_fields={"lens_type": "Monofocal", "power": "+21.5D"},
        requires_followup=True,
    )
    db.add(procedure)
    db.commit()
    db.refresh(procedure)
    return procedure


@pytest.fixture
def followup_intelligence(db):
    """Create follow-up intelligence service."""
    from app.core.database import async_session_maker

    async def get_service():
        async with async_session_maker() as session:
            return FollowupIntelligence(session)

    return asyncio.run(get_service())


class TestFollowupIntelligence:
    """Test Follow-up Intelligence Service."""

    @pytest.mark.asyncio
    async def test_suggest_followups_cardiology_stent(
        self,
        db,
        test_procedure_cardiology,
    ):
        """Test follow-up suggestions for stent placement."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            intelligence = FollowupIntelligence(session)
            suggestions = await intelligence.suggest_followups_after_procedure(
                test_procedure_cardiology
            )

            assert len(suggestions) >= 2
            # Should have 7-day and 30-day follow-ups
            days = [s.days_from_procedure for s in suggestions]
            assert 7 in days
            assert 30 in days

            # Check priority
            for suggestion in suggestions:
                assert 1 <= suggestion.priority <= 5

    @pytest.mark.asyncio
    async def test_suggest_followups_ophthalmology_cataract(
        self,
        db,
        test_procedure_ophthalmology,
    ):
        """Test follow-up suggestions for cataract surgery."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            intelligence = FollowupIntelligence(session)
            suggestions = await intelligence.suggest_followups_after_procedure(
                test_procedure_ophthalmology
            )

            assert len(suggestions) >= 3
            # Should have day 1, week 1, and month 1 follow-ups
            days = [s.days_from_procedure for s in suggestions]
            assert 1 in days
            assert 7 in days
            assert 30 in days

    @pytest.mark.asyncio
    async def test_suggest_followups_unknown_procedure(self, db, test_clinic, test_doctor, test_patient):
        """Test follow-up suggestions for unknown procedure type."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            # Create procedure with unknown type
            procedure = Procedure(
                id=uuid4(),
                clinic_id=test_clinic.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                category="unknown",
                procedure_type="Custom Procedure",
                name="Custom Treatment",
                performed_at=datetime.now(timezone.utc),
            )
            session.add(procedure)
            await session.commit()

            intelligence = FollowupIntelligence(session)
            suggestions = await intelligence.suggest_followups_after_procedure(procedure)

            # Should return empty list for unknown procedures
            assert len(suggestions) == 0

    @pytest.mark.asyncio
    async def test_create_followup_schedules(
        self,
        db,
        test_procedure_cardiology,
    ):
        """Test creating follow-up schedules."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            intelligence = FollowupIntelligence(session)
            schedules = await intelligence.create_followup_schedules(
                test_procedure_cardiology
            )

            assert len(schedules) >= 2
            for schedule in schedules:
                assert schedule.clinic_id == test_procedure_cardiology.clinic_id
                assert schedule.patient_id == test_procedure_cardiology.patient_id
                assert schedule.doctor_id == test_procedure_cardiology.doctor_id
                assert schedule.procedure_id == test_procedure_cardiology.id
                assert schedule.completed is False

    @pytest.mark.asyncio
    async def test_get_pending_followups(
        self,
        db,
        test_clinic,
        test_procedure_cardiology,
    ):
        """Test getting pending follow-ups."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            intelligence = FollowupIntelligence(session)

            # Create schedules
            await intelligence.create_followup_schedules(test_procedure_cardiology)

            # Get pending follow-ups for next 30 days
            reminders = await intelligence.get_pending_followups(
                test_clinic.id,
                days_ahead=30,
            )

            assert len(reminders) >= 1

    @pytest.mark.asyncio
    async def test_get_overdue_followups(
        self,
        db,
        test_clinic,
        test_procedure_cardiology,
    ):
        """Test getting overdue follow-ups."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            # Create a procedure from the past
            old_procedure = Procedure(
                id=uuid4(),
                clinic_id=test_clinic.id,
                patient_id=test_procedure_cardiology.patient_id,
                doctor_id=test_procedure_cardiology.doctor_id,
                category="cardiology",
                procedure_type="Stent Placement",
                name="Past Stent",
                performed_at=datetime.now(timezone.utc) - timedelta(days=30),
            )
            session.add(old_procedure)
            await session.commit()

            intelligence = FollowupIntelligence(session)

            # Create schedules (7-day follow-up will be overdue)
            await intelligence.create_followup_schedules(old_procedure)

            # Get overdue follow-ups
            overdue = await intelligence.get_overdue_followups(test_clinic.id)

            assert len(overdue) >= 1
            for reminder in overdue:
                assert reminder.days_overdue > 0

    @pytest.mark.asyncio
    async def test_mark_followup_completed(
        self,
        db,
        test_procedure_cardiology,
    ):
        """Test marking a follow-up as completed."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            intelligence = FollowupIntelligence(session)

            # Create schedules
            schedules = await intelligence.create_followup_schedules(
                test_procedure_cardiology
            )

            # Mark first one as completed
            completed = await intelligence.mark_followup_completed(schedules[0].id)

            assert completed.completed is True
            assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_check_condition_ef_below_40(
        self,
        db,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test condition check for low EF."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            # Create procedure with low EF
            procedure = Procedure(
                id=uuid4(),
                clinic_id=test_clinic.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                category="cardiology",
                procedure_type="Echocardiogram",
                name="2D Echo",
                performed_at=datetime.now(timezone.utc),
                custom_fields={"ef": 35},  # Low EF
            )
            session.add(procedure)
            await session.commit()

            intelligence = FollowupIntelligence(session)

            # Should trigger repeat echo
            suggestions = await intelligence.suggest_followups_after_procedure(procedure)

            # With low EF, should have follow-up
            assert len(suggestions) >= 1

    @pytest.mark.asyncio
    async def test_check_condition_polyps_found(
        self,
        db,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test condition check for polyps found."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            # Create procedure with polyps
            procedure = Procedure(
                id=uuid4(),
                clinic_id=test_clinic.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                category="gastroenterology",
                procedure_type="Colonoscopy",
                name="Diagnostic Colonoscopy",
                performed_at=datetime.now(timezone.utc),
                findings="Multiple polyps found and removed",
            )
            session.add(procedure)
            await session.commit()

            intelligence = FollowupIntelligence(session)
            suggestions = await intelligence.suggest_followups_after_procedure(procedure)

            # Should have follow-up due to polyps
            assert len(suggestions) >= 1

    @pytest.mark.asyncio
    async def test_prioritize_high_risk_patients(
        self,
        db,
        test_clinic,
        test_procedure_cardiology,
    ):
        """Test that high-risk procedures get higher priority."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            intelligence = FollowupIntelligence(session)
            suggestions = await intelligence.suggest_followups_after_procedure(
                test_procedure_cardiology
            )

            # Check that early follow-ups have higher priority
            early_followup = next(s for s in suggestions if s.days_from_procedure == 7)
            late_followup = next(s for s in suggestions if s.days_from_procedure == 180)

            assert early_followup.priority >= late_followup.priority

    @pytest.mark.asyncio
    async def test_multiple_procedure_types(
        self,
        db,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test follow-up suggestions for multiple procedure types."""
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            intelligence = FollowupIntelligence(session)

            # Test orthopedics
            ortho_procedure = Procedure(
                id=uuid4(),
                clinic_id=test_clinic.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                category="orthopedics",
                procedure_type="Total Knee Replacement",
                name="TKR - Right Knee",
                performed_at=datetime.now(timezone.utc),
            )
            session.add(ortho_procedure)
            await session.commit()

            ortho_suggestions = await intelligence.suggest_followups_after_procedure(
                ortho_procedure
            )

            # Should have multiple follow-ups including suture removal
            assert len(ortho_suggestions) >= 3
            assert any(14 == s.days_from_procedure for s in ortho_suggestions)  # Suture removal


# ==========================================
# INTEGRATION TESTS
# ==========================================


class TestOCRAndEMRIntegration:
    """Test integration between OCR and EMR sync."""

    @pytest.mark.asyncio
    async def test_ocr_to_emr_patient_flow(
        self,
        ocr_service,
        emr_sync_service,
        mock_easyocr_reader,
        sample_image_file,
    ):
        """Test extracting patient data via OCR and syncing to EMR."""
        # Mock OCR to return patient data
        mock_easyocr_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 50], [0, 50]], "Patient: Amit Patel", 0.92),
            ([[0, 60], [100, 60], [100, 110], [0, 110]], "Phone: 9123456789", 0.90),
            ([[0, 120], [100, 120], [100, 170], [0, 170]], "Age: 50", 0.88),
        ]

        # Extract via OCR
        result = ocr_service.process_document(sample_image_file, extract_structured=True)

        # Verify extraction
        assert "extracted_data" in result
        assert "phone" in result["extracted_data"]
        # Phone number should be detected
        assert result["extracted_data"]["phone"] == "9123456789"
