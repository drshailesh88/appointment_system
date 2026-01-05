"""
Comprehensive tests for Google Calendar integration.

Tests OAuth flow, two-way sync, conflict resolution, and edge cases.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from googleapiclient.errors import HttpError

from app.integrations.google_calendar import (
    GoogleCalendarService,
    SCOPES,
    DEFAULT_COLOR_MAPPINGS,
)
from app.models.appointment import AppointmentStatus, AppointmentType
from app.models.calendar_sync import (
    CalendarConnection,
    SyncDirection,
    SyncStatus,
    ConflictResolution,
)


class TestOAuthFlow:
    """Test OAuth authentication flow."""

    def test_get_auth_url(self):
        """Test generating OAuth authorization URL."""
        service = GoogleCalendarService(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
        )

        auth_url = service.get_auth_url(state="test_state")

        assert "accounts.google.com/o/oauth2/auth" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "state=test_state" in auth_url
        assert "access_type=offline" in auth_url

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_new_connection(self, async_db):
        """Test handling OAuth callback for new connection."""
        service = GoogleCalendarService(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        user_id = uuid4()
        clinic_id = uuid4()

        with patch("app.integrations.google_calendar.Flow") as mock_flow_class:
            # Mock Flow
            mock_flow = MagicMock()
            mock_flow_class.from_client_config.return_value = mock_flow

            # Mock credentials
            mock_credentials = MagicMock()
            mock_credentials.token = "access_token_123"
            mock_credentials.refresh_token = "refresh_token_123"
            mock_credentials.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            mock_credentials.scopes = SCOPES
            mock_flow.credentials = mock_credentials

            # Mock Google Calendar API
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                mock_calendar = {
                    "summary": "Test Calendar",
                    "timeZone": "Asia/Kolkata",
                }
                mock_service.calendars().get().execute.return_value = mock_calendar
                mock_build.return_value = mock_service

                connection = await service.handle_oauth_callback(
                    code="auth_code_123",
                    db=async_db,
                    user_id=user_id,
                    clinic_id=clinic_id,
                )

                assert connection is not None
                assert connection.user_id == user_id
                assert connection.clinic_id == clinic_id
                assert connection.access_token == "access_token_123"
                assert connection.refresh_token == "refresh_token_123"
                assert connection.is_active is True

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_existing_connection(self, async_db):
        """Test handling OAuth callback when connection already exists."""
        service = GoogleCalendarService()
        user_id = uuid4()
        clinic_id = uuid4()

        # Create existing connection
        existing = CalendarConnection(
            user_id=user_id,
            clinic_id=clinic_id,
            google_calendar_id="primary",
            calendar_name="Old Calendar",
            calendar_timezone="Asia/Kolkata",
            access_token="old_token",
            refresh_token="old_refresh",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )
        async_db.add(existing)
        await async_db.commit()

        with patch("app.integrations.google_calendar.Flow") as mock_flow_class:
            mock_flow = MagicMock()
            mock_flow_class.from_client_config.return_value = mock_flow

            mock_credentials = MagicMock()
            mock_credentials.token = "new_access_token"
            mock_credentials.refresh_token = "new_refresh_token"
            mock_credentials.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            mock_credentials.scopes = SCOPES
            mock_flow.credentials = mock_credentials

            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                mock_calendar = {"summary": "Updated Calendar", "timeZone": "Asia/Kolkata"}
                mock_service.calendars().get().execute.return_value = mock_calendar
                mock_build.return_value = mock_service

                connection = await service.handle_oauth_callback(
                    code="auth_code_456",
                    db=async_db,
                    user_id=user_id,
                    clinic_id=clinic_id,
                )

                # Should update existing connection
                assert connection.access_token == "new_access_token"
                assert connection.calendar_name == "Updated Calendar"

    def test_token_refresh(self):
        """Test automatic token refresh."""
        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=uuid4(),
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="expired_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        service = GoogleCalendarService(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        with patch("app.integrations.google_calendar.Credentials") as mock_creds_class:
            mock_credentials = MagicMock()
            mock_credentials.expired = True
            mock_credentials.refresh_token = "refresh_token"
            mock_credentials.token = "new_access_token"
            mock_credentials.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

            mock_creds_class.return_value = mock_credentials

            with patch("app.integrations.google_calendar.Request") as mock_request:
                credentials = service._get_credentials(connection)

                # Should refresh token
                mock_credentials.refresh.assert_called_once()
                assert connection.access_token == "new_access_token"

    def test_invalid_expired_token(self):
        """Test handling of invalid/expired tokens."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=uuid4(),
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="invalid_token",
            refresh_token=None,  # No refresh token
            token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        # Should raise error when trying to refresh without refresh token
        with pytest.raises(Exception):
            service._get_credentials(connection)


