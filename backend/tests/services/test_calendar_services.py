"""
Tests for Calendar and Scheduling Services.

Tests:
- CalendarSyncService (Google Calendar sync)
- BackgroundCalendarSyncService (periodic sync)
- ScheduleOptimizer (gap detection, overbooking)
- ReminderService (SMS/WhatsApp reminders)
"""

import pytest
from datetime import datetime, timedelta, timezone, date
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from uuid import uuid4

from app.services.calendar_sync import CalendarSyncService
from app.services.background_calendar_sync import BackgroundCalendarSyncService
from app.services.schedule_optimizer import ScheduleOptimizer, PROCEDURE_DURATIONS
from app.services.reminder import ReminderService
from app.models.appointment import Appointment, AppointmentStatus
from app.models.calendar_settings import DoctorCalendarSettings
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.procedure import Procedure
from app.schemas.insights import TimeGap, BufferSuggestion, OverbookingRisk
from app.integrations.sms import MessageResult, MessageChannel, SMSService


# ==================== CalendarSyncService Tests ====================


class TestCalendarSyncService:
    """Tests for CalendarSyncService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_gcal(self):
        """Create mock Google Calendar integration."""
        gcal = MagicMock()
        gcal.is_configured.return_value = True
        gcal.create_event.return_value = "event_id_12345"
        gcal.update_event.return_value = None
        gcal.delete_event.return_value = None
        gcal.check_conflicts.return_value = []
        return gcal

    @pytest.fixture
    def calendar_sync_service(self, mock_db, mock_gcal):
        """Create calendar sync service with mocks."""
        service = CalendarSyncService(mock_db)
        service.gcal = mock_gcal
        return service

    @pytest.fixture
    def mock_calendar_settings(self):
        """Create mock calendar settings."""
        settings = MagicMock(spec=DoctorCalendarSettings)
        settings.doctor_id = uuid4()
        settings.google_calendar_id = "primary"
        settings.google_refresh_token = "encrypted_token_123"
        settings.sync_enabled = True
        settings.event_visibility = "private"
        settings.event_reminders = None
        settings.total_synced = 10
        settings.total_failed = 0
        settings.last_sync_error = None
        return settings

    @pytest.fixture
    def mock_appointment(self):
        """Create mock appointment."""
        appointment = MagicMock(spec=Appointment)
        appointment.id = uuid4()
        appointment.doctor_id = uuid4()
        appointment.patient_id = uuid4()
        appointment.status = AppointmentStatus.SCHEDULED
        appointment.scheduled_start = datetime.now(timezone.utc) + timedelta(days=1)
        appointment.scheduled_end = appointment.scheduled_start + timedelta(minutes=15)
        appointment.chief_complaint = "Follow-up checkup"
        appointment.notes = "Patient requested morning slot"
        appointment.google_calendar_event_id = None
        appointment.calendar_sync_status = None
        appointment.calendar_sync_error = None
        appointment.last_calendar_sync_at = None

        # Mock relationships
        mock_patient = MagicMock(spec=Patient)
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.phone = "+919876543210"
        appointment.patient = mock_patient

        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.name = "Dr. Smith"
        mock_clinic = MagicMock()
        mock_clinic.address = "123 Main St, Mumbai"
        mock_doctor.clinic = mock_clinic
        appointment.doctor = mock_doctor

        return appointment

    @pytest.mark.asyncio
    async def test_get_doctor_calendar_settings(
        self, calendar_sync_service, mock_db, mock_calendar_settings
    ):
        """Test getting calendar settings for doctor."""
        doctor_id = uuid4()

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_settings
        mock_db.execute.return_value = mock_result

        settings = await calendar_sync_service.get_doctor_calendar_settings(doctor_id)

        assert settings == mock_calendar_settings
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_appointment_not_configured(
        self, calendar_sync_service, mock_appointment
    ):
        """Test sync when Google Calendar not configured."""
        calendar_sync_service.gcal.is_configured.return_value = False

        result = await calendar_sync_service.sync_appointment(mock_appointment)

        assert result is False
        calendar_sync_service.gcal.create_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_appointment_disabled(
        self, calendar_sync_service, mock_db, mock_appointment, mock_calendar_settings
    ):
        """Test sync when calendar sync is disabled."""
        mock_calendar_settings.sync_enabled = False

        # Mock settings query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_settings
        mock_db.execute.return_value = mock_result

        result = await calendar_sync_service.sync_appointment(mock_appointment)

        assert result is False
        assert mock_appointment.calendar_sync_status == "skipped"

    @pytest.mark.asyncio
    async def test_create_calendar_event_success(
        self,
        calendar_sync_service,
        mock_db,
        mock_appointment,
        mock_calendar_settings,
        mock_gcal,
    ):
        """Test successfully creating a calendar event."""
        # Mock settings query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_settings
        mock_db.execute.return_value = mock_result

        result = await calendar_sync_service.sync_appointment(mock_appointment)

        assert result is True
        assert mock_appointment.google_calendar_event_id == "event_id_12345"
        assert mock_appointment.calendar_sync_status == "synced"
        assert mock_appointment.calendar_sync_error is None
        assert mock_appointment.last_calendar_sync_at is not None
        assert mock_calendar_settings.total_synced == 11  # Incremented from 10
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_calendar_event_success(
        self,
        calendar_sync_service,
        mock_db,
        mock_appointment,
        mock_calendar_settings,
        mock_gcal,
    ):
        """Test successfully updating an existing calendar event."""
        # Set existing event ID
        mock_appointment.google_calendar_event_id = "existing_event_123"

        # Mock settings query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_settings
        mock_db.execute.return_value = mock_result

        result = await calendar_sync_service.sync_appointment(mock_appointment)

        assert result is True
        mock_gcal.update_event.assert_called_once()
        assert mock_appointment.calendar_sync_status == "synced"
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_calendar_event_on_cancellation(
        self,
        calendar_sync_service,
        mock_db,
        mock_appointment,
        mock_calendar_settings,
        mock_gcal,
    ):
        """Test deleting calendar event when appointment is cancelled."""
        # Set appointment as cancelled with existing event
        mock_appointment.status = AppointmentStatus.CANCELLED
        mock_appointment.google_calendar_event_id = "event_to_delete"

        # Mock settings query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_settings
        mock_db.execute.return_value = mock_result

        result = await calendar_sync_service.sync_appointment(mock_appointment)

        assert result is True
        mock_gcal.delete_event.assert_called_once()
        assert mock_appointment.google_calendar_event_id is None
        assert mock_appointment.calendar_sync_status == "deleted"

    @pytest.mark.asyncio
    async def test_sync_appointment_api_error(
        self,
        calendar_sync_service,
        mock_db,
        mock_appointment,
        mock_calendar_settings,
        mock_gcal,
    ):
        """Test handling Google Calendar API errors."""
        # Mock API error
        mock_gcal.create_event.side_effect = Exception("API Error: 500")

        # Mock settings query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_settings
        mock_db.execute.return_value = mock_result

        result = await calendar_sync_service.sync_appointment(mock_appointment)

        assert result is False
        assert mock_appointment.calendar_sync_status == "failed"
        assert "API Error: 500" in mock_appointment.calendar_sync_error
        assert mock_calendar_settings.total_failed == 1

    @pytest.mark.asyncio
    async def test_check_conflicts(
        self, calendar_sync_service, mock_db, mock_calendar_settings, mock_gcal
    ):
        """Test checking calendar conflicts."""
        doctor_id = uuid4()
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=30)

        # Mock conflicts
        mock_gcal.check_conflicts.return_value = [
            {
                "event_id": "conflict_1",
                "summary": "Existing Meeting",
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            }
        ]

        # Mock settings query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_settings
        mock_db.execute.return_value = mock_result

        conflicts = await calendar_sync_service.check_conflicts(
            doctor_id, start_time, end_time
        )

        assert len(conflicts) == 1
        assert conflicts[0]["summary"] == "Existing Meeting"

    @pytest.mark.asyncio
    async def test_sync_multiple_appointments(
        self, calendar_sync_service, mock_db, mock_calendar_settings
    ):
        """Test syncing multiple appointments."""
        doctor_id = uuid4()

        # Mock appointments
        appt1 = MagicMock(spec=Appointment)
        appt1.id = uuid4()
        appt2 = MagicMock(spec=Appointment)
        appt2.id = uuid4()

        # Mock query results
        mock_settings_result = AsyncMock()
        mock_settings_result.scalar_one_or_none.return_value = mock_calendar_settings

        mock_appts_result = AsyncMock()
        mock_appts_result.scalars.return_value.all.return_value = [appt1, appt2]

        mock_db.execute.side_effect = [mock_settings_result, mock_appts_result]

        # Mock sync_appointment to return success
        with patch.object(
            calendar_sync_service, "sync_appointment", new=AsyncMock(return_value=True)
        ) as mock_sync:
            stats = await calendar_sync_service.sync_multiple_appointments(doctor_id)

        assert stats["synced"] == 2
        assert stats["failed"] == 0
        assert mock_sync.call_count == 2

    @pytest.mark.asyncio
    async def test_disconnect_calendar(
        self, calendar_sync_service, mock_db, mock_calendar_settings, mock_gcal
    ):
        """Test disconnecting Google Calendar."""
        doctor_id = uuid4()

        # Mock appointments with calendar events
        appt1 = MagicMock(spec=Appointment)
        appt1.google_calendar_event_id = "event_1"
        appt2 = MagicMock(spec=Appointment)
        appt2.google_calendar_event_id = "event_2"

        # Mock queries
        mock_settings_result = AsyncMock()
        mock_settings_result.scalar_one_or_none.return_value = mock_calendar_settings

        mock_appts_result = AsyncMock()
        mock_appts_result.scalars.return_value.all.return_value = [appt1, appt2]

        mock_db.execute.side_effect = [mock_settings_result, mock_appts_result]

        result = await calendar_sync_service.disconnect_calendar(doctor_id)

        assert result is True
        assert mock_gcal.delete_event.call_count == 2
        assert appt1.google_calendar_event_id is None
        assert appt2.google_calendar_event_id is None
        mock_db.delete.assert_called_once_with(mock_calendar_settings)


# ==================== BackgroundCalendarSyncService Tests ====================


class TestBackgroundCalendarSyncService:
    """Tests for BackgroundCalendarSyncService."""

    @pytest.fixture
    def bg_sync_service(self):
        """Create background sync service."""
        with patch("app.services.background_calendar_sync.create_async_engine"):
            with patch("app.services.background_calendar_sync.sessionmaker"):
                service = BackgroundCalendarSyncService()
                service.async_session_maker = AsyncMock()
                return service

    @pytest.mark.asyncio
    async def test_sync_all_doctors(self, bg_sync_service):
        """Test syncing all doctors with calendar enabled."""
        # Mock database session
        mock_db = AsyncMock()
        bg_sync_service.async_session_maker.return_value.__aenter__.return_value = (
            mock_db
        )

        # Mock calendar settings
        settings1 = MagicMock(spec=DoctorCalendarSettings)
        settings1.doctor_id = uuid4()
        settings1.sync_enabled = True
        settings1.last_synced_at = None

        settings2 = MagicMock(spec=DoctorCalendarSettings)
        settings2.doctor_id = uuid4()
        settings2.sync_enabled = True
        settings2.last_synced_at = datetime.now(timezone.utc) - timedelta(hours=1)

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [settings1, settings2]
        mock_db.execute.return_value = mock_result

        # Mock sync service
        with patch(
            "app.services.background_calendar_sync.CalendarSyncService"
        ) as mock_sync_cls:
            mock_sync = AsyncMock()
            mock_sync.sync_multiple_appointments.return_value = {
                "synced": 5,
                "failed": 1,
            }
            mock_sync_cls.return_value = mock_sync

            await bg_sync_service._sync_all_doctors()

            # Should be called twice (once per doctor)
            assert mock_sync.sync_multiple_appointments.call_count == 2

    def test_start_background_sync(self, bg_sync_service):
        """Test starting background sync scheduler."""
        assert not bg_sync_service._running

        bg_sync_service.start(interval_minutes=30)

        assert bg_sync_service._running
        assert bg_sync_service.scheduler.running

        # Clean up
        bg_sync_service.stop()

    def test_stop_background_sync(self, bg_sync_service):
        """Test stopping background sync scheduler."""
        bg_sync_service.start(interval_minutes=30)
        assert bg_sync_service._running

        bg_sync_service.stop()

        assert not bg_sync_service._running
        assert not bg_sync_service.scheduler.running

    @pytest.mark.asyncio
    async def test_trigger_manual_sync(self, bg_sync_service):
        """Test triggering manual sync."""
        with patch.object(
            bg_sync_service, "_sync_all_doctors", new=AsyncMock()
        ) as mock_sync:
            await bg_sync_service.trigger_manual_sync()
            mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_handles_errors(self, bg_sync_service):
        """Test that background sync handles errors gracefully."""
        # Mock database session
        mock_db = AsyncMock()
        bg_sync_service.async_session_maker.return_value.__aenter__.return_value = (
            mock_db
        )

        # Mock settings with one that will fail
        settings1 = MagicMock(spec=DoctorCalendarSettings)
        settings1.doctor_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [settings1]
        mock_db.execute.return_value = mock_result

        # Mock sync service to raise error
        with patch(
            "app.services.background_calendar_sync.CalendarSyncService"
        ) as mock_sync_cls:
            mock_sync = AsyncMock()
            mock_sync.sync_multiple_appointments.side_effect = Exception("Sync failed")
            mock_sync_cls.return_value = mock_sync

            # Should not raise exception
            await bg_sync_service._sync_all_doctors()


# ==================== ScheduleOptimizer Tests ====================


class TestScheduleOptimizer:
    """Tests for ScheduleOptimizer."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def optimizer(self, mock_db):
        """Create schedule optimizer."""
        return ScheduleOptimizer(mock_db)

    @pytest.mark.asyncio
    async def test_find_gaps_no_appointments(self, optimizer, mock_db):
        """Test finding gaps when no appointments exist."""
        clinic_id = uuid4()
        doctor_id = uuid4()
        target_date = date.today()

        # Mock empty appointments
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        gaps = await optimizer.find_gaps(clinic_id, doctor_id, target_date)

        assert len(gaps) == 1
        assert gaps[0].duration_minutes == 540  # 9 hours

    @pytest.mark.asyncio
    async def test_find_gaps_with_appointments(self, optimizer, mock_db):
        """Test finding gaps between appointments."""
        clinic_id = uuid4()
        doctor_id = uuid4()
        target_date = date.today()

        # Create mock appointments with gaps
        appt1 = MagicMock(spec=Appointment)
        appt1.appointment_date = datetime.combine(
            target_date, datetime.min.time().replace(hour=10, minute=0)
        )
        appt1.duration_minutes = 15
        appt1.status = "scheduled"

        appt2 = MagicMock(spec=Appointment)
        appt2.appointment_date = datetime.combine(
            target_date, datetime.min.time().replace(hour=11, minute=0)
        )
        appt2.duration_minutes = 15
        appt2.status = "scheduled"

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [appt1, appt2]
        mock_db.execute.return_value = mock_result

        gaps = await optimizer.find_gaps(
            clinic_id, doctor_id, target_date, min_gap_minutes=30
        )

        # Should find gap before first appt, between appts, and after last appt
        assert len(gaps) > 0
        # Gap between 10:15 and 11:00 should be 45 minutes
        middle_gaps = [g for g in gaps if g.duration_minutes == 45]
        assert len(middle_gaps) >= 1

    @pytest.mark.asyncio
    async def test_suggest_buffer_time_no_history(self, optimizer, mock_db):
        """Test buffer suggestion with no appointment history."""
        patient_id = uuid4()
        doctor_id = uuid4()

        # Mock empty history
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        suggestion = await optimizer.suggest_buffer_time(patient_id, doctor_id)

        assert suggestion is None

    @pytest.mark.asyncio
    async def test_suggest_buffer_time_with_overruns(self, optimizer, mock_db):
        """Test buffer suggestion based on appointment overruns."""
        patient_id = uuid4()
        doctor_id = uuid4()

        # Create appointments with overruns
        appt1 = MagicMock(spec=Appointment)
        appt1.duration_minutes = 15
        appt1.actual_duration_minutes = 25  # 10 min overrun

        appt2 = MagicMock(spec=Appointment)
        appt2.duration_minutes = 15
        appt2.actual_duration_minutes = 20  # 5 min overrun

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [appt1, appt2]
        mock_db.execute.return_value = mock_result

        suggestion = await optimizer.suggest_buffer_time(patient_id, doctor_id)

        assert suggestion is not None
        assert isinstance(suggestion, BufferSuggestion)
        assert suggestion.suggested_duration_minutes == 7  # Average of 10 and 5
        assert suggestion.confidence > 0

    @pytest.mark.asyncio
    async def test_analyze_overbooking_risk_low(self, optimizer, mock_db):
        """Test overbooking risk analysis - low risk."""
        clinic_id = uuid4()
        doctor_id = uuid4()
        target_date = date.today()

        # Create a few appointments (low load)
        appt1 = MagicMock(spec=Appointment)
        appt1.duration_minutes = 15

        appt2 = MagicMock(spec=Appointment)
        appt2.duration_minutes = 15

        # Mock queries
        mock_appts_result = AsyncMock()
        mock_appts_result.scalars.return_value.all.return_value = [appt1, appt2]

        mock_procs_result = AsyncMock()
        mock_procs_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_appts_result, mock_procs_result]

        risk = await optimizer.analyze_overbooking_risk(
            clinic_id, doctor_id, target_date
        )

        assert isinstance(risk, OverbookingRisk)
        assert risk.risk_level == "low"
        assert risk.total_procedures == 2
        assert risk.estimated_duration_minutes == 30

    @pytest.mark.asyncio
    async def test_analyze_overbooking_risk_high(self, optimizer, mock_db):
        """Test overbooking risk analysis - high risk (overbooked)."""
        clinic_id = uuid4()
        doctor_id = uuid4()
        target_date = date.today()

        # Create many appointments
        appointments = [
            MagicMock(spec=Appointment, duration_minutes=30) for _ in range(20)
        ]

        # Add a procedure
        proc = MagicMock(spec=Procedure)
        proc.procedure_type = "Echocardiogram"

        mock_appts_result = AsyncMock()
        mock_appts_result.scalars.return_value.all.return_value = appointments

        mock_procs_result = AsyncMock()
        mock_procs_result.scalars.return_value.all.return_value = [proc]

        mock_db.execute.side_effect = [mock_appts_result, mock_procs_result]

        risk = await optimizer.analyze_overbooking_risk(
            clinic_id, doctor_id, target_date
        )

        assert risk.risk_level == "high"
        assert "OVERBOOKED" in risk.recommendations[0]

    @pytest.mark.asyncio
    async def test_get_optimal_slot_for_procedure(self, optimizer, mock_db):
        """Test finding optimal slot for procedure."""
        clinic_id = uuid4()
        doctor_id = uuid4()
        target_date = date.today()
        procedure_type = "Echocardiogram"

        # Mock a gap that fits the procedure
        with patch.object(optimizer, "find_gaps") as mock_find_gaps:
            gap = TimeGap(
                start_time=datetime.combine(
                    target_date, datetime.min.time().replace(hour=10, minute=0)
                ),
                end_time=datetime.combine(
                    target_date, datetime.min.time().replace(hour=11, minute=0)
                ),
                duration_minutes=60,
                doctor_id=doctor_id,
                doctor_name="Dr. Smith",
            )
            mock_find_gaps.return_value = [gap]

            slot = await optimizer.get_optimal_slot_for_procedure(
                clinic_id, doctor_id, procedure_type, target_date
            )

            assert slot is not None
            assert slot == gap.start_time
            # Should request gap of at least procedure duration (30 min for Echo)
            mock_find_gaps.assert_called_once()
            call_args = mock_find_gaps.call_args
            assert call_args[1]["min_gap_minutes"] == PROCEDURE_DURATIONS[procedure_type]

    @pytest.mark.asyncio
    async def test_get_patient_appointment_patterns(self, optimizer, mock_db):
        """Test analyzing patient appointment patterns."""
        patient_id = uuid4()

        # Create appointments with various statuses
        appt1 = MagicMock(spec=Appointment, status="completed")
        appt2 = MagicMock(spec=Appointment, status="no_show")
        appt3 = MagicMock(spec=Appointment, status="cancelled")
        appt4 = MagicMock(spec=Appointment, status="completed")

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [
            appt1,
            appt2,
            appt3,
            appt4,
        ]
        mock_db.execute.return_value = mock_result

        patterns = await optimizer.get_patient_appointment_patterns(patient_id)

        assert patterns["total_appointments"] == 4
        assert patterns["no_show_rate"] == 25.0  # 1 out of 4
        assert patterns["cancellation_rate"] == 25.0  # 1 out of 4
        assert patterns["reliability_score"] == 50.0  # 2 out of 4 completed


