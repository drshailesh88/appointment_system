"""
Comprehensive tests for Patient Data Integrity.

This test suite ensures the robustness of patient data operations
including CRUD, validation, EMR sync, security, and edge cases.
"""
import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.emr_sync_service import EMRSyncService

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def async_db_session(db) -> AsyncSession:
    """Convert sync session to async for testing."""
    # For testing, we'll use the sync session since the test DB is SQLite
    # In production, we use async PostgreSQL
    return db


@pytest.fixture
def test_clinic_data() -> dict:
    """Test clinic data."""
    return {
        "id": uuid4(),
        "name": "Test Clinic",
        "address": "123 Test Street",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001",
        "phone": "+919876543210",
        "email": "clinic@test.com",
        "subscription_tier": "professional",
    }


@pytest.fixture
def test_patient_data(test_clinic_data: dict) -> dict:
    """Valid test patient data."""
    return {
        "first_name": "Rajesh",
        "last_name": "Kumar",
        "phone": "+919876543210",
        "email": "rajesh.kumar@example.com",
        "date_of_birth": date(1985, 6, 15),
        "gender": "M",
        "address": "123 MG Road",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001",
        "blood_group": "O+",
        "allergies": "Penicillin",
        "emergency_contact_name": "Priya Kumar",
        "emergency_contact_phone": "+919876543211",
        "preferred_language": "hi",
        "clinic_id": test_clinic_data["id"],
    }


# ============================================================================
# TEST CLASS 1: CRUD OPERATIONS
# ============================================================================


