"""
Google Calendar Integration Service.

Provides two-way sync between DocAssist appointments and Google Calendar.

Features:
- OAuth2 authentication flow
- Create/update/delete calendar events
- Two-way sync with conflict resolution
- Support for multiple calendars per doctor
- Color coding by appointment type
- Incremental sync using sync tokens

References:
- Google Calendar API: https://developers.google.com/calendar/api/v3/reference
- OAuth2: https://developers.google.com/identity/protocols/oauth2
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.calendar_sync import (
    CalendarConnection,
    CalendarSyncLog,
    ConflictResolution,
    SyncDirection,
    SyncStatus,
)

logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# Color IDs for appointment types (Google Calendar has 11 colors: 1-11)
DEFAULT_COLOR_MAPPINGS = {
    AppointmentType.NEW_CONSULTATION.value: "1",  # Lavender
    AppointmentType.FOLLOW_UP.value: "2",  # Sage
    AppointmentType.PROCEDURE.value: "3",  # Grape
    AppointmentType.EMERGENCY.value: "11",  # Red
    AppointmentType.TELECONSULTATION.value: "6",  # Orange
}


class GoogleCalendarService:
    """
    Google Calendar integration service.

    Handles OAuth2 authentication and calendar event synchronization.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        """
        Initialize Google Calendar service.

        Args:
            client_id: Google OAuth2 client ID
            client_secret: Google OAuth2 client secret
            redirect_uri: OAuth2 redirect URI
        """
        self.client_id = client_id or getattr(
            settings, "google_client_id", "YOUR_CLIENT_ID"
        )
        self.client_secret = client_secret or getattr(
            settings, "google_client_secret", "YOUR_CLIENT_SECRET"
        )
        self.redirect_uri = redirect_uri or getattr(
            settings,
            "google_redirect_uri",
            f"{getattr(settings, 'api_base_url', 'http://localhost:8000')}/api/v1/calendar/callback",
        )

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Get OAuth2 authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for user to visit
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )

        return auth_url

    async def handle_oauth_callback(
        self,
        code: str,
        db: AsyncSession,
        user_id: UUID,
        clinic_id: UUID,
    ) -> CalendarConnection:
        """
        Handle OAuth2 callback and create calendar connection.

        Args:
            code: Authorization code from Google
            db: Database session
            user_id: User connecting the calendar
            clinic_id: Associated clinic

        Returns:
            Created CalendarConnection

        Raises:
            Exception: If OAuth flow fails
        """
        # Exchange code for tokens
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get calendar info
        service = build("calendar", "v3", credentials=credentials)
        calendar = service.calendars().get(calendarId="primary").execute()

        # Check if connection already exists
        result = await db.execute(
            select(CalendarConnection)
            .where(CalendarConnection.user_id == user_id)
            .where(CalendarConnection.clinic_id == clinic_id)
            .where(CalendarConnection.is_active == True)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing connection
            existing.access_token = credentials.token
            existing.refresh_token = credentials.refresh_token or existing.refresh_token
            existing.token_expires_at = credentials.expiry or datetime.now(timezone.utc) + timedelta(hours=1)
            existing.token_scope = " ".join(credentials.scopes or SCOPES)
            existing.calendar_name = calendar.get("summary", "Primary Calendar")
            existing.calendar_timezone = calendar.get("timeZone", "Asia/Kolkata")
            existing.is_active = True
            connection = existing
        else:
            # Create new connection
            connection = CalendarConnection(
                user_id=user_id,
                clinic_id=clinic_id,
                google_calendar_id="primary",
                calendar_name=calendar.get("summary", "Primary Calendar"),
                calendar_timezone=calendar.get("timeZone", "Asia/Kolkata"),
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expires_at=credentials.expiry or datetime.now(timezone.utc) + timedelta(hours=1),
                token_scope=" ".join(credentials.scopes or SCOPES),
                sync_direction=SyncDirection.TWO_WAY.value,
                conflict_resolution=ConflictResolution.LATEST_WINS.value,
                auto_sync_enabled=True,
                sync_interval_minutes=15,
                color_mappings=DEFAULT_COLOR_MAPPINGS,
                is_active=True,
            )
            db.add(connection)

        await db.commit()
        await db.refresh(connection)
        return connection

    def _get_credentials(self, connection: CalendarConnection) -> Credentials:
        """
        Get Google credentials from connection.

        Refreshes token if expired.

        Args:
            connection: CalendarConnection with OAuth tokens

        Returns:
            Valid Google Credentials
        """
        credentials = Credentials(
            token=connection.access_token,
            refresh_token=connection.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=connection.token_scope.split() if connection.token_scope else SCOPES,
        )

        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            # Update connection with new tokens (caller should commit)
            connection.access_token = credentials.token
            connection.token_expires_at = credentials.expiry or datetime.now(timezone.utc) + timedelta(hours=1)

        return credentials

    async def list_calendars(self, connection: CalendarConnection) -> list[dict[str, Any]]:
        """
        List available calendars for the connected account.

        Args:
            connection: CalendarConnection

        Returns:
            List of calendar info dicts
        """
        try:
            credentials = self._get_credentials(connection)
            service = build("calendar", "v3", credentials=credentials)

            calendar_list = service.calendarList().list().execute()
            calendars = []

            for calendar in calendar_list.get("items", []):
                calendars.append({
                    "id": calendar["id"],
                    "summary": calendar.get("summary", ""),
                    "description": calendar.get("description", ""),
                    "timezone": calendar.get("timeZone", ""),
                    "primary": calendar.get("primary", False),
                })

            return calendars

        except HttpError as e:
            logger.error(f"Error listing calendars: {e}")
            raise

    async def sync_appointment_to_google(
        self,
        appointment: Appointment,
        connection: CalendarConnection,
        db: AsyncSession,
    ) -> Optional[str]:
        """
        Sync a single appointment to Google Calendar.

        Args:
            appointment: Appointment to sync
            connection: CalendarConnection
            db: Database session

        Returns:
            Google Calendar event ID, or None if failed
        """
        try:
            credentials = self._get_credentials(connection)
            service = build("calendar", "v3", credentials=credentials)

            # Build event
            event = self._appointment_to_event(appointment, connection)

            # Check if event already exists (stored in appointment metadata)
            google_event_id = None
            if appointment.voice_booking_metadata:
                google_event_id = appointment.voice_booking_metadata.get("google_event_id")

            if google_event_id:
                # Update existing event
                try:
                    updated_event = (
                        service.events()
                        .update(
                            calendarId=connection.google_calendar_id,
                            eventId=google_event_id,
                            body=event,
                        )
                        .execute()
                    )
                    logger.info(f"Updated Google Calendar event: {google_event_id}")
                    return updated_event["id"]
                except HttpError as e:
                    if e.resp.status == 404:
                        # Event was deleted, create new one
                        google_event_id = None
                    else:
                        raise

            if not google_event_id:
                # Create new event
                created_event = (
                    service.events()
                    .insert(
                        calendarId=connection.google_calendar_id,
                        body=event,
                    )
                    .execute()
                )
                google_event_id = created_event["id"]

                # Store event ID in appointment metadata
                if not appointment.voice_booking_metadata:
                    appointment.voice_booking_metadata = {}
                appointment.voice_booking_metadata["google_event_id"] = google_event_id
                await db.commit()

                logger.info(f"Created Google Calendar event: {google_event_id}")
                return google_event_id

        except HttpError as e:
            logger.error(f"Error syncing appointment to Google: {e}")
            return None

    async def delete_google_event(
        self,
        appointment: Appointment,
        connection: CalendarConnection,
    ) -> bool:
        """
        Delete a Google Calendar event.

        Args:
            appointment: Appointment with Google event ID
            connection: CalendarConnection

        Returns:
            True if deleted successfully
        """
        try:
            if not appointment.voice_booking_metadata:
                return False

            google_event_id = appointment.voice_booking_metadata.get("google_event_id")
            if not google_event_id:
                return False

            credentials = self._get_credentials(connection)
            service = build("calendar", "v3", credentials=credentials)

            service.events().delete(
                calendarId=connection.google_calendar_id,
                eventId=google_event_id,
            ).execute()

            logger.info(f"Deleted Google Calendar event: {google_event_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted
                return True
            logger.error(f"Error deleting Google event: {e}")
            return False

    async def sync_to_google(
        self,
        connection: CalendarConnection,
        db: AsyncSession,
    ) -> CalendarSyncLog:
        """
        Sync appointments to Google Calendar.

        Args:
            connection: CalendarConnection
            db: Database session

        Returns:
            CalendarSyncLog with sync results
        """
        sync_log = CalendarSyncLog(
            connection_id=connection.id,
            sync_direction=SyncDirection.ONE_WAY_TO_GOOGLE.value,
            status=SyncStatus.IN_PROGRESS.value,
            started_at=datetime.now(timezone.utc),
        )
        db.add(sync_log)
        await db.commit()

        try:
            # Get appointments to sync (recent and upcoming)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            result = await db.execute(
                select(Appointment)
                .join(Appointment.doctor)
                .where(Appointment.doctor.has(clinic_id=connection.clinic_id))
                .where(Appointment.scheduled_start >= cutoff_date)
                .where(Appointment.status.in_([
                    AppointmentStatus.SCHEDULED.value,
                    AppointmentStatus.CONFIRMED.value,
                    AppointmentStatus.CHECKED_IN.value,
                    AppointmentStatus.IN_PROGRESS.value,
                ]))
            )
            appointments = result.scalars().all()

            events_created = 0
            events_updated = 0

            for appointment in appointments:
                event_id = await self.sync_appointment_to_google(
                    appointment, connection, db
                )
                if event_id:
                    # Check if it was an update or create
                    if appointment.voice_booking_metadata and appointment.voice_booking_metadata.get("google_event_id"):
                        events_updated += 1
                    else:
                        events_created += 1

            sync_log.events_synced = len(appointments)
            sync_log.events_created = events_created
            sync_log.events_updated = events_updated
            sync_log.status = SyncStatus.COMPLETED.value
            sync_log.completed_at = datetime.now(timezone.utc)

            connection.last_sync_at = datetime.now(timezone.utc)
            connection.last_sync_status = SyncStatus.COMPLETED.value

        except Exception as e:
            logger.error(f"Sync to Google failed: {e}")
            sync_log.status = SyncStatus.FAILED.value
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.now(timezone.utc)

            connection.last_sync_status = SyncStatus.FAILED.value
            connection.last_sync_error = str(e)

        await db.commit()
        await db.refresh(sync_log)
        return sync_log

    def _appointment_to_event(
        self,
        appointment: Appointment,
        connection: CalendarConnection,
    ) -> dict[str, Any]:
        """
        Convert appointment to Google Calendar event.

        Args:
            appointment: Appointment to convert
            connection: CalendarConnection for settings

        Returns:
            Google Calendar event dict
        """
        # Get patient and doctor info
        patient_name = appointment.patient.name if appointment.patient else "Patient"
        doctor_name = appointment.doctor.name if appointment.doctor else "Doctor"

        # Build summary
        summary = f"{patient_name} - {appointment.appointment_type.replace('_', ' ').title()}"

        # Build description
        description_parts = [
            f"Doctor: Dr. {doctor_name}",
            f"Patient: {patient_name}",
            f"Type: {appointment.appointment_type.replace('_', ' ').title()}",
        ]
        if appointment.chief_complaint:
            description_parts.append(f"Chief Complaint: {appointment.chief_complaint}")
        if appointment.notes:
            description_parts.append(f"Notes: {appointment.notes}")

        description = "\n".join(description_parts)

        # Get color
        color_mappings = connection.color_mappings or DEFAULT_COLOR_MAPPINGS
        color_id = color_mappings.get(appointment.appointment_type, "1")

        # Build event
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": appointment.scheduled_start.isoformat(),
                "timeZone": connection.calendar_timezone,
            },
            "end": {
                "dateTime": appointment.scheduled_end.isoformat(),
                "timeZone": connection.calendar_timezone,
            },
            "colorId": color_id,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30},
                    {"method": "email", "minutes": 60},
                ],
            },
        }

        return event

    async def disconnect(
        self,
        connection: CalendarConnection,
        db: AsyncSession,
    ) -> bool:
        """
        Disconnect Google Calendar.

        Args:
            connection: CalendarConnection to disconnect
            db: Database session

        Returns:
            True if disconnected successfully
        """
        connection.is_active = False
        connection.auto_sync_enabled = False
        await db.commit()
        return True


# Singleton
_google_calendar_service: Optional[GoogleCalendarService] = None


def get_google_calendar_service() -> GoogleCalendarService:
    """Get Google Calendar service singleton."""
    global _google_calendar_service
    if _google_calendar_service is None:
        _google_calendar_service = GoogleCalendarService()
    return _google_calendar_service