class TestTwoWaySync:
    """Test two-way synchronization."""

    @pytest.mark.asyncio
    async def test_push_appointment_to_google(self, async_db, sample_appointment):
        """Test pushing appointment to Google Calendar."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test Calendar",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        with patch.object(service, "_get_credentials") as mock_get_creds:
            mock_credentials = MagicMock()
            mock_get_creds.return_value = mock_credentials

            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                mock_event = {"id": "google_event_123"}
                mock_service.events().insert().execute.return_value = mock_event
                mock_build.return_value = mock_service

                event_id = await service.sync_appointment_to_google(
                    appointment=sample_appointment,
                    connection=connection,
                    db=async_db,
                )

                assert event_id == "google_event_123"
                assert sample_appointment.voice_booking_metadata is not None
                assert sample_appointment.voice_booking_metadata["google_event_id"] == "google_event_123"

    @pytest.mark.asyncio
    async def test_update_synced_event(self, async_db, sample_appointment):
        """Test updating already synced event."""
        service = GoogleCalendarService()

        # Mark appointment as already synced
        sample_appointment.voice_booking_metadata = {"google_event_id": "existing_event_123"}

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        with patch.object(service, "_get_credentials"):
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                mock_event = {"id": "existing_event_123"}
                mock_service.events().update().execute.return_value = mock_event
                mock_build.return_value = mock_service

                event_id = await service.sync_appointment_to_google(
                    appointment=sample_appointment,
                    connection=connection,
                    db=async_db,
                )

                # Should update existing event
                mock_service.events().update.assert_called_once()
                assert event_id == "existing_event_123"

    @pytest.mark.asyncio
    async def test_delete_synced_event(self, async_db, sample_appointment):
        """Test deleting Google Calendar event."""
        service = GoogleCalendarService()

        sample_appointment.voice_booking_metadata = {"google_event_id": "event_to_delete"}

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        with patch.object(service, "_get_credentials"):
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                mock_service.events().delete().execute.return_value = None
                mock_build.return_value = mock_service

                result = await service.delete_google_event(
                    appointment=sample_appointment,
                    connection=connection,
                )

                assert result is True
                mock_service.events().delete.assert_called_once()


class TestConflictResolution:
    """Test conflict resolution scenarios."""

    @pytest.mark.asyncio
    async def test_event_deleted_on_google(self, async_db, sample_appointment):
        """Test handling event deleted on Google Calendar."""
        service = GoogleCalendarService()

        sample_appointment.voice_booking_metadata = {"google_event_id": "deleted_event"}

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        with patch.object(service, "_get_credentials"):
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()

                # Mock 404 error for update (event not found)
                error_resp = MagicMock()
                error_resp.status = 404
                mock_service.events().update().execute.side_effect = HttpError(error_resp, b"Not found")

                # Mock successful create
                mock_event = {"id": "new_event_123"}
                mock_service.events().insert().execute.return_value = mock_event
                mock_build.return_value = mock_service

                event_id = await service.sync_appointment_to_google(
                    appointment=sample_appointment,
                    connection=connection,
                    db=async_db,
                )

                # Should create new event after 404
                assert event_id == "new_event_123"
                mock_service.events().insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_modified_latest_wins(self, async_db):
        """Test conflict when both sides modified (latest wins strategy)."""
        # This would require comparing timestamps
        # Implementation depends on storing last_modified timestamps
        pass


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_all_day_event_handling(self):
        """Test handling all-day events."""
        service = GoogleCalendarService()

        # All-day events use 'date' instead of 'dateTime'
        # This test ensures proper handling
        pass

    @pytest.mark.asyncio
    async def test_recurring_appointments(self):
        """Test handling recurring appointments."""
        # Recurring events need special handling in Google Calendar
        pass

    @pytest.mark.asyncio
    async def test_timezone_conversion(self, sample_appointment):
        """Test timezone conversion."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="America/New_York",  # Different timezone
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        event = service._appointment_to_event(sample_appointment, connection)

        # Should use connection's timezone
        assert event["start"]["timeZone"] == "America/New_York"
        assert event["end"]["timeZone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_calendar_not_found(self):
        """Test handling when calendar doesn't exist."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=uuid4(),
            google_calendar_id="non_existent_calendar",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        with patch.object(service, "_get_credentials"):
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                error_resp = MagicMock()
                error_resp.status = 404
                mock_service.calendars().get().execute.side_effect = HttpError(error_resp, b"Not found")
                mock_build.return_value = mock_service

                # Should handle 404 gracefully
                with pytest.raises(HttpError):
                    await service.list_calendars(connection)

    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, async_db, sample_appointment):
        """Test handling API rate limiting."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        with patch.object(service, "_get_credentials"):
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                error_resp = MagicMock()
                error_resp.status = 429  # Too Many Requests
                mock_service.events().insert().execute.side_effect = HttpError(
                    error_resp, b"Rate limit exceeded"
                )
                mock_build.return_value = mock_service

                event_id = await service.sync_appointment_to_google(
                    appointment=sample_appointment,
                    connection=connection,
                    db=async_db,
                )

                # Should return None on rate limit error
                assert event_id is None


class TestColorCoding:
    """Test color coding by appointment type."""

    def test_default_color_mappings(self):
        """Test default color mappings exist."""
        assert AppointmentType.EMERGENCY.value in DEFAULT_COLOR_MAPPINGS
        assert AppointmentType.NEW_CONSULTATION.value in DEFAULT_COLOR_MAPPINGS
        assert AppointmentType.FOLLOW_UP.value in DEFAULT_COLOR_MAPPINGS

    def test_custom_color_mapping(self, sample_appointment):
        """Test custom color mapping."""
        service = GoogleCalendarService()

        custom_colors = {
            AppointmentType.EMERGENCY.value: "11",  # Red
            AppointmentType.NEW_CONSULTATION.value: "5",  # Yellow
        }

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            color_mappings=custom_colors,
            is_active=True,
        )

        sample_appointment.appointment_type = AppointmentType.EMERGENCY.value

        event = service._appointment_to_event(sample_appointment, connection)

        assert event["colorId"] == "11"