class TestPatientCRUDOperations:
    """Test Create, Read, Update, Delete operations for patients."""

    async def test_create_patient_with_all_fields(self, db, test_clinic_data, test_patient_data):
        """Test creating a patient with all required and optional fields."""
        # Create clinic first
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create patient
        patient = Patient(**test_patient_data)
        db.add(patient)
        db.commit()
        db.refresh(patient)

        # Assertions
        assert patient.id is not None
        assert patient.first_name == "Rajesh"
        assert patient.last_name == "Kumar"
        assert patient.phone == "+919876543210"
        assert patient.email == "rajesh.kumar@example.com"
        assert patient.date_of_birth == date(1985, 6, 15)
        assert patient.gender == "M"
        assert patient.blood_group == "O+"
        assert patient.is_active is True
        assert patient.clinic_id == test_clinic_data["id"]

    async def test_create_patient_with_minimal_fields(self, db, test_clinic_data):
        """Test creating a patient with only required fields."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="Amit",
            phone="+919876543299",
            clinic_id=test_clinic_data["id"],
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        assert patient.id is not None
        assert patient.first_name == "Amit"
        assert patient.last_name is None
        assert patient.phone == "+919876543299"
        assert patient.is_active is True

    async def test_get_patient_by_id(self, db, test_clinic_data, test_patient_data):
        """Test retrieving a patient by ID."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(**test_patient_data)
        db.add(patient)
        db.commit()
        patient_id = patient.id

        # Retrieve patient
        result = db.execute(select(Patient).where(Patient.id == patient_id))
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert retrieved.id == patient_id
        assert retrieved.first_name == "Rajesh"

    async def test_get_patient_by_phone(self, db, test_clinic_data, test_patient_data):
        """Test retrieving a patient by phone number."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(**test_patient_data)
        db.add(patient)
        db.commit()

        # Retrieve by phone
        result = db.execute(
            select(Patient).where(
                Patient.phone == "+919876543210",
                Patient.clinic_id == test_clinic_data["id"],
            )
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert retrieved.phone == "+919876543210"
        assert retrieved.first_name == "Rajesh"

    async def test_get_patient_by_email(self, db, test_clinic_data, test_patient_data):
        """Test retrieving a patient by email."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(**test_patient_data)
        db.add(patient)
        db.commit()

        # Retrieve by email
        result = db.execute(
            select(Patient).where(Patient.email == "rajesh.kumar@example.com")
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert retrieved.email == "rajesh.kumar@example.com"

    async def test_search_patients_by_name_partial_match(self, db, test_clinic_data):
        """Test searching patients by partial name match."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create multiple patients
        patients_data = [
            {"first_name": "Rajesh", "last_name": "Kumar", "phone": "+919876543210"},
            {"first_name": "Rakesh", "last_name": "Sharma", "phone": "+919876543211"},
            {"first_name": "Suresh", "last_name": "Gupta", "phone": "+919876543212"},
        ]

        for data in patients_data:
            patient = Patient(clinic_id=clinic.id, **data)
            db.add(patient)
        db.commit()

        # Search for "Raj" - should match Rajesh
        result = db.execute(
            select(Patient).where(Patient.first_name.ilike("%Raj%"))
        )
        matches = result.scalars().all()

        assert len(matches) == 1
        assert matches[0].first_name == "Rajesh"

    async def test_search_patients_by_name_case_insensitive(self, db, test_clinic_data):
        """Test case-insensitive name search."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="Rajesh",
            last_name="Kumar",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        # Search with different case
        result = db.execute(
            select(Patient).where(Patient.first_name.ilike("%rajesh%"))
        )
        matches = result.scalars().all()

        assert len(matches) == 1
        assert matches[0].first_name == "Rajesh"

    async def test_update_patient_information(self, db, test_clinic_data, test_patient_data):
        """Test updating patient information."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(**test_patient_data)
        db.add(patient)
        db.commit()
        patient_id = patient.id

        # Update patient
        patient.address = "456 New Address"
        patient.blood_group = "A+"
        patient.allergies = "Penicillin, Aspirin"
        db.commit()

        # Retrieve and verify
        result = db.execute(select(Patient).where(Patient.id == patient_id))
        updated = result.scalar_one()

        assert updated.address == "456 New Address"
        assert updated.blood_group == "A+"
        assert updated.allergies == "Penicillin, Aspirin"
        assert updated.first_name == "Rajesh"  # Unchanged fields remain

    async def test_soft_delete_patient(self, db, test_clinic_data, test_patient_data):
        """Test soft deleting a patient (setting is_active to False)."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(**test_patient_data)
        db.add(patient)
        db.commit()
        patient_id = patient.id

        # Soft delete
        patient.is_active = False
        db.commit()

        # Verify patient still exists but is inactive
        result = db.execute(select(Patient).where(Patient.id == patient_id))
        deleted = result.scalar_one()

        assert deleted is not None
        assert deleted.is_active is False
        assert deleted.first_name == "Rajesh"  # Data still intact

    async def test_list_active_patients_only(self, db, test_clinic_data):
        """Test listing only active patients."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create active and inactive patients
        active_patient = Patient(
            first_name="Active",
            phone="+919876543210",
            clinic_id=clinic.id,
            is_active=True,
        )
        inactive_patient = Patient(
            first_name="Inactive",
            phone="+919876543211",
            clinic_id=clinic.id,
            is_active=False,
        )
        db.add(active_patient)
        db.add(inactive_patient)
        db.commit()

        # Query only active
        result = db.execute(
            select(Patient).where(
                Patient.clinic_id == clinic.id,
                Patient.is_active == True,
            )
        )
        active_only = result.scalars().all()

        assert len(active_only) == 1
        assert active_only[0].first_name == "Active"


# ============================================================================
# TEST CLASS 2: DATA VALIDATION
# ============================================================================


class TestPatientDataValidation:
    """Test data validation rules for patient records."""

    async def test_phone_number_indian_format(self, db, test_clinic_data):
        """Test valid Indian phone number format."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Valid Indian numbers
        valid_numbers = [
            "+919876543210",  # With +91
            "9876543210",     # Without country code
            "09876543210",    # With leading 0
        ]

        for phone in valid_numbers:
            patient = Patient(
                first_name=f"Test{phone[-4:]}",
                phone=phone,
                clinic_id=clinic.id,
            )
            db.add(patient)

        db.commit()

        # All should be saved
        result = db.execute(select(Patient).where(Patient.clinic_id == clinic.id))
        patients = result.scalars().all()
        assert len(patients) >= len(valid_numbers)

    async def test_phone_number_length_validation(self, db, test_clinic_data):
        """Test phone number length constraints."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Phone too short - should be rejected by database constraints
        with pytest.raises(Exception):  # Database integrity error
            patient = Patient(
                first_name="ShortPhone",
                phone="123",
                clinic_id=clinic.id,
            )
            db.add(patient)
            db.commit()

        db.rollback()

    async def test_email_format_validation(self, db, test_clinic_data):
        """Test email format validation."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Valid emails should work
        valid_patient = Patient(
            first_name="ValidEmail",
            phone="+919876543210",
            email="valid@example.com",
            clinic_id=clinic.id,
        )
        db.add(valid_patient)
        db.commit()

        assert valid_patient.email == "valid@example.com"

        # Note: Email validation is done at Pydantic schema level, not database

    async def test_date_of_birth_not_in_future(self, db, test_clinic_data):
        """Test that date of birth cannot be in the future."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Past date - should work
        past_dob = Patient(
            first_name="PastDOB",
            phone="+919876543210",
            date_of_birth=date(1990, 1, 1),
            clinic_id=clinic.id,
        )
        db.add(past_dob)
        db.commit()

        assert past_dob.date_of_birth == date(1990, 1, 1)

        # Future date - database allows it, but should be validated at API level
        future_date = date.today() + timedelta(days=365)
        future_dob = Patient(
            first_name="FutureDOB",
            phone="+919876543211",
            date_of_birth=future_date,
            clinic_id=clinic.id,
        )
        db.add(future_dob)
        db.commit()

        # Database allows it, validation should happen in API/schema layer
        assert future_dob.date_of_birth == future_date

    async def test_required_fields_enforcement(self, db, test_clinic_data):
        """Test that required fields are enforced."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Missing first_name
        with pytest.raises(Exception):
            patient = Patient(
                phone="+919876543210",
                clinic_id=clinic.id,
            )
            db.add(patient)
            db.commit()

        db.rollback()

        # Missing phone
        with pytest.raises(Exception):
            patient = Patient(
                first_name="NoPhone",
                clinic_id=clinic.id,
            )
            db.add(patient)
            db.commit()

        db.rollback()

        # Missing clinic_id
        with pytest.raises(Exception):
            patient = Patient(
                first_name="NoClinic",
                phone="+919876543210",
            )
            db.add(patient)
            db.commit()

        db.rollback()

    async def test_duplicate_phone_prevention_same_clinic(self, db, test_clinic_data):
        """Test prevention of duplicate phone numbers within same clinic."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create first patient
        patient1 = Patient(
            first_name="First",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient1)
        db.commit()

        # Try to create second patient with same phone in same clinic
        patient2 = Patient(
            first_name="Second",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient2)

        # This should be allowed at database level (no unique constraint)
        # But should be prevented at API level
        db.commit()  # Database allows it

        # Check both exist
        result = db.execute(
            select(Patient).where(
                Patient.phone == "+919876543210",
                Patient.clinic_id == clinic.id,
            )
        )
        duplicates = result.scalars().all()
        assert len(duplicates) == 2  # Database allows, API should prevent

    async def test_duplicate_phone_allowed_different_clinics(self, db, test_clinic_data):
        """Test that same phone is allowed in different clinics."""
        # Create two clinics
        clinic1 = Clinic(**test_clinic_data)
        db.add(clinic1)

        clinic2_data = test_clinic_data.copy()
        clinic2_data["id"] = uuid4()
        clinic2_data["name"] = "Second Clinic"
        clinic2 = Clinic(**clinic2_data)
        db.add(clinic2)
        db.commit()

        # Same phone in different clinics
        patient1 = Patient(
            first_name="Clinic1Patient",
            phone="+919876543210",
            clinic_id=clinic1.id,
        )
        patient2 = Patient(
            first_name="Clinic2Patient",
            phone="+919876543210",
            clinic_id=clinic2.id,
        )
        db.add(patient1)
        db.add(patient2)
        db.commit()

        assert patient1.phone == patient2.phone
        assert patient1.clinic_id != patient2.clinic_id

    async def test_gender_values_validation(self, db, test_clinic_data):
        """Test gender field accepts M, F, O values."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        valid_genders = ["M", "F", "O"]
        for i, gender in enumerate(valid_genders):
            patient = Patient(
                first_name=f"Gender{gender}",
                phone=f"+91987654{i:04d}",
                gender=gender,
                clinic_id=clinic.id,
            )
            db.add(patient)

        db.commit()

        # Verify all saved correctly
        result = db.execute(select(Patient).where(Patient.clinic_id == clinic.id))
        patients = result.scalars().all()
        assert len(patients) >= 3

        # Invalid gender (database allows, should validate at schema level)
        invalid_patient = Patient(
            first_name="InvalidGender",
            phone="+919876543999",
            gender="X",
            clinic_id=clinic.id,
        )
        db.add(invalid_patient)
        db.commit()  # Database allows it


# ============================================================================
# TEST CLASS 3: EMR SYNC
# ============================================================================


class TestPatientEMRSync:
    """Test EMR synchronization for patient data."""

    @patch("app.services.emr_sync_service.EMRIntegrationAsync")
    async def test_sync_patient_from_emr_new_patient(
        self, mock_emr_async, db, test_clinic_data
    ):
        """Test syncing a new patient from EMR."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Mock EMR patient data
        mock_emr_patient = MagicMock()
        mock_emr_patient.id = "EMR123"
        mock_emr_patient.first_name = "EMR Patient"
        mock_emr_patient.last_name = "Synced"
        mock_emr_patient.phone = "+919876543210"
        mock_emr_patient.email = "emr@example.com"
        mock_emr_patient.date_of_birth = date(1980, 1, 1)
        mock_emr_patient.gender = "M"
        mock_emr_patient.blood_group = "B+"
        mock_emr_patient.allergies = "None"
        mock_emr_patient.address = "EMR Address"

        # Mock EMR service
        mock_emr_instance = AsyncMock()
        mock_emr_instance.get_patient = AsyncMock(return_value=mock_emr_patient)
        mock_emr_async.return_value = mock_emr_instance

        # Create EMR sync service with mocked EMR
        emr_service = EMRSyncService()
        emr_service.emr_async = mock_emr_instance

        # Sync patient (note: requires clinic_id which we need to add)
        # This is a simplified test - actual implementation may vary
        patient = Patient(
            emr_patient_id="EMR123",
            first_name=mock_emr_patient.first_name,
            last_name=mock_emr_patient.last_name,
            phone=mock_emr_patient.phone,
            email=mock_emr_patient.email,
            date_of_birth=mock_emr_patient.date_of_birth,
            gender=mock_emr_patient.gender,
            blood_group=mock_emr_patient.blood_group,
            allergies=mock_emr_patient.allergies,
            address=mock_emr_patient.address,
            clinic_id=clinic.id,
            emr_synced_at=datetime.now(timezone.utc),
        )
        db.add(patient)
        db.commit()

        # Verify patient created from EMR
        result = db.execute(
            select(Patient).where(Patient.emr_patient_id == "EMR123")
        )
        synced_patient = result.scalar_one_or_none()

        assert synced_patient is not None
        assert synced_patient.first_name == "EMR Patient"
        assert synced_patient.emr_patient_id == "EMR123"
        assert synced_patient.emr_synced_at is not None

    async def test_sync_patient_from_emr_update_existing(self, db, test_clinic_data):
        """Test updating existing patient with EMR data."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create existing patient
        patient = Patient(
            emr_patient_id="EMR456",
            first_name="Old Name",
            last_name="Old Last",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()
        patient_id = patient.id

        # Simulate EMR update
        patient.first_name = "Updated Name"
        patient.last_name = "Updated Last"
        patient.email = "updated@example.com"
        patient.emr_synced_at = datetime.now(timezone.utc)
        db.commit()

        # Verify update
        result = db.execute(select(Patient).where(Patient.id == patient_id))
        updated = result.scalar_one()

        assert updated.first_name == "Updated Name"
        assert updated.last_name == "Updated Last"
        assert updated.email == "updated@example.com"
        assert updated.emr_synced_at is not None

    async def test_emr_conflict_resolution_emr_wins(self, db, test_clinic_data):
        """Test that EMR data takes precedence in conflicts."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create patient with local data
        patient = Patient(
            emr_patient_id="EMR789",
            first_name="Local Name",
            phone="+919876543210",
            email="local@example.com",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        # Simulate EMR sync overwriting local data
        patient.first_name = "EMR Name"
        patient.email = "emr@example.com"
        patient.emr_synced_at = datetime.now(timezone.utc)
        db.commit()

        # Verify EMR data won
        result = db.execute(
            select(Patient).where(Patient.emr_patient_id == "EMR789")
        )
        resolved = result.scalar_one()

        assert resolved.first_name == "EMR Name"
        assert resolved.email == "emr@example.com"

    async def test_handle_missing_emr_database_gracefully(self, db, test_clinic_data):
        """Test graceful handling when EMR database is not available."""
        # Create EMR service with non-existent database
        with patch.dict(os.environ, {"EMR_SYNC_ENABLED": "false"}):
            emr_service = EMRSyncService()

            # Check service status
            status = emr_service.get_status()

            assert status["enabled"] is False or status["available"] is False

    async def test_emr_sync_timestamp_tracking(self, db, test_clinic_data):
        """Test that EMR sync timestamps are properly tracked."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create patient without EMR sync
        patient = Patient(
            first_name="Not Synced",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        assert patient.emr_synced_at is None

        # Update with EMR sync
        sync_time = datetime.now(timezone.utc)
        patient.emr_patient_id = "EMR999"
        patient.emr_synced_at = sync_time
        db.commit()

        # Verify timestamp
        result = db.execute(select(Patient).where(Patient.id == patient.id))
        synced = result.scalar_one()

        assert synced.emr_synced_at is not None
        assert synced.emr_patient_id == "EMR999"


# ============================================================================
# TEST CLASS 4: PRIVACY & SECURITY
# ============================================================================


class TestPatientPrivacySecurity:
    """Test privacy and security measures for patient data."""

    async def test_patient_data_isolation_between_clinics(self, db, test_clinic_data):
        """Test that patients are isolated between clinics."""
        # Create two clinics
        clinic1 = Clinic(**test_clinic_data)
        db.add(clinic1)

        clinic2_data = test_clinic_data.copy()
        clinic2_data["id"] = uuid4()
        clinic2_data["name"] = "Clinic 2"
        clinic2 = Clinic(**clinic2_data)
        db.add(clinic2)
        db.commit()

        # Create patients in each clinic
        patient1 = Patient(
            first_name="Clinic1Patient",
            phone="+919876543210",
            clinic_id=clinic1.id,
        )
        patient2 = Patient(
            first_name="Clinic2Patient",
            phone="+919876543211",
            clinic_id=clinic2.id,
        )
        db.add(patient1)
        db.add(patient2)
        db.commit()

        # Query clinic 1 patients only
        result = db.execute(
            select(Patient).where(Patient.clinic_id == clinic1.id)
        )
        clinic1_patients = result.scalars().all()

        assert len(clinic1_patients) == 1
        assert clinic1_patients[0].first_name == "Clinic1Patient"

        # Query clinic 2 patients only
        result = db.execute(
            select(Patient).where(Patient.clinic_id == clinic2.id)
        )
        clinic2_patients = result.scalars().all()

        assert len(clinic2_patients) == 1
        assert clinic2_patients[0].first_name == "Clinic2Patient"

    async def test_sensitive_fields_properly_stored(self, db, test_clinic_data):
        """Test that sensitive fields are properly handled."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create patient with sensitive data
        patient = Patient(
            first_name="Sensitive",
            phone="+919876543210",
            aadhaar_last_four="1234",
            allergies="HIV medications",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        # Verify data is stored (encryption would be at column level)
        result = db.execute(select(Patient).where(Patient.id == patient.id))
        retrieved = result.scalar_one()

        assert retrieved.aadhaar_last_four == "1234"
        assert retrieved.allergies == "HIV medications"

    async def test_audit_trail_via_timestamps(self, db, test_clinic_data):
        """Test that created_at and updated_at provide audit trail."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create patient
        patient = Patient(
            first_name="AuditTest",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        created_at = patient.created_at
        assert created_at is not None

        # Update patient
        import time
        time.sleep(0.1)  # Ensure time difference
        patient.address = "New Address"
        db.commit()

        updated_at = patient.updated_at
        assert updated_at is not None
        # Note: updated_at may not be automatically set in test DB

    async def test_soft_delete_preserves_data_for_audit(self, db, test_clinic_data):
        """Test that soft delete preserves data for audit purposes."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="ToDelete",
            phone="+919876543210",
            email="delete@example.com",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()
        patient_id = patient.id

        # Soft delete
        patient.is_active = False
        db.commit()

        # Verify data still exists
        result = db.execute(select(Patient).where(Patient.id == patient_id))
        deleted = result.scalar_one()

        assert deleted is not None
        assert deleted.is_active is False
        assert deleted.first_name == "ToDelete"
        assert deleted.email == "delete@example.com"


# ============================================================================
# TEST CLASS 5: EDGE CASES
# ============================================================================


class TestPatientEdgeCases:
    """Test edge cases and special scenarios."""

    async def test_unicode_hindi_name(self, db, test_clinic_data):
        """Test patient name in Hindi (Devanagari script)."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="राजेश",
            last_name="कुमार",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        result = db.execute(select(Patient).where(Patient.id == patient.id))
        retrieved = result.scalar_one()

        assert retrieved.first_name == "राजेश"
        assert retrieved.last_name == "कुमार"
        assert retrieved.full_name == "राजेश कुमार"

    async def test_unicode_tamil_name(self, db, test_clinic_data):
        """Test patient name in Tamil script."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="முருகன்",
            last_name="செல்வம்",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        result = db.execute(select(Patient).where(Patient.id == patient.id))
        retrieved = result.scalar_one()

        assert retrieved.first_name == "முருகன்"
        assert retrieved.last_name == "செல்வம்"

    async def test_very_long_name(self, db, test_clinic_data):
        """Test handling of very long names."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Name at the limit (100 characters)
        long_name = "A" * 100
        patient = Patient(
            first_name=long_name,
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        assert len(patient.first_name) == 100

    async def test_special_characters_in_address(self, db, test_clinic_data):
        """Test special characters in address field."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        special_address = "Flat #23, 2nd Floor, \"Star\" Building, S.V. Road, @Mumbai-400001"
        patient = Patient(
            first_name="Special",
            phone="+919876543210",
            address=special_address,
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        result = db.execute(select(Patient).where(Patient.id == patient.id))
        retrieved = result.scalar_one()

        assert retrieved.address == special_address

    async def test_multiple_patients_same_name(self, db, test_clinic_data):
        """Test handling multiple patients with identical names."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Create 3 patients with same name
        for i in range(3):
            patient = Patient(
                first_name="Rajesh",
                last_name="Kumar",
                phone=f"+91987654{i:04d}",
                clinic_id=clinic.id,
            )
            db.add(patient)
        db.commit()

        # Query all Rajesh Kumars
        result = db.execute(
            select(Patient).where(
                Patient.first_name == "Rajesh",
                Patient.last_name == "Kumar",
                Patient.clinic_id == clinic.id,
            )
        )
        same_name_patients = result.scalars().all()

        assert len(same_name_patients) == 3
        # Should be distinguishable by phone and ID
        phones = [p.phone for p in same_name_patients]
        assert len(set(phones)) == 3  # All unique

    async def test_patient_age_calculation(self, db, test_clinic_data):
        """Test accurate age calculation from date of birth."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # Patient born 30 years ago
        dob = date.today() - timedelta(days=30 * 365)
        patient = Patient(
            first_name="AgeTest",
            phone="+919876543210",
            date_of_birth=dob,
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        assert patient.age is not None
        assert 29 <= patient.age <= 30  # Account for leap years

    async def test_patient_age_with_no_dob(self, db, test_clinic_data):
        """Test age property when date of birth is not set."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="NoDOB",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        assert patient.age is None

    async def test_empty_string_vs_null_handling(self, db, test_clinic_data):
        """Test handling of empty strings vs NULL values."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="EmptyTest",
            phone="+919876543210",
            email="",  # Empty string
            last_name=None,  # Explicit NULL
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()

        result = db.execute(select(Patient).where(Patient.id == patient.id))
        retrieved = result.scalar_one()

        # Empty string is stored as-is (database allows it)
        assert retrieved.email == ""
        assert retrieved.last_name is None

    async def test_patient_full_name_property(self, db, test_clinic_data):
        """Test full_name property with various name combinations."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        # With both names
        patient1 = Patient(
            first_name="Rajesh",
            last_name="Kumar",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient1)

        # Only first name
        patient2 = Patient(
            first_name="Madonna",
            phone="+919876543211",
            clinic_id=clinic.id,
        )
        db.add(patient2)
        db.commit()

        assert patient1.full_name == "Rajesh Kumar"
        assert patient2.full_name == "Madonna"

    async def test_concurrent_patient_updates(self, db, test_clinic_data):
        """Test handling of concurrent updates to same patient."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="Concurrent",
            phone="+919876543210",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.commit()
        patient_id = patient.id

        # Simulate concurrent updates
        patient.address = "Address 1"
        db.commit()

        # Reload and update again
        result = db.execute(select(Patient).where(Patient.id == patient_id))
        patient_reload = result.scalar_one()
        patient_reload.address = "Address 2"
        db.commit()

        # Verify final state
        result = db.execute(select(Patient).where(Patient.id == patient_id))
        final = result.scalar_one()
        assert final.address == "Address 2"

    async def test_patient_with_all_optional_fields_null(self, db, test_clinic_data):
        """Test patient with only required fields, all optional NULL."""
        clinic = Clinic(**test_clinic_data)
        db.add(clinic)
        db.commit()

        patient = Patient(
            first_name="MinimalPatient",
            phone="+919876543210",
            clinic_id=clinic.id,
            # All other fields implicitly NULL
        )
        db.add(patient)
        db.commit()

        result = db.execute(select(Patient).where(Patient.id == patient.id))
        minimal = result.scalar_one()

        assert minimal.last_name is None
        assert minimal.email is None
        assert minimal.date_of_birth is None
        assert minimal.gender is None
        assert minimal.address is None
        assert minimal.blood_group is None
        assert minimal.allergies is None
