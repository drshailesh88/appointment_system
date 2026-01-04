"""
Google Calendar API endpoints.
"""

import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.integrations.google_calendar import get_google_calendar_integration
from app.models.calendar_settings import DoctorCalendarSettings
from app.models.doctor import Doctor
from app.services.calendar_sync import CalendarSyncService

router = APIRouter()

# In-memory state storage (replace with Redis in production)
_oauth_states: dict[str, UUID] = {}


# ==================
# Request/Response Schemas
# ==================

class AuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""
    auth_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""
    code: str
    state: str
    doctor_id: UUID


class CalendarInfo(BaseModel):
    """Calendar information."""
    id: str
    summary: str


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response."""
    success: bool
    calendar_id: str
    calendars: list[CalendarInfo]


class SyncRequest(BaseModel):
    """Manual sync request."""
    doctor_id: UUID
    force: bool = False


class SyncResponse(BaseModel):
    """Sync response."""
    synced: int
    failed: int
    errors: list[str] = []


class StatusResponse(BaseModel):
    """Calendar sync status response."""
    connected: bool
    sync_enabled: bool = False
    last_synced_at: datetime | None = None
    calendar_id: str | None = None
    pending_sync_count: int = 0


class DisconnectRequest(BaseModel):
    """Disconnect request."""
    doctor_id: UUID


class DisconnectResponse(BaseModel):
    """Disconnect response."""
    success: bool
    message: str


class ConflictCheckRequest(BaseModel):
    """Conflict check request."""
    doctor_id: UUID
    start_time: datetime
    end_time: datetime


class ConflictEvent(BaseModel):
    """Conflicting event."""
    event_id: str
    summary: str
    start: str
    end: str


class ConflictCheckResponse(BaseModel):
    """Conflict check response."""
    has_conflict: bool
    conflicts: list[ConflictEvent] = []


# ==================
# API Endpoints
# ==================

@router.get("/auth-url", response_model=AuthUrlResponse)
async def get_auth_url(
    doctor_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> AuthUrlResponse:
    """
    Get OAuth authorization URL for Google Calendar.

    The user should visit this URL to grant calendar access.
    """
    gcal = get_google_calendar_integration()

    if not gcal.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Calendar integration not configured",
        )

    # Verify doctor exists
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = doctor_id

    # Get authorization URL
    auth_url = gcal.get_authorization_url(state)

    return AuthUrlResponse(auth_url=auth_url, state=state)


@router.post("/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    request: OAuthCallbackRequest,
    db: DbSession,
) -> OAuthCallbackResponse:
    """
    Handle OAuth callback from Google.

    Exchanges authorization code for tokens and stores them.
    """
    gcal = get_google_calendar_integration()

    # Verify state token
    if request.state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state token",
        )

    doctor_id = _oauth_states.pop(request.state)

    if doctor_id != request.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor ID mismatch",
        )

    # Exchange code for tokens
    try:
        tokens = gcal.exchange_code_for_token(request.code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code: {str(e)}",
        )

    # Encrypt refresh token
    encrypted_refresh_token = gcal.encrypt_token(tokens["refresh_token"])

    # Get list of available calendars
    calendars = gcal.list_calendars(encrypted_refresh_token)

    # Use primary calendar by default
    primary_calendar_id = "primary"

    # Check if settings already exist
    result = await db.execute(
        select(DoctorCalendarSettings).where(
            DoctorCalendarSettings.doctor_id == doctor_id
        )
    )
    settings = result.scalar_one_or_none()

    if settings:
        # Update existing settings
        settings.google_calendar_id = primary_calendar_id
        settings.google_refresh_token = encrypted_refresh_token
        settings.sync_enabled = True
        settings.last_sync_error = None
    else:
        # Create new settings
        settings = DoctorCalendarSettings(
            doctor_id=doctor_id,
            google_calendar_id=primary_calendar_id,
            google_refresh_token=encrypted_refresh_token,
            sync_enabled=True,
        )
        db.add(settings)

    await db.commit()

    return OAuthCallbackResponse(
        success=True,
        calendar_id=primary_calendar_id,
        calendars=[CalendarInfo(**cal) for cal in calendars],
    )


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SyncResponse:
    """
    Trigger manual sync of appointments to Google Calendar.

    By default, only syncs appointments modified since last sync.
    Use force=true to sync all future appointments.
    """
    service = CalendarSyncService(db)

    # Determine since timestamp
    since = None
    if not request.force:
        settings = await service.get_doctor_calendar_settings(request.doctor_id)
        if settings and settings.last_synced_at:
            since = settings.last_synced_at

    # Sync appointments
    try:
        stats = await service.sync_multiple_appointments(
            doctor_id=request.doctor_id,
            since=since,
        )
        return SyncResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get("/status", response_model=StatusResponse)
async def get_sync_status(
    doctor_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> StatusResponse:
    """
    Get calendar sync status for a doctor.
    """
    service = CalendarSyncService(db)
    settings = await service.get_doctor_calendar_settings(doctor_id)

    if not settings:
        return StatusResponse(connected=False)

    # Count pending syncs
    from app.models.appointment import Appointment
    from sqlalchemy import func

    pending_count_query = select(func.count()).where(
        Appointment.doctor_id == doctor_id,
        Appointment.scheduled_start >= datetime.now(),
        Appointment.calendar_sync_status == "pending",
    )
    result = await db.execute(pending_count_query)
    pending_count = result.scalar_one()

    return StatusResponse(
        connected=True,
        sync_enabled=settings.sync_enabled,
        last_synced_at=settings.last_synced_at,
        calendar_id=settings.google_calendar_id,
        pending_sync_count=pending_count,
    )


@router.delete("/disconnect", response_model=DisconnectResponse)
async def disconnect_calendar(
    request: DisconnectRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> DisconnectResponse:
    """
    Disconnect Google Calendar and delete all synced events.
    """
    service = CalendarSyncService(db)

    success = await service.disconnect_calendar(request.doctor_id)

    if success:
        return DisconnectResponse(
            success=True,
            message="Calendar disconnected successfully",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect calendar",
        )


@router.post("/conflicts", response_model=ConflictCheckResponse)
async def check_conflicts(
    request: ConflictCheckRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ConflictCheckResponse:
    """
    Check for calendar conflicts at a specific time.
    """
    service = CalendarSyncService(db)

    conflicts = await service.check_conflicts(
        doctor_id=request.doctor_id,
        start_time=request.start_time,
        end_time=request.end_time,
    )

    return ConflictCheckResponse(
        has_conflict=len(conflicts) > 0,
        conflicts=[ConflictEvent(**c) for c in conflicts],
    )
