"""
Comprehensive tests for AI Services (Entity Extraction and Action Execution).

Phase 16b: Conversational Actions

Tests cover:
- AI Entity Extractor (dates, times, patients, doctors, urgency, reasons)
- AI Action Executor (booking, rescheduling, canceling, etc.)
- LLM Integration (mocking Ollama)
- Error handling and edge cases
"""

import json
import pytest
from datetime import date, time, datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import MagicMock, AsyncMock, patch

import httpx

from app.services.ai_entity_extractor import EntityExtractor
from app.services.ai_action_executor import (
    AIActionExecutor,
    ActionType,
    ActionResult,
    PendingAction,
    UndoRecord,
)
from app.services.ai_assistant import (
    PracticeAIAssistant,
    FunctionName,
    AIResponse,
    ConversationSession,
)
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment, AppointmentStatus, BookingSource
from app.models.waitlist import Waitlist, WaitlistPriority, WaitlistStatus


# =============================================================================
# AI ENTITY EXTRACTOR TESTS
# =============================================================================


class TestEntityExtractorDateExtraction:
    """Tests for date extraction from natural language."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def extractor(self, mock_db):
        """Create entity extractor instance."""
        return EntityExtractor(mock_db)

    def test_extract_date_today(self, extractor):
        """Test extraction of 'today'."""
        result = extractor.extract_date("Book for today")
        assert result == date.today()

    def test_extract_date_tomorrow(self, extractor):
        """Test extraction of 'tomorrow'."""
        result = extractor.extract_date("Schedule appointment tomorrow")
        assert result == date.today() + timedelta(days=1)

    def test_extract_date_day_after_tomorrow(self, extractor):
        """Test extraction of 'day after tomorrow'."""
        result = extractor.extract_date("day after tomorrow please")
        assert result == date.today() + timedelta(days=2)

    def test_extract_date_yesterday(self, extractor):
        """Test extraction of 'yesterday'."""
        result = extractor.extract_date("Check yesterday's appointments")
        assert result == date.today() - timedelta(days=1)

    def test_extract_date_hindi_aaj(self, extractor):
        """Test extraction of 'aaj' (today in Hindi)."""
        result = extractor.extract_date("aaj ka appointment")
        assert result == date.today()

    def test_extract_date_hindi_kal(self, extractor):
        """Test extraction of 'kal' (tomorrow in Hindi)."""
        result = extractor.extract_date("kal appointment book karo")
        assert result == date.today() + timedelta(days=1)

    def test_extract_date_hindi_parso(self, extractor):
        """Test extraction of 'parso' (day after tomorrow in Hindi)."""
        result = extractor.extract_date("parso ka slot available hai?")
        assert result == date.today() + timedelta(days=2)

    def test_extract_date_next_week(self, extractor):
        """Test extraction of 'next week'."""
        result = extractor.extract_date("Schedule for next week")
        today = date.today()
        days_to_monday = 7 - today.weekday()
        expected = today + timedelta(days=days_to_monday)
        assert result == expected

    def test_extract_date_this_week(self, extractor):
        """Test extraction of 'this week'."""
        result = extractor.extract_date("Book this week")
        assert result is not None
        today = date.today()
        # Should return a date this week
        assert result >= today

    def test_extract_date_next_month(self, extractor):
        """Test extraction of 'next month'."""
        result = extractor.extract_date("Next month appointment")
        today = date.today()
        if today.month == 12:
            expected = date(today.year + 1, 1, 1)
        else:
            expected = date(today.year, today.month + 1, 1)
        assert result == expected

    def test_extract_date_monday(self, extractor):
        """Test extraction of 'Monday'."""
        result = extractor.extract_date("Book for Monday")
        assert result is not None
        assert result.weekday() == 0  # Monday is 0

    def test_extract_date_tuesday(self, extractor):
        """Test extraction of 'Tuesday'."""
        result = extractor.extract_date("Tuesday appointment")
        assert result is not None
        assert result.weekday() == 1  # Tuesday is 1

    def test_extract_date_friday(self, extractor):
        """Test extraction of 'Friday'."""
        result = extractor.extract_date("See you Friday")
        assert result is not None
        assert result.weekday() == 4  # Friday is 4

    def test_extract_date_specific_ddmmyyyy(self, extractor):
        """Test extraction of 'DD/MM/YYYY' format."""
        result = extractor.extract_date("Book for 15/01/2026")
        assert result == date(2026, 1, 15)

    def test_extract_date_specific_iso(self, extractor):
        """Test extraction of 'YYYY-MM-DD' format."""
        result = extractor.extract_date("2026-02-20 appointment")
        assert result == date(2026, 2, 20)

    def test_extract_date_month_name_15th_january(self, extractor):
        """Test extraction of '15th January' format."""
        result = extractor.extract_date("Book for 15th January")
        assert result is not None
        assert result.month == 1
        assert result.day == 15

    def test_extract_date_month_name_january_15(self, extractor):
        """Test extraction of 'January 15th' format."""
        result = extractor.extract_date("January 15th appointment")
        assert result is not None
        assert result.month == 1
        assert result.day == 15

    def test_extract_date_no_date_found(self, extractor):
        """Test when no date is present."""
        result = extractor.extract_date("Book an appointment")
        assert result is None

    def test_extract_date_ambiguous(self, extractor):
        """Test with ambiguous input."""
        result = extractor.extract_date("Some random text")
        assert result is None

    def test_extract_date_with_reference_date(self, extractor):
        """Test with custom reference date."""
        reference = date(2026, 1, 15)
        result = extractor.extract_date("tomorrow", reference_date=reference)
        assert result == date(2026, 1, 16)

    def test_extract_date_past_month_assumes_next_year(self, extractor):
        """Test that past month dates assume next year."""
        # If we're in January and user says "December 25th", it should be next year
        result = extractor.extract_date("December 25th", reference_date=date(2026, 1, 10))
        assert result == date(2026, 12, 25)


class TestEntityExtractorTimeExtraction:
    """Tests for time extraction from natural language."""

    @pytest.fixture
    def extractor(self):
        """Create entity extractor instance."""
        return EntityExtractor(MagicMock())

    def test_extract_time_3pm(self, extractor):
        """Test extraction of '3pm' format."""
        result = extractor.extract_time("at 3pm")
        assert result == time(15, 0)

    def test_extract_time_3_30pm(self, extractor):
        """Test extraction of '3:30pm' format."""
        result = extractor.extract_time("at 3:30pm")
        assert result == time(15, 30)

    def test_extract_time_9am(self, extractor):
        """Test extraction of '9am' format."""
        result = extractor.extract_time("at 9am")
        assert result == time(9, 0)

    def test_extract_time_12pm(self, extractor):
        """Test extraction of '12pm' (noon)."""
        result = extractor.extract_time("at 12pm")
        assert result == time(12, 0)

    def test_extract_time_12am(self, extractor):
        """Test extraction of '12am' (midnight)."""
        result = extractor.extract_time("at 12am")
        assert result == time(0, 0)

    def test_extract_time_24hour_1530(self, extractor):
        """Test extraction of '15:30' format."""
        result = extractor.extract_time("at 15:30")
        assert result == time(15, 30)

    def test_extract_time_24hour_0900(self, extractor):
        """Test extraction of '09:00' format."""
        result = extractor.extract_time("at 09:00")
        assert result == time(9, 0)

    def test_extract_time_morning(self, extractor):
        """Test extraction of 'morning'."""
        result = extractor.extract_time("in the morning")
        assert result == time(9, 0)

    def test_extract_time_afternoon(self, extractor):
        """Test extraction of 'afternoon'."""
        result = extractor.extract_time("in the afternoon")
        assert result == time(14, 0)

    def test_extract_time_evening(self, extractor):
        """Test extraction of 'evening'."""
        result = extractor.extract_time("in the evening")
        assert result == time(18, 0)

    def test_extract_time_night(self, extractor):
        """Test extraction of 'night'."""
        result = extractor.extract_time("at night")
        assert result == time(20, 0)

    def test_extract_time_lunch(self, extractor):
        """Test extraction of 'lunch'."""
        result = extractor.extract_time("during lunch")
        assert result == time(14, 0)

    def test_extract_time_no_time_found(self, extractor):
        """Test when no time is present."""
        result = extractor.extract_time("Book an appointment")
        assert result is None

    def test_extract_time_invalid_hour(self, extractor):
        """Test with invalid hour (should return None)."""
        result = extractor.extract_time("at 25:00")
        assert result is None


class TestEntityExtractorPatientExtraction:
    """Tests for patient extraction from natural language."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def extractor(self, mock_db):
        """Create entity extractor instance."""
        return EntityExtractor(mock_db)

    @pytest.mark.asyncio
    async def test_extract_patient_by_phone(self, extractor, mock_db):
        """Test patient extraction by phone number."""
        patient = MagicMock(spec=Patient)
        patient.id = uuid4()
        patient.full_name = "Rajesh Kumar"
        patient.phone = "9876543210"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = patient
        mock_db.query.return_value = mock_query

        clinic_id = uuid4()
        result = await extractor.extract_patient("Book 9876543210 for tomorrow", clinic_id)
        assert result == patient

    @pytest.mark.asyncio
    async def test_extract_patient_by_name(self, extractor, mock_db):
        """Test patient extraction by name."""
        patient = MagicMock(spec=Patient)
        patient.id = uuid4()
        patient.full_name = "Priya Sharma"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = patient
        mock_db.query.return_value = mock_query

        clinic_id = uuid4()
        result = await extractor.extract_patient("Book Priya Sharma", clinic_id)
        assert result == patient

    @pytest.mark.asyncio
    async def test_extract_patient_from_context(self, extractor, mock_db):
        """Test patient extraction from conversation context."""
        patient = MagicMock(spec=Patient)
        patient_id = uuid4()
        patient.id = patient_id
        patient.clinic_id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = patient
        mock_db.query.return_value = mock_query

        result = await extractor.extract_patient(
            "Book tomorrow", patient.clinic_id, context_patient_id=patient_id
        )
        assert result == patient

    @pytest.mark.asyncio
    async def test_extract_patient_not_found(self, extractor, mock_db):
        """Test when patient is not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        result = await extractor.extract_patient("Book someone unknown", uuid4())
        assert result is None


class TestEntityExtractorDoctorExtraction:
    """Tests for doctor extraction from natural language."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def extractor(self, mock_db):
        """Create entity extractor instance."""
        return EntityExtractor(mock_db)

    @pytest.mark.asyncio
    async def test_extract_doctor_by_name_with_dr(self, extractor, mock_db):
        """Test doctor extraction with 'Dr.' prefix."""
        doctor = MagicMock(spec=Doctor)
        doctor.id = uuid4()
        doctor.full_name = "Sharma"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = doctor
        mock_db.query.return_value = mock_query

        clinic_id = uuid4()
        result = await extractor.extract_doctor("Book with Dr. Sharma", clinic_id)
        assert result == doctor

    @pytest.mark.asyncio
    async def test_extract_doctor_by_name_without_dr(self, extractor, mock_db):
        """Test doctor extraction without 'Dr.' prefix."""
        doctor = MagicMock(spec=Doctor)
        doctor.id = uuid4()
        doctor.full_name = "Verma"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = doctor
        mock_db.query.return_value = mock_query

        clinic_id = uuid4()
        result = await extractor.extract_doctor("Book with Verma", clinic_id)
        assert result == doctor

    @pytest.mark.asyncio
    async def test_extract_doctor_from_context(self, extractor, mock_db):
        """Test doctor extraction from conversation context."""
        doctor = MagicMock(spec=Doctor)
        doctor_id = uuid4()
        doctor.id = doctor_id
        doctor.clinic_id = uuid4()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = doctor
        mock_db.query.return_value = mock_query

        result = await extractor.extract_doctor(
            "Book tomorrow", doctor.clinic_id, context_doctor_id=doctor_id
        )
        assert result == doctor

    @pytest.mark.asyncio
    async def test_extract_doctor_default_first_active(self, extractor, mock_db):
        """Test default doctor extraction (first active)."""
        doctor = MagicMock(spec=Doctor)
        doctor.id = uuid4()
        doctor.is_active = True

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = doctor
        mock_db.query.return_value = mock_query

        clinic_id = uuid4()
        result = await extractor.extract_doctor("Book appointment", clinic_id)
        assert result == doctor


