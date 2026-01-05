"""
Tests for Google Calendar Sync functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy import select

from app.integrations.google_calendar import GoogleCalendarIntegration
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.calendar_settings import DoctorCalendarSettings
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.services.calendar_sync import CalendarSyncService


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar integration."""
    with patch("app.integrations.google_calendar.get_google_calendar_integration") as mock:
        integration = MagicMock(spec=GoogleCalendarIntegration)
        integration.is_configured.return_value = True
        integration.encrypt_token.return_value = "encrypted_token"
        integration.decrypt_token.return_value = "decrypted_token"
        integration.create_event.return_value = "event_123"
        integration.update_event.return_value = None
        integration.delete_event.return_value = None
        integration.check_conflicts.return_value = []
        mock.return_value = integration
        yield integration


@pytest.fixture
async def doctor_with_calendar(db_session, clinic):
    """Create a doctor with calendar settings."""
    doctor = Doctor(
        name="Dr. Test",
        clinic_id=clinic.id,
        specialization="General",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)

    settings = DoctorCalendarSettings(
        doctor_id=doctor.id,
        google_calendar_id="primary",
        google_refresh_token="encrypted_refresh_token",
        sync_enabled=True,
    )
    db_session.add(settings)
    await db_session.commit()

    return doctor


@pytest.fixture
async def patient(db_session, clinic):
    """Create a test patient."""
    patient = Patient(
        first_name="John",
        last_name="Doe",
        phone="1234567890",
        clinic_id=clinic.id,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest.fixture
async def appointment(db_session, doctor_with_calendar, patient):
    """Create a test appointment."""
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor_with_calendar.id,
        scheduled_start=start_time,
        scheduled_end=end_time,
        duration_minutes=30,
        appointment_type=AppointmentType.NEW_CONSULTATION.value,
        chief_complaint="Regular checkup",
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


class TestGoogleCalendarIntegration:
    """Test Google Calendar integration."""

    @pytest.mark.asyncio


    async def test_encryption(self):
        """Test token encryption and decryption."""
        integration = GoogleCalendarIntegration(
            client_id="test_id",
            client_secret="test_secret",
            encryption_key="test_key_1234567890123456789012",
        )

        token = "my_refresh_token"
        encrypted = integration.encrypt_token(token)
        decrypted = integration.decrypt_token(encrypted)

        assert encrypted != token
        assert decrypted == token

    @pytest.mark.asyncio


    async def test_is_configured(self):
        """Test configuration check."""
        # Not configured
        integration = GoogleCalendarIntegration()
        assert not integration.is_configured()

        # Configured
        integration = GoogleCalendarIntegration(
            client_id="test_id",
            client_secret="test_secret",
        )
        assert integration.is_configured()


class TestCalendarSyncService:
    """Test Calendar Sync Service."""

    @pytest.mark.asyncio


    async def test_get_doctor_calendar_settings(
        self, db_session, doctor_with_calendar
    ):
        """Test retrieving doctor calendar settings."""
        service = CalendarSyncService(db_session)
        settings = await service.get_doctor_calendar_settings(doctor_with_calendar.id)

        assert settings is not None
        assert settings.doctor_id == doctor_with_calendar.id
        assert settings.sync_enabled is True

    @pytest.mark.asyncio


    async def test_get_settings_when_not_configured(self, db_session, doctor):
        """Test retrieving settings when doctor has no calendar configured."""
        service = CalendarSyncService(db_session)
        settings = await service.get_doctor_calendar_settings(doctor.id)

        assert settings is None

    @pytest.mark.asyncio


    async def test_sync_appointment_creates_event(
        self, db_session, appointment, mock_google_calendar
    ):
        """Test syncing appointment creates calendar event."""
        service = CalendarSyncService(db_session)

        # Sync appointment
        success = await service.sync_appointment(appointment)

        assert success is True
        assert appointment.google_calendar_event_id == "event_123"
        assert appointment.calendar_sync_status == "synced"
        assert appointment.last_calendar_sync_at is not None

        # Verify create_event was called
        mock_google_calendar.create_event.assert_called_once()

    @pytest.mark.asyncio


    async def test_sync_appointment_updates_event(
        self, db_session, appointment, mock_google_calendar
    ):
        """Test syncing appointment updates existing event."""
        # Set existing event ID
        appointment.google_calendar_event_id = "event_456"
        await db_session.commit()

        service = CalendarSyncService(db_session)

        # Sync appointment
        success = await service.sync_appointment(appointment)

        assert success is True

        # Verify update_event was called
        mock_google_calendar.update_event.assert_called_once()

    @pytest.mark.asyncio


    async def test_sync_cancelled_appointment_deletes_event(
        self, db_session, appointment, mock_google_calendar
    ):
        """Test syncing cancelled appointment deletes event."""
        # Set existing event ID and cancel
        appointment.google_calendar_event_id = "event_789"
        appointment.status = AppointmentStatus.CANCELLED.value
        await db_session.commit()

        service = CalendarSyncService(db_session)

        # Sync appointment
        success = await service.sync_appointment(appointment)

        assert success is True
        assert appointment.calendar_sync_status == "deleted"

        # Verify delete_event was called
        mock_google_calendar.delete_event.assert_called_once()

    @pytest.mark.asyncio


    async def test_sync_appointment_when_sync_disabled(
        self, db_session, appointment
    ):
        """Test sync skips when calendar sync is disabled."""
        # Disable sync
        result = await db_session.execute(
            select(DoctorCalendarSettings).where(
                DoctorCalendarSettings.doctor_id == appointment.doctor_id
            )
        )
        settings = result.scalar_one()
        settings.sync_enabled = False
        await db_session.commit()

        service = CalendarSyncService(db_session)

        # Sync appointment
        success = await service.sync_appointment(appointment)

        assert success is False
        assert appointment.calendar_sync_status == "skipped"

    @pytest.mark.asyncio


    async def test_check_conflicts(
        self, db_session, doctor_with_calendar, mock_google_calendar
    ):
        """Test conflict checking."""
        # Mock conflicts
        mock_google_calendar.check_conflicts.return_value = [
            {
                "event_id": "conflict_1",
                "summary": "Existing Meeting",
                "start": "2026-01-05T10:00:00Z",
                "end": "2026-01-05T11:00:00Z",
            }
        ]

        service = CalendarSyncService(db_session)

        start_time = datetime(2026, 1, 5, 10, 30, tzinfo=timezone.utc)
        end_time = datetime(2026, 1, 5, 11, 0, tzinfo=timezone.utc)

        conflicts = await service.check_conflicts(
            doctor_id=doctor_with_calendar.id,
            start_time=start_time,
            end_time=end_time,
        )

        assert len(conflicts) == 1
        assert conflicts[0]["event_id"] == "conflict_1"

    @pytest.mark.asyncio


    async def test_sync_multiple_appointments(
        self, db_session, doctor_with_calendar, patient, mock_google_calendar
    ):
        """Test syncing multiple appointments."""
        # Create multiple appointments
        appointments = []
        for i in range(3):
            start_time = datetime.now(timezone.utc) + timedelta(days=i + 1)
            end_time = start_time + timedelta(minutes=30)

            appt = Appointment(
                patient_id=patient.id,
                doctor_id=doctor_with_calendar.id,
                scheduled_start=start_time,
                scheduled_end=end_time,
                duration_minutes=30,
                appointment_type=AppointmentType.NEW_CONSULTATION.value,
            )
            db_session.add(appt)
            appointments.append(appt)

        await db_session.commit()

        service = CalendarSyncService(db_session)

        # Sync all appointments
        stats = await service.sync_multiple_appointments(
            doctor_id=doctor_with_calendar.id
        )

        assert stats["synced"] == 3
        assert stats["failed"] == 0

    @pytest.mark.asyncio


    async def test_disconnect_calendar(
        self, db_session, doctor_with_calendar, appointment, mock_google_calendar
    ):
        """Test disconnecting calendar."""
        # Set event ID
        appointment.google_calendar_event_id = "event_999"
        await db_session.commit()

        service = CalendarSyncService(db_session)

        # Disconnect
        success = await service.disconnect_calendar(doctor_with_calendar.id)

        assert success is True

        # Verify settings deleted
        result = await db_session.execute(
            select(DoctorCalendarSettings).where(
                DoctorCalendarSettings.doctor_id == doctor_with_calendar.id
            )
        )
        settings = result.scalar_one_or_none()
        assert settings is None

        # Verify event ID cleared
        await db_session.refresh(appointment)
        assert appointment.google_calendar_event_id is None

    @pytest.mark.asyncio


    async def test_event_description_formatting(
        self, db_session, appointment
    ):
        """Test event description is properly formatted."""
        service = CalendarSyncService(db_session)

        description = service._build_event_description(appointment)

        assert "Patient: John Doe" in description
        assert "Phone: 1234567890" in description
        assert "Type: New Consultation" in description
        assert "Reason: Regular checkup" in description
        assert "DocAssist Practice Manager" in description


class TestCalendarAPIEndpoints:
    """Test Calendar API endpoints."""

    @pytest.mark.asyncio


    async def test_get_auth_url(self, client, authenticated_user, doctor):
        """Test getting OAuth authorization URL."""
        with patch("app.integrations.google_calendar.get_google_calendar_integration") as mock:
            integration = MagicMock()
            integration.is_configured.return_value = True
            integration.get_authorization_url.return_value = "https://accounts.google.com/oauth..."
            mock.return_value = integration

            response = await client.get(
                f"/api/v1/calendar/auth-url?doctor_id={str(doctor.id)}",
                headers=authenticated_user,
            )

            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "state" in data

    @pytest.mark.asyncio


    async def test_oauth_callback(self, client, db_session, doctor):
        """Test OAuth callback handling."""
        with patch("app.integrations.google_calendar.get_google_calendar_integration") as mock:
            integration = MagicMock()
            integration.exchange_code_for_token.return_value = {
                "access_token": "access_token",
                "refresh_token": "refresh_token",
                "expires_in": 3600,
            }
            integration.encrypt_token.return_value = "encrypted_token"
            integration.list_calendars.return_value = [
                {"id": "primary", "summary": "Main Calendar"}
            ]
            mock.return_value = integration

            # First get auth URL to create state
            from app.api.v1.calendar import _oauth_states
            state = "test_state"
            _oauth_states[state] = doctor.id

            response = await client.post(
                "/api/v1/calendar/callback",
                json={
                    "code": "auth_code",
                    "state": state,
                    "doctor_id": str(doctor.id),
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio


    async def test_get_sync_status(
        self, client, authenticated_user, doctor_with_calendar
    ):
        """Test getting sync status."""
        response = await client.get(
            f"/api/v1/calendar/status?doctor_id={str(doctor_with_calendar.id)}",
            headers=authenticated_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["sync_enabled"] is True

    @pytest.mark.asyncio


    async def test_trigger_sync(
        self, client, authenticated_user, doctor_with_calendar, mock_google_calendar
    ):
        """Test triggering manual sync."""
        response = await client.post(
            "/api/v1/calendar/sync",
            headers=authenticated_user,
            json={"doctor_id": str(doctor_with_calendar.id), "force": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert "synced" in data
        assert "failed" in data