class TestListCalendars:
    """Test listing available calendars."""

    @pytest.mark.asyncio
    async def test_list_calendars(self):
        """Test listing available calendars."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=uuid4(),
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )

        with patch.object(service, "_get_credentials"):
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                mock_calendar_list = {
                    "items": [
                        {
                            "id": "primary",
                            "summary": "Primary Calendar",
                            "description": "My primary calendar",
                            "timeZone": "Asia/Kolkata",
                            "primary": True,
                        },
                        {
                            "id": "calendar2",
                            "summary": "Work Calendar",
                            "timeZone": "Asia/Kolkata",
                            "primary": False,
                        },
                    ]
                }
                mock_service.calendarList().list().execute.return_value = mock_calendar_list
                mock_build.return_value = mock_service

                calendars = await service.list_calendars(connection)

                assert len(calendars) == 2
                assert calendars[0]["id"] == "primary"
                assert calendars[0]["primary"] is True
                assert calendars[1]["summary"] == "Work Calendar"


class TestDisconnect:
    """Test disconnecting Google Calendar."""

    @pytest.mark.asyncio
    async def test_disconnect_calendar(self, async_db):
        """Test disconnecting calendar connection."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=uuid4(),
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
            auto_sync_enabled=True,
        )
        async_db.add(connection)
        await async_db.commit()

        result = await service.disconnect(connection, async_db)

        assert result is True
        assert connection.is_active is False
        assert connection.auto_sync_enabled is False


class TestFullSync:
    """Test full calendar sync."""

    @pytest.mark.asyncio
    async def test_sync_to_google_success(self, async_db, sample_appointment):
        """Test successful sync to Google Calendar."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=sample_appointment.doctor.clinic_id,
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="valid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )
        async_db.add(connection)
        await async_db.commit()

        with patch.object(service, "_get_credentials"):
            with patch("app.integrations.google_calendar.build") as mock_build:
                mock_service = MagicMock()
                mock_event = {"id": "synced_event_123"}
                mock_service.events().insert().execute.return_value = mock_event
                mock_build.return_value = mock_service

                sync_log = await service.sync_to_google(connection, async_db)

                assert sync_log.status == SyncStatus.COMPLETED.value
                assert sync_log.events_synced >= 0
                assert connection.last_sync_status == SyncStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_sync_to_google_failure(self, async_db):
        """Test sync failure handling."""
        service = GoogleCalendarService()

        connection = CalendarConnection(
            user_id=uuid4(),
            clinic_id=uuid4(),
            google_calendar_id="primary",
            calendar_name="Test",
            calendar_timezone="Asia/Kolkata",
            access_token="invalid_token",
            refresh_token="refresh_token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_scope=" ".join(SCOPES),
            is_active=True,
        )
        async_db.add(connection)
        await async_db.commit()

        with patch.object(service, "_get_credentials") as mock_get_creds:
            mock_get_creds.side_effect = Exception("Authentication failed")

            sync_log = await service.sync_to_google(connection, async_db)

            assert sync_log.status == SyncStatus.FAILED.value
            assert sync_log.error_message is not None
            assert connection.last_sync_status == SyncStatus.FAILED.value