class TestEntityExtractorOthers:
    """Tests for urgency and reason extraction."""

    @pytest.fixture
    def extractor(self):
        """Create entity extractor instance."""
        return EntityExtractor(MagicMock())

    def test_extract_urgency_high_urgent(self, extractor):
        """Test extraction of high urgency with 'urgent'."""
        assert extractor.extract_urgency("This is urgent") == "high"

    def test_extract_urgency_high_emergency(self, extractor):
        """Test extraction of high urgency with 'emergency'."""
        assert extractor.extract_urgency("Emergency case") == "high"

    def test_extract_urgency_high_asap(self, extractor):
        """Test extraction of high urgency with 'ASAP'."""
        assert extractor.extract_urgency("Need ASAP") == "high"

    def test_extract_urgency_high_immediately(self, extractor):
        """Test extraction of high urgency with 'immediately'."""
        assert extractor.extract_urgency("See immediately") == "high"

    def test_extract_urgency_medium_soon(self, extractor):
        """Test extraction of medium urgency with 'soon'."""
        assert extractor.extract_urgency("Soon please") == "medium"

    def test_extract_urgency_medium_priority(self, extractor):
        """Test extraction of medium urgency with 'priority'."""
        assert extractor.extract_urgency("Priority case") == "medium"

    def test_extract_urgency_low_default(self, extractor):
        """Test extraction of low urgency (default)."""
        assert extractor.extract_urgency("Regular appointment") == "low"

    def test_extract_reason_for(self, extractor):
        """Test extraction of reason with 'for'."""
        result = extractor.extract_reason("Book for headache")
        assert result == "headache"

    def test_extract_reason_because_of(self, extractor):
        """Test extraction of reason with 'because of'."""
        result = extractor.extract_reason("Appointment because of chest pain")
        assert result == "chest pain"

    def test_extract_reason_complaint(self, extractor):
        """Test extraction of reason with 'complaint:'."""
        result = extractor.extract_reason("complaint: fever and cough")
        assert result == "fever and cough"

    def test_extract_reason_none(self, extractor):
        """Test when no reason is present."""
        result = extractor.extract_reason("Book tomorrow at 3pm")
        assert result is None