# ==================== ReminderService Tests ====================


class TestReminderService:
    """Tests for ReminderService."""

    @pytest.fixture
    def mock_sms_service(self):
        """Create mock SMS service."""
        sms = AsyncMock(spec=SMSService)
        sms.send_appointment_reminder.return_value = MessageResult(
            success=True, message_id="msg_123", channel=MessageChannel.SMS
        )
        sms.send_appointment_confirmation.return_value = MessageResult(
            success=True, message_id="msg_124", channel=MessageChannel.WHATSAPP
        )
        sms.send_sms.return_value = MessageResult(
            success=True, message_id="msg_125", channel=MessageChannel.SMS
        )
        return sms

    @pytest.fixture
    def reminder_service(self, mock_sms_service):
        """Create reminder service with mock SMS."""
        return ReminderService(sms_service=mock_sms_service)

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_send_reminders_24_hours(
        self, reminder_service, mock_db, mock_sms_service
    ):
        """Test sending 24-hour reminders."""
        # Create appointments needing reminders
        appt1 = MagicMock(spec=Appointment)
        appt1.id = uuid4()
        appt1.scheduled_start = datetime.now(timezone.utc) + timedelta(hours=24)
        appt1.status = AppointmentStatus.SCHEDULED.value
        appt1.reminder_sent = False

        mock_patient = MagicMock(spec=Patient)
        mock_patient.phone = "+919876543210"
        mock_patient.full_name = "John Doe"
        mock_patient.sms_consent = True
        mock_patient.whatsapp_consent = False
        appt1.patient = mock_patient

        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.name = "Dr. Smith"
        appt1.doctor = mock_doctor

        # Mock query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [appt1]
        mock_db.execute.return_value = mock_result

        stats = await reminder_service.send_reminders(mock_db, hours_before=24)

        assert stats["total"] == 1
        assert stats["sent"] == 1
        assert stats["failed"] == 0
        assert appt1.reminder_sent is True
        assert appt1.reminder_sent_at is not None
        mock_sms_service.send_appointment_reminder.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_reminders_skip_no_consent(
        self, reminder_service, mock_db, mock_sms_service
    ):
        """Test skipping reminders when patient has no consent."""
        appt = MagicMock(spec=Appointment)
        appt.id = uuid4()
        appt.scheduled_start = datetime.now(timezone.utc) + timedelta(hours=24)
        appt.status = AppointmentStatus.SCHEDULED.value
        appt.reminder_sent = False

        mock_patient = MagicMock(spec=Patient)
        mock_patient.sms_consent = False
        mock_patient.whatsapp_consent = False
        appt.patient = mock_patient

        mock_doctor = MagicMock(spec=Doctor)
        appt.doctor = mock_doctor

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [appt]
        mock_db.execute.return_value = mock_result

        stats = await reminder_service.send_reminders(mock_db, hours_before=24)

        assert stats["total"] == 1
        assert stats["skipped"] == 1
        assert stats["sent"] == 0
        mock_sms_service.send_appointment_reminder.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_reminders_handle_failure(
        self, reminder_service, mock_db, mock_sms_service
    ):
        """Test handling reminder send failures."""
        appt = MagicMock(spec=Appointment)
        appt.id = uuid4()
        appt.scheduled_start = datetime.now(timezone.utc) + timedelta(hours=24)
        appt.status = AppointmentStatus.SCHEDULED.value
        appt.reminder_sent = False

        mock_patient = MagicMock(spec=Patient)
        mock_patient.phone = "+919876543210"
        mock_patient.full_name = "John Doe"
        mock_patient.sms_consent = True
        mock_patient.whatsapp_consent = False
        appt.patient = mock_patient

        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.name = "Dr. Smith"
        appt.doctor = mock_doctor

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [appt]
        mock_db.execute.return_value = mock_result

        # Mock SMS failure
        mock_sms_service.send_appointment_reminder.return_value = MessageResult(
            success=False, error="SMS service unavailable"
        )

        stats = await reminder_service.send_reminders(mock_db, hours_before=24)

        assert stats["total"] == 1
        assert stats["failed"] == 1
        assert stats["sent"] == 0

    @pytest.mark.asyncio
    async def test_send_confirmation(
        self, reminder_service, mock_db, mock_sms_service
    ):
        """Test sending appointment confirmation."""
        appt = MagicMock(spec=Appointment)
        appt.id = uuid4()
        appt.patient_id = uuid4()
        appt.doctor_id = uuid4()
        appt.scheduled_start = datetime.now(timezone.utc) + timedelta(days=1)
        appt.token_number = 42

        mock_patient = MagicMock(spec=Patient)
        mock_patient.id = appt.patient_id
        mock_patient.phone = "+919876543210"
        mock_patient.full_name = "John Doe"
        mock_patient.whatsapp_consent = True
        appt.patient = mock_patient

        mock_clinic = MagicMock()
        mock_clinic.address = "123 Main St"
        mock_clinic.city = "Mumbai"

        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.id = appt.doctor_id
        mock_doctor.name = "Dr. Smith"
        mock_doctor.clinic = mock_clinic
        appt.doctor = mock_doctor

        result = await reminder_service.send_confirmation(appt, mock_db)

        assert result is True
        mock_sms_service.send_appointment_confirmation.assert_called_once()
        call_args = mock_sms_service.send_appointment_confirmation.call_args
        assert call_args[1]["prefer_whatsapp"] is True

    @pytest.mark.asyncio
    async def test_send_cancellation_notice(
        self, reminder_service, mock_db, mock_sms_service
    ):
        """Test sending cancellation notice."""
        appt = MagicMock(spec=Appointment)
        appt.id = uuid4()
        appt.patient_id = uuid4()
        appt.doctor_id = uuid4()
        appt.scheduled_start = datetime.now(timezone.utc) + timedelta(days=1)

        mock_patient = MagicMock(spec=Patient)
        mock_patient.id = appt.patient_id
        mock_patient.phone = "+919876543210"
        appt.patient = mock_patient

        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.id = appt.doctor_id
        mock_doctor.name = "Dr. Smith"
        appt.doctor = mock_doctor

        result = await reminder_service.send_cancellation_notice(appt, mock_db)

        assert result is True
        mock_sms_service.send_sms.assert_called_once()

    @pytest.mark.asyncio
    async def test_avoid_duplicate_reminders(
        self, reminder_service, mock_db, mock_sms_service
    ):
        """Test that already-sent reminders are not sent again."""
        # Create appointment with reminder already sent
        appt = MagicMock(spec=Appointment)
        appt.id = uuid4()
        appt.scheduled_start = datetime.now(timezone.utc) + timedelta(hours=24)
        appt.status = AppointmentStatus.SCHEDULED.value
        appt.reminder_sent = True  # Already sent!

        # Mock empty query result (filtered out by query)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        stats = await reminder_service.send_reminders(mock_db, hours_before=24)

        assert stats["total"] == 0
        assert stats["sent"] == 0
        mock_sms_service.send_appointment_reminder.assert_not_called()

    @pytest.mark.asyncio
    async def test_1_hour_reminders(self, reminder_service, mock_db, mock_sms_service):
        """Test sending 1-hour reminders."""
        appt = MagicMock(spec=Appointment)
        appt.id = uuid4()
        appt.scheduled_start = datetime.now(timezone.utc) + timedelta(hours=1)
        appt.status = AppointmentStatus.SCHEDULED.value
        appt.reminder_sent = False

        mock_patient = MagicMock(spec=Patient)
        mock_patient.phone = "+919876543210"
        mock_patient.full_name = "Jane Doe"
        mock_patient.sms_consent = True
        mock_patient.whatsapp_consent = True
        appt.patient = mock_patient

        mock_doctor = MagicMock(spec=Doctor)
        mock_doctor.name = "Dr. Jones"
        appt.doctor = mock_doctor

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [appt]
        mock_db.execute.return_value = mock_result

        stats = await reminder_service.send_reminders(mock_db, hours_before=1)

        assert stats["sent"] == 1
        # Should prefer WhatsApp
        call_args = mock_sms_service.send_appointment_reminder.call_args
        assert call_args[1]["prefer_whatsapp"] is True
