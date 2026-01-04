"""
Google Calendar Integration Module.

Handles OAuth 2.0 flow, token management, and Google Calendar API operations.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleCalendarIntegration:
    """
    Google Calendar Integration service.

    Provides:
    - OAuth 2.0 authorization flow
    - Token encryption/decryption
    - Token refresh
    - Calendar event CRUD operations
    - Conflict detection
    """

    # OAuth scopes required
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize Google Calendar integration.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth redirect URI
            encryption_key: Fernet encryption key for tokens
        """
        self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/api/v1/calendar/callback",
        )

        # Initialize encryption
        encryption_key_bytes = (encryption_key or os.getenv("CALENDAR_ENCRYPTION_KEY", "")).encode()
        if not encryption_key_bytes:
            # Generate a key if none provided (for development only)
            encryption_key_bytes = Fernet.generate_key()
            logger.warning("Using auto-generated encryption key. Set CALENDAR_ENCRYPTION_KEY in production!")

        self.cipher = Fernet(encryption_key_bytes)

        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth credentials not configured. Calendar sync disabled.")

    def is_configured(self) -> bool:
        """Check if Google Calendar integration is properly configured."""
        return bool(self.client_id and self.client_secret)

    # ==================
    # OAuth Flow
    # ==================

    def get_authorization_url(self, state: str) -> str:
        """
        Get OAuth authorization URL.

        Args:
            state: Random state token for CSRF protection

        Returns:
            Authorization URL for user to visit
        """
        if not self.is_configured():
            raise ValueError("Google OAuth not configured")

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
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",  # Force consent to get refresh token
        )

        return auth_url

    def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict with 'access_token', 'refresh_token', 'expires_in'
        """
        if not self.is_configured():
            raise ValueError("Google OAuth not configured")

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
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_in": credentials.expiry.timestamp() if credentials.expiry else None,
        }

    # ==================
    # Token Management
    # ==================

    def encrypt_token(self, token: str) -> str:
        """Encrypt refresh token for storage."""
        return self.cipher.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt refresh token from storage."""
        return self.cipher.decrypt(encrypted_token.encode()).decode()

    def get_credentials(self, refresh_token: str) -> Credentials:
        """
        Get Google credentials from refresh token.

        Args:
            refresh_token: Encrypted refresh token from database

        Returns:
            Google OAuth2 Credentials object
        """
        decrypted_token = self.decrypt_token(refresh_token)

        credentials = Credentials(
            token=None,
            refresh_token=decrypted_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )

        # Refresh the access token
        credentials.refresh(Request())

        return credentials

    # ==================
    # Calendar Operations
    # ==================

    def list_calendars(self, refresh_token: str) -> list[dict[str, str]]:
        """
        List available calendars for the user.

        Args:
            refresh_token: Encrypted refresh token

        Returns:
            List of dicts with 'id' and 'summary' (name) of calendars
        """
        try:
            credentials = self.get_credentials(refresh_token)
            service = build("calendar", "v3", credentials=credentials)

            calendars_result = service.calendarList().list().execute()
            calendars = calendars_result.get("items", [])

            return [
                {"id": cal["id"], "summary": cal.get("summary", "Unnamed Calendar")}
                for cal in calendars
            ]

        except HttpError as e:
            logger.error(f"Error listing calendars: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing calendars: {e}")
            raise

    def create_event(
        self,
        refresh_token: str,
        calendar_id: str,
        summary: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        visibility: str = "private",
        reminders: Optional[dict] = None,
    ) -> str:
        """
        Create a calendar event.

        Args:
            refresh_token: Encrypted refresh token
            calendar_id: Google Calendar ID
            summary: Event title
            description: Event description
            start_time: Event start time (timezone-aware)
            end_time: Event end time (timezone-aware)
            location: Event location
            visibility: Event visibility (default, public, private)
            reminders: Custom reminders config

        Returns:
            Google Calendar event ID
        """
        try:
            credentials = self.get_credentials(refresh_token)
            service = build("calendar", "v3", credentials=credentials)

            event = {
                "summary": summary,
                "description": description,
                "location": location,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": str(start_time.tzinfo) if start_time.tzinfo else "UTC",
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": str(end_time.tzinfo) if end_time.tzinfo else "UTC",
                },
                "visibility": visibility,
            }

            # Add reminders if specified
            if reminders:
                event["reminders"] = reminders
            else:
                # Default: 30 minutes before
                event["reminders"] = {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 30},
                    ],
                }

            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event,
            ).execute()

            logger.info(f"Created calendar event: {created_event['id']}")
            return created_event["id"]

        except HttpError as e:
            logger.error(f"Error creating event: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating event: {e}")
            raise

    def update_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event_id: str,
        summary: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        location: Optional[str] = None,
        visibility: str = "private",
    ) -> None:
        """
        Update an existing calendar event.

        Args:
            refresh_token: Encrypted refresh token
            calendar_id: Google Calendar ID
            event_id: Google Calendar event ID
            summary: Event title
            description: Event description
            start_time: Event start time (timezone-aware)
            end_time: Event end time (timezone-aware)
            location: Event location
            visibility: Event visibility
        """
        try:
            credentials = self.get_credentials(refresh_token)
            service = build("calendar", "v3", credentials=credentials)

            event = {
                "summary": summary,
                "description": description,
                "location": location,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": str(start_time.tzinfo) if start_time.tzinfo else "UTC",
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": str(end_time.tzinfo) if end_time.tzinfo else "UTC",
                },
                "visibility": visibility,
            }

            service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
            ).execute()

            logger.info(f"Updated calendar event: {event_id}")

        except HttpError as e:
            logger.error(f"Error updating event: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating event: {e}")
            raise

    def delete_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event_id: str,
    ) -> None:
        """
        Delete a calendar event.

        Args:
            refresh_token: Encrypted refresh token
            calendar_id: Google Calendar ID
            event_id: Google Calendar event ID
        """
        try:
            credentials = self.get_credentials(refresh_token)
            service = build("calendar", "v3", credentials=credentials)

            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
            ).execute()

            logger.info(f"Deleted calendar event: {event_id}")

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Event {event_id} not found, skipping deletion")
            else:
                logger.error(f"Error deleting event: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error deleting event: {e}")
            raise

    def check_conflicts(
        self,
        refresh_token: str,
        calendar_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """
        Check for conflicting events in the calendar.

        Args:
            refresh_token: Encrypted refresh token
            calendar_id: Google Calendar ID
            start_time: Start time to check
            end_time: End time to check

        Returns:
            List of conflicting events with 'id', 'summary', 'start', 'end'
        """
        try:
            credentials = self.get_credentials(refresh_token)
            service = build("calendar", "v3", credentials=credentials)

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])

            conflicts = []
            for event in events:
                # Skip all-day events and declined events
                if event.get("start").get("date"):
                    continue
                if event.get("status") == "cancelled":
                    continue

                conflicts.append({
                    "event_id": event["id"],
                    "summary": event.get("summary", "(No title)"),
                    "start": event["start"]["dateTime"],
                    "end": event["end"]["dateTime"],
                })

            return conflicts

        except HttpError as e:
            logger.error(f"Error checking conflicts: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error checking conflicts: {e}")
            raise


# Singleton instance
_google_calendar_integration: Optional[GoogleCalendarIntegration] = None


def get_google_calendar_integration() -> GoogleCalendarIntegration:
    """Get singleton Google Calendar integration instance."""
    global _google_calendar_integration
    if _google_calendar_integration is None:
        _google_calendar_integration = GoogleCalendarIntegration()
    return _google_calendar_integration