class TestEntityExtractorIntegration:
    """Integration tests for combined entity extraction."""

    @pytest.fixture
    def extractor(self):
        """Create entity extractor instance."""
        return EntityExtractor(MagicMock())

    def test_extract_date_and_time_together(self, extractor):
        """Test extracting both date and time from single message."""
        message = "Book for tomorrow at 3pm"
        extracted_date = extractor.extract_date(message)
        extracted_time = extractor.extract_time(message)

        assert extracted_date == date.today() + timedelta(days=1)
        assert extracted_time == time(15, 0)

    def test_extract_complex_message(self, extractor):
        """Test extracting multiple entities from complex message."""
        message = "Urgent appointment for chest pain tomorrow afternoon"

        extracted_date = extractor.extract_date(message)
        extracted_time = extractor.extract_time(message)
        urgency = extractor.extract_urgency(message)
        reason = extractor.extract_reason(message)

        assert extracted_date == date.today() + timedelta(days=1)
        assert extracted_time == time(14, 0)  # afternoon
        assert urgency == "high"  # urgent
        assert reason == "chest pain"

    def test_extract_hindi_english_mixed(self, extractor):
        """Test extracting from Hindi-English mixed message."""
        message = "kal 3pm appointment book karo for fever"

        extracted_date = extractor.extract_date(message)
        extracted_time = extractor.extract_time(message)
        reason = extractor.extract_reason(message)

        assert extracted_date == date.today() + timedelta(days=1)  # kal = tomorrow
        assert extracted_time == time(15, 0)
        assert reason == "fever"


# =============================================================================
# AI ACTION EXECUTOR TESTS
# =============================================================================


class TestActionExecutorBookAppointment:
    """Tests for booking appointments via AI."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.get = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def executor(self, mock_db):
        """Create action executor instance."""
        return AIActionExecutor(mock_db)

    @pytest.mark.asyncio
    async def test_book_appointment_missing_patient_id(self, executor):
        """Test booking fails with missing patient_id."""
        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={"date": date.today(), "time": time(15, 0)},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing required parameters" in result.message
        assert "patient_id" in result.message

    @pytest.mark.asyncio
    async def test_book_appointment_missing_date(self, executor):
        """Test booking fails with missing date."""
        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={"patient_id": uuid4(), "time": time(15, 0)},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing required parameters" in result.message

    @pytest.mark.asyncio
    async def test_book_appointment_missing_time(self, executor):
        """Test booking fails with missing time."""
        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={"patient_id": uuid4(), "date": date.today()},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing required parameters" in result.message

    @pytest.mark.asyncio
    async def test_book_appointment_patient_not_found(self, executor, mock_db):
        """Test booking fails when patient not found."""
        mock_db.get.return_value = None

        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={
                "patient_id": uuid4(),
                "date": date.today() + timedelta(days=1),
                "time": time(15, 0),
            },
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Patient not found" in result.message

    @pytest.mark.asyncio
    async def test_book_appointment_past_datetime(self, executor, mock_db):
        """Test booking fails for past datetime."""
        patient = MagicMock(spec=Patient)
        patient.id = uuid4()
        patient.clinic_id = uuid4()
        patient.full_name = "Test Patient"

        doctor = MagicMock(spec=Doctor)
        doctor.id = uuid4()
        doctor.clinic_id = patient.clinic_id
        doctor.full_name = "Test Doctor"

        mock_db.get.side_effect = lambda model, id: patient if id == patient.id else doctor

        # Use yesterday's date
        past_date = date.today() - timedelta(days=1)
        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={
                "patient_id": str(patient.id),
                "doctor_id": str(doctor.id),
                "date": past_date,
                "time": time(15, 0),
            },
            user_id=uuid4(),
            clinic_id=patient.clinic_id,
        )
        assert not result.success
        assert "Cannot book appointment in the past" in result.message

    @pytest.mark.asyncio
    async def test_book_appointment_slot_conflict(self, executor, mock_db):
        """Test booking fails when slot is already occupied."""
        clinic_id = uuid4()

        patient = MagicMock(spec=Patient)
        patient.id = uuid4()
        patient.clinic_id = clinic_id
        patient.full_name = "Test Patient"

        doctor = MagicMock(spec=Doctor)
        doctor.id = uuid4()
        doctor.clinic_id = clinic_id
        doctor.full_name = "Test Doctor"

        # Mock conflict appointment
        conflict_appt = MagicMock(spec=Appointment)
        conflict_appt.id = uuid4()
        conflict_appt.scheduled_start = datetime.now() + timedelta(days=1, hours=15)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conflict_appt
        mock_db.execute.return_value = mock_result

        mock_db.get.side_effect = lambda model, id: patient if id == patient.id else doctor

        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={
                "patient_id": str(patient.id),
                "doctor_id": str(doctor.id),
                "date": date.today() + timedelta(days=1),
                "time": time(15, 0),
            },
            user_id=uuid4(),
            clinic_id=clinic_id,
        )
        assert not result.success
        assert "not available" in result.message
        assert result.error == "Slot conflict"

    @pytest.mark.asyncio
    async def test_book_appointment_success(self, executor, mock_db):
        """Test successful appointment booking."""
        clinic_id = uuid4()

        patient = MagicMock(spec=Patient)
        patient.id = uuid4()
        patient.clinic_id = clinic_id
        patient.full_name = "Rajesh Kumar"

        doctor = MagicMock(spec=Doctor)
        doctor.id = uuid4()
        doctor.clinic_id = clinic_id
        doctor.full_name = "Sharma"

        # No conflicts
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_db.get.side_effect = lambda model, id: patient if id == patient.id else doctor

        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={
                "patient_id": str(patient.id),
                "doctor_id": str(doctor.id),
                "date": date.today() + timedelta(days=1),
                "time": time(15, 0),
                "reason": "Follow-up",
            },
            user_id=uuid4(),
            clinic_id=clinic_id,
        )
        assert result.success
        assert "Appointment booked" in result.message
        assert "Rajesh Kumar" in result.message
        assert "Dr. Sharma" in result.message
        assert result.data is not None


class TestActionExecutorReschedule:
    """Tests for rescheduling appointments."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.get = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def executor(self, mock_db):
        """Create action executor instance."""
        return AIActionExecutor(mock_db)

    @pytest.mark.asyncio
    async def test_reschedule_missing_appointment_id(self, executor):
        """Test reschedule fails without appointment ID."""
        result = await executor.execute_action(
            action_type=ActionType.RESCHEDULE_APPOINTMENT,
            params={"new_date": date.today(), "new_time": time(16, 0)},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing required parameters" in result.message

    @pytest.mark.asyncio
    async def test_reschedule_appointment_not_found(self, executor, mock_db):
        """Test reschedule fails when appointment not found."""
        mock_db.get.return_value = None

        result = await executor.execute_action(
            action_type=ActionType.RESCHEDULE_APPOINTMENT,
            params={
                "appointment_id": uuid4(),
                "new_date": date.today() + timedelta(days=1),
                "new_time": time(16, 0),
            },
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Appointment not found" in result.message

    @pytest.mark.asyncio
    async def test_reschedule_slot_conflict(self, executor, mock_db):
        """Test reschedule fails when new slot conflicts."""
        clinic_id = uuid4()

        appointment = MagicMock(spec=Appointment)
        appointment.id = uuid4()
        appointment.doctor_id = uuid4()
        appointment.patient_id = uuid4()
        appointment.scheduled_start = datetime.now() + timedelta(days=1, hours=15)
        appointment.scheduled_end = datetime.now() + timedelta(days=1, hours=15, minutes=15)
        appointment.duration_minutes = 15

        doctor = MagicMock(spec=Doctor)
        doctor.id = appointment.doctor_id
        doctor.clinic_id = clinic_id

        # Mock conflict
        conflict_appt = MagicMock(spec=Appointment)
        conflict_appt.id = uuid4()
        conflict_appt.scheduled_start = datetime.now() + timedelta(days=2, hours=16)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = conflict_appt
        mock_db.execute.return_value = mock_result

        mock_db.get.side_effect = lambda model, id: (
            appointment if id == appointment.id else doctor
        )

        result = await executor.execute_action(
            action_type=ActionType.RESCHEDULE_APPOINTMENT,
            params={
                "appointment_id": str(appointment.id),
                "new_date": date.today() + timedelta(days=2),
                "new_time": time(16, 0),
            },
            user_id=uuid4(),
            clinic_id=clinic_id,
        )
        assert not result.success
        assert "not available" in result.message


class TestActionExecutorCancel:
    """Tests for canceling appointments."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.get = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def executor(self, mock_db):
        """Create action executor instance."""
        return AIActionExecutor(mock_db)

    @pytest.mark.asyncio
    async def test_cancel_missing_appointment_id(self, executor):
        """Test cancel fails without appointment ID."""
        result = await executor.execute_action(
            action_type=ActionType.CANCEL_APPOINTMENT,
            params={},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing appointment_id" in result.message

    @pytest.mark.asyncio
    async def test_cancel_appointment_not_found(self, executor, mock_db):
        """Test cancel fails when appointment not found."""
        mock_db.get.return_value = None

        result = await executor.execute_action(
            action_type=ActionType.CANCEL_APPOINTMENT,
            params={"appointment_id": uuid4()},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Appointment not found" in result.message

    @pytest.mark.asyncio
    async def test_cancel_appointment_success(self, executor, mock_db):
        """Test successful appointment cancellation."""
        clinic_id = uuid4()

        appointment = MagicMock(spec=Appointment)
        appointment.id = uuid4()
        appointment.doctor_id = uuid4()
        appointment.patient_id = uuid4()
        appointment.status = AppointmentStatus.SCHEDULED.value
        appointment.scheduled_start = datetime.now() + timedelta(days=1, hours=15)

        doctor = MagicMock(spec=Doctor)
        doctor.id = appointment.doctor_id
        doctor.clinic_id = clinic_id

        patient = MagicMock(spec=Patient)
        patient.id = appointment.patient_id
        patient.full_name = "Test Patient"

        mock_db.get.side_effect = lambda model, id: {
            appointment.id: appointment,
            doctor.id: doctor,
            patient.id: patient,
        }.get(id)

        result = await executor.execute_action(
            action_type=ActionType.CANCEL_APPOINTMENT,
            params={"appointment_id": str(appointment.id), "reason": "Patient unavailable"},
            user_id=uuid4(),
            clinic_id=clinic_id,
        )
        assert result.success
        assert "Appointment cancelled" in result.message
        assert appointment.status == AppointmentStatus.CANCELLED.value


class TestActionExecutorOthers:
    """Tests for other action executor methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.get = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def executor(self, mock_db):
        """Create action executor instance."""
        return AIActionExecutor(mock_db)

    @pytest.mark.asyncio
    async def test_add_to_waitlist_missing_patient_id(self, executor):
        """Test waitlist fails without patient ID."""
        result = await executor.execute_action(
            action_type=ActionType.ADD_TO_WAITLIST,
            params={},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing patient_id" in result.message

    @pytest.mark.asyncio
    async def test_add_to_waitlist_success(self, executor, mock_db):
        """Test successful waitlist addition."""
        clinic_id = uuid4()

        patient = MagicMock(spec=Patient)
        patient.id = uuid4()
        patient.clinic_id = clinic_id
        patient.full_name = "Test Patient"

        mock_db.get.return_value = patient

        result = await executor.execute_action(
            action_type=ActionType.ADD_TO_WAITLIST,
            params={"patient_id": str(patient.id), "urgency": "high"},
            user_id=uuid4(),
            clinic_id=clinic_id,
        )
        assert result.success
        assert "Added" in result.message
        assert "waitlist" in result.message

    @pytest.mark.asyncio
    async def test_lookup_patient_empty_query(self, executor):
        """Test patient lookup fails with empty query."""
        result = await executor.execute_action(
            action_type=ActionType.LOOKUP_PATIENT,
            params={"query": ""},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing query parameter" in result.message

    @pytest.mark.asyncio
    async def test_check_availability_missing_date(self, executor):
        """Test availability check fails without date."""
        result = await executor.execute_action(
            action_type=ActionType.CHECK_AVAILABILITY,
            params={},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success
        assert "Missing date parameter" in result.message

    @pytest.mark.asyncio
    async def test_check_availability_success(self, executor, mock_db):
        """Test successful availability check."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await executor.execute_action(
            action_type=ActionType.CHECK_AVAILABILITY,
            params={"date": date.today() + timedelta(days=1)},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert result.success
        assert "available" in result.message

    @pytest.mark.asyncio
    async def test_invalid_action_type(self, executor):
        """Test handling of invalid action type."""
        # This would require creating a fake ActionType which isn't possible
        # So we test by direct method call
        result = await executor.execute_action(
            action_type="invalid_action",  # type: ignore
            params={},
            user_id=uuid4(),
            clinic_id=uuid4(),
        )
        assert not result.success


class TestActionExecutorUndo:
    """Tests for undo functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.get = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def executor(self, mock_db):
        """Create action executor instance."""
        return AIActionExecutor(mock_db)

    @pytest.mark.asyncio
    async def test_undo_no_history(self, executor):
        """Test undo fails when no history."""
        result = await executor.undo_last_action("session123")
        assert not result.success
        assert "No actions to undo" in result.message

    @pytest.mark.asyncio
    async def test_undo_book_appointment(self, executor, mock_db):
        """Test undoing a booked appointment."""
        # First record an action
        appt_id = uuid4()
        executor._record_undo(
            action_type=ActionType.BOOK_APPOINTMENT,
            data={"appointment_id": str(appt_id), "can_cancel": True},
        )

        appointment = MagicMock(spec=Appointment)
        appointment.id = appt_id
        appointment.status = AppointmentStatus.SCHEDULED.value

        mock_db.get.return_value = appointment

        result = await executor.undo_last_action("session123")
        assert result.success
        assert "undone" in result.message
        assert appointment.status == AppointmentStatus.CANCELLED.value


# =============================================================================
# LLM INTEGRATION TESTS (AI ASSISTANT)
# =============================================================================


class TestAIAssistantLLMIntegration:
    """Tests for AI Assistant with mocked LLM responses."""

    @pytest.fixture
    def assistant(self):
        """Create AI assistant instance."""
        return PracticeAIAssistant(
            model="qwen2.5:latest",
            base_url="http://localhost:11434"
        )

    @pytest.mark.asyncio
    async def test_chat_ollama_success(self, assistant):
        """Test successful chat with mocked Ollama response."""
        mock_response = {
            "message": {
                "content": json.dumps({
                    "function_call": {
                        "function": "get_procedure_stats",
                        "arguments": {
                            "start_date": "2026-01-01",
                            "end_date": "2026-01-31"
                        }
                    },
                    "explanation": "Fetching procedure stats for January"
                })
            }
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )

            result = await assistant.chat(
                message="How many procedures this month?",
                clinic_id=uuid4(),
                user_id=uuid4(),
            )

            assert result.response is not None
            assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_chat_ollama_unavailable(self, assistant):
        """Test graceful handling when Ollama is unavailable."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            result = await assistant.chat(
                message="How many procedures?",
                clinic_id=uuid4(),
                user_id=uuid4(),
            )

            # Should fall back to keyword matching
            assert result.response is not None

    @pytest.mark.asyncio
    async def test_chat_ollama_timeout(self, assistant):
        """Test timeout handling."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            result = await assistant.chat(
                message="Revenue today?",
                clinic_id=uuid4(),
                user_id=uuid4(),
            )

            # Should fall back gracefully
            assert result.response is not None

    @pytest.mark.asyncio
    async def test_chat_malformed_llm_response(self, assistant):
        """Test handling of malformed LLM response."""
        mock_response = {
            "message": {
                "content": "This is not valid JSON"
            }
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )

            result = await assistant.chat(
                message="How many appointments?",
                clinic_id=uuid4(),
                user_id=uuid4(),
            )

            # Should handle gracefully
            assert result.response is not None

    @pytest.mark.asyncio
    async def test_chat_missing_function_in_response(self, assistant):
        """Test handling when LLM doesn't return function call."""
        mock_response = {
            "message": {
                "content": json.dumps({
                    "clarification_needed": "What would you like to know?",
                    "suggestions": ["Example 1", "Example 2"]
                })
            }
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )

            result = await assistant.chat(
                message="Tell me something",
                clinic_id=uuid4(),
                user_id=uuid4(),
            )

            assert result.response is not None
            assert "not sure" in result.response or "help" in result.response

    def test_session_management(self, assistant):
        """Test conversation session management."""
        session_id = str(uuid4())
        assistant._sessions[session_id] = ConversationSession(
            session_id=session_id,
            user_id=str(uuid4()),
            clinic_id=str(uuid4()),
        )

        # Get session
        session = assistant.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id

        # Clear session
        cleared = assistant.clear_session(session_id)
        assert cleared is True

        # Session should be gone
        session = assistant.get_session(session_id)
        assert session is None

    def test_cleanup_old_sessions(self, assistant):
        """Test cleanup of old sessions."""
        old_session = ConversationSession(
            session_id=str(uuid4()),
            user_id=str(uuid4()),
            clinic_id=str(uuid4()),
        )
        old_session.updated_at = datetime.utcnow() - timedelta(hours=48)
        assistant._sessions[old_session.session_id] = old_session

        new_session = ConversationSession(
            session_id=str(uuid4()),
            user_id=str(uuid4()),
            clinic_id=str(uuid4()),
        )
        assistant._sessions[new_session.session_id] = new_session

        # Cleanup sessions older than 24 hours
        assistant.cleanup_old_sessions(max_age_hours=24)

        # Old session should be removed
        assert old_session.session_id not in assistant._sessions
        # New session should remain
        assert new_session.session_id in assistant._sessions

    def test_fallback_parse_procedure_query(self, assistant):
        """Test fallback parsing for procedure queries."""
        result = assistant._fallback_parse("How many echos this month?")
        assert result is not None
        assert result.function == FunctionName.GET_PROCEDURE_STATS

    def test_fallback_parse_revenue_query(self, assistant):
        """Test fallback parsing for revenue queries."""
        result = assistant._fallback_parse("What's the revenue today?")
        assert result is not None
        assert result.function == FunctionName.GET_REVENUE_ANALYTICS

    def test_fallback_parse_appointment_query(self, assistant):
        """Test fallback parsing for appointment queries."""
        result = assistant._fallback_parse("Show me appointment stats")
        assert result is not None
        assert result.function == FunctionName.GET_APPOINTMENT_STATS

    def test_fallback_parse_patient_search(self, assistant):
        """Test fallback parsing for patient search."""
        result = assistant._fallback_parse("Find patient Rajesh")
        assert result is not None
        assert result.function == FunctionName.SEARCH_PATIENTS

    def test_fallback_parse_doctor_stats(self, assistant):
        """Test fallback parsing for doctor stats."""
        result = assistant._fallback_parse("Dr. Sharma's performance")
        assert result is not None
        assert result.function == FunctionName.GET_DOCTOR_STATS


class TestAIAssistantFunctionCalling:
    """Tests for function calling and response generation."""

    @pytest.fixture
    def assistant(self):
        """Create AI assistant instance."""
        return PracticeAIAssistant()

    def test_generate_suggestions_procedure_stats(self, assistant):
        """Test suggestion generation for procedure stats."""
        from app.services.ai_assistant import FunctionCall, FunctionName

        fc = FunctionCall(
            function=FunctionName.GET_PROCEDURE_STATS,
            arguments={}
        )
        suggestions = assistant._generate_suggestions(fc, {})
        assert len(suggestions) > 0
        assert any("doctor" in s.lower() for s in suggestions)

    def test_generate_suggestions_revenue(self, assistant):
        """Test suggestion generation for revenue analytics."""
        from app.services.ai_assistant import FunctionCall, FunctionName

        fc = FunctionCall(
            function=FunctionName.GET_REVENUE_ANALYTICS,
            arguments={}
        )
        suggestions = assistant._generate_suggestions(fc, {})
        assert len(suggestions) > 0
        assert any("revenue" in s.lower() or "payment" in s.lower() for s in suggestions)

    def test_parse_relative_date_today(self, assistant):
        """Test parsing 'today'."""
        result = assistant._parse_relative_date("today")
        assert result == date.today()

    def test_parse_relative_date_yesterday(self, assistant):
        """Test parsing 'yesterday'."""
        result = assistant._parse_relative_date("yesterday")
        assert result == date.today() - timedelta(days=1)

    def test_parse_relative_date_this_month_start(self, assistant):
        """Test parsing 'this month start'."""
        result = assistant._parse_relative_date("this month start")
        assert result == date.today().replace(day=1)

    def test_parse_function_arguments_dates(self, assistant):
        """Test parsing function arguments with dates."""
        args = {
            "start_date": "2026-01-15",
            "end_date": "2026-01-31",
        }
        parsed = assistant._parse_function_arguments(args)
        assert parsed["start_date"] == date(2026, 1, 15)
        assert parsed["end_date"] == date(2026, 1, 31)

    def test_parse_function_arguments_uuid(self, assistant):
        """Test parsing function arguments with UUIDs."""
        test_uuid = uuid4()
        args = {"doctor_id": str(test_uuid)}
        parsed = assistant._parse_function_arguments(args)
        assert parsed["doctor_id"] == test_uuid


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_entity_extractor_with_special_characters(self):
        """Test entity extraction with special characters in input."""
        extractor = EntityExtractor(MagicMock())
        message = "Book for @#$% tomorrow!!! at 3pm???"

        extracted_date = extractor.extract_date(message)
        extracted_time = extractor.extract_time(message)

        assert extracted_date == date.today() + timedelta(days=1)
        assert extracted_time == time(15, 0)

    @pytest.mark.asyncio
    async def test_entity_extractor_empty_message(self):
        """Test entity extraction with empty message."""
        extractor = EntityExtractor(MagicMock())

        assert extractor.extract_date("") is None
        assert extractor.extract_time("") is None
        assert extractor.extract_urgency("") == "low"
        assert extractor.extract_reason("") is None

    @pytest.mark.asyncio
    async def test_action_executor_exception_handling(self):
        """Test action executor handles exceptions gracefully."""
        mock_db = MagicMock()
        mock_db.get = AsyncMock(side_effect=Exception("Database error"))

        executor = AIActionExecutor(mock_db)

        result = await executor.execute_action(
            action_type=ActionType.BOOK_APPOINTMENT,
            params={
                "patient_id": uuid4(),
                "date": date.today(),
                "time": time(15, 0),
            },
            user_id=uuid4(),
            clinic_id=uuid4(),
        )

        assert not result.success
        assert "Failed to execute action" in result.message

    def test_action_definitions_completeness(self):
        """Test that all action types have proper definitions."""
        executor = AIActionExecutor(MagicMock())

        for action_type in ActionType:
            assert action_type.value in executor.ACTION_DEFINITIONS
            defn = executor.ACTION_DEFINITIONS[action_type.value]
            assert "description" in defn
            assert "parameters" in defn
            assert "requires_confirmation" in defn
