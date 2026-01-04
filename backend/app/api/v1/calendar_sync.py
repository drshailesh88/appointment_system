"""
Calendar Sync API endpoints for Google Calendar integration.

Provides endpoints for:
- OAuth2 authentication flow
- Calendar connection management
- Manual sync triggers
- Sync status and logs
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.integrations.google_calendar import (
    GoogleCalendarService,
    get_google_calendar_service,
)
from app.models.calendar_sync import (
    CalendarConnection,
    CalendarSyncLog,
    ConflictResolution,
    SyncDirection,
)
from app.models.user import User

router = APIRouter()


# Request/Response Models


class AuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""

    auth_url: str
    state: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str
    state: Optional[str] = None


class CalendarConnectionResponse(BaseModel):
    """Calendar connection response."""

    id: str
    user_id: str
    clinic_id: str
    google_calendar_id: str
    calendar_name: str
    calendar_timezone: str
    sync_direction: str
    conflict_resolution: str
    auto_sync_enabled: bool
    sync_interval_minutes: int
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CalendarInfo(BaseModel):
    """Calendar information."""

    id: str
    summary: str
    description: str
    timezone: str
    primary: bool


class SyncSettingsUpdate(BaseModel):
    """Update sync settings."""

    google_calendar_id: Optional[str] = None
    sync_direction: Optional[SyncDirection] = None
    conflict_resolution: Optional[ConflictResolution] = None
    auto_sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    color_mappings: Optional[dict[str, str]] = None


class SyncLogResponse(BaseModel):
    """Sync log response."""

    id: str
    connection_id: str
    sync_direction: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    events_synced: int
    events_created: int
    events_updated: int
    events_deleted: int
    conflicts_found: int
    conflicts_resolved: int
    error_message: Optional[str] = None
    duration_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class SyncStatusResponse(BaseModel):
    """Sync status response."""

    connected: bool
    connection: Optional[CalendarConnectionResponse] = None
    last_sync: Optional[SyncLogResponse] = None
    recent_logs: list[SyncLogResponse] = []


# Endpoints


@router.get("/auth-url", response_model=AuthUrlResponse)
async def get_auth_url(
    calendar_service: GoogleCalendarService = Depends(get_google_calendar_service),
    current_user: User = Depends(get_current_user),
) -> AuthUrlResponse:
    """
    Get OAuth2 authorization URL.

    Redirects user to Google for calendar access permission.
    """
    # Use user ID as state for CSRF protection
    state = str(current_user.id)
    auth_url = calendar_service.get_auth_url(state=state)

    return AuthUrlResponse(auth_url=auth_url, state=state)


@router.post("/callback", response_model=CalendarConnectionResponse)
async def oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
    calendar_service: GoogleCalendarService = Depends(get_google_calendar_service),
    current_user: User = Depends(get_current_user),
) -> CalendarConnectionResponse:
    """
    Handle OAuth2 callback.

    Exchanges authorization code for access tokens and creates calendar connection.
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be associated with a clinic",
        )

    try:
        connection = await calendar_service.handle_oauth_callback(
            code=request.code,
            db=db,
            user_id=current_user.id,
            clinic_id=current_user.clinic_id,
        )

        return CalendarConnectionResponse.model_validate(connection)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}",
        )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncStatusResponse:
    """
    Get calendar sync status.

    Returns current connection status and recent sync logs.
    """
    # Get active connection
    result = await db.execute(
        select(CalendarConnection)
        .where(CalendarConnection.user_id == current_user.id)
        .where(CalendarConnection.is_active == True)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return SyncStatusResponse(connected=False, recent_logs=[])

    # Get recent sync logs
    logs_result = await db.execute(
        select(CalendarSyncLog)
        .where(CalendarSyncLog.connection_id == connection.id)
        .order_by(CalendarSyncLog.started_at.desc())
        .limit(10)
    )
    logs = logs_result.scalars().all()

    last_sync = logs[0] if logs else None

    return SyncStatusResponse(
        connected=True,
        connection=CalendarConnectionResponse.model_validate(connection),
        last_sync=SyncLogResponse.model_validate(last_sync) if last_sync else None,
        recent_logs=[SyncLogResponse.model_validate(log) for log in logs],
    )


@router.post("/sync", response_model=SyncLogResponse)
async def trigger_sync(
    db: AsyncSession = Depends(get_db),
    calendar_service: GoogleCalendarService = Depends(get_google_calendar_service),
    current_user: User = Depends(get_current_user),
) -> SyncLogResponse:
    """
    Trigger manual sync to Google Calendar.

    Syncs recent and upcoming appointments to Google Calendar.
    """
    # Get active connection
    result = await db.execute(
        select(CalendarConnection)
        .where(CalendarConnection.user_id == current_user.id)
        .where(CalendarConnection.is_active == True)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active calendar connection found",
        )

    # Trigger sync
    sync_log = await calendar_service.sync_to_google(connection, db)

    return SyncLogResponse.model_validate(sync_log)


@router.get("/calendars", response_model=list[CalendarInfo])
async def list_calendars(
    db: AsyncSession = Depends(get_db),
    calendar_service: GoogleCalendarService = Depends(get_google_calendar_service),
    current_user: User = Depends(get_current_user),
) -> list[CalendarInfo]:
    """
    List available Google Calendars.

    Returns all calendars accessible by the connected account.
    """
    # Get active connection
    result = await db.execute(
        select(CalendarConnection)
        .where(CalendarConnection.user_id == current_user.id)
        .where(CalendarConnection.is_active == True)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active calendar connection found",
        )

    try:
        calendars = await calendar_service.list_calendars(connection)
        return [CalendarInfo(**cal) for cal in calendars]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list calendars: {str(e)}",
        )


@router.put("/settings", response_model=CalendarConnectionResponse)
async def update_sync_settings(
    settings: SyncSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarConnectionResponse:
    """
    Update sync settings.

    Allows changing sync direction, calendar selection, and other settings.
    """
    # Get active connection
    result = await db.execute(
        select(CalendarConnection)
        .where(CalendarConnection.user_id == current_user.id)
        .where(CalendarConnection.is_active == True)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active calendar connection found",
        )

    # Update settings
    if settings.google_calendar_id is not None:
        connection.google_calendar_id = settings.google_calendar_id

    if settings.sync_direction is not None:
        connection.sync_direction = settings.sync_direction.value

    if settings.conflict_resolution is not None:
        connection.conflict_resolution = settings.conflict_resolution.value

    if settings.auto_sync_enabled is not None:
        connection.auto_sync_enabled = settings.auto_sync_enabled

    if settings.sync_interval_minutes is not None:
        connection.sync_interval_minutes = settings.sync_interval_minutes

    if settings.color_mappings is not None:
        connection.color_mappings = settings.color_mappings

    await db.commit()
    await db.refresh(connection)

    return CalendarConnectionResponse.model_validate(connection)


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_calendar(
    db: AsyncSession = Depends(get_db),
    calendar_service: GoogleCalendarService = Depends(get_google_calendar_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Disconnect Google Calendar.

    Deactivates the calendar connection without deleting sync history.
    """
    # Get active connection
    result = await db.execute(
        select(CalendarConnection)
        .where(CalendarConnection.user_id == current_user.id)
        .where(CalendarConnection.is_active == True)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active calendar connection found",
        )

    await calendar_service.disconnect(connection, db)


@router.get("/logs", response_model=list[SyncLogResponse])
async def get_sync_logs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SyncLogResponse]:
    """
    Get sync logs.

    Returns recent sync operation logs for debugging.
    """
    # Get active connection
    result = await db.execute(
        select(CalendarConnection)
        .where(CalendarConnection.user_id == current_user.id)
        .where(CalendarConnection.is_active == True)
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return []

    # Get logs
    logs_result = await db.execute(
        select(CalendarSyncLog)
        .where(CalendarSyncLog.connection_id == connection.id)
        .order_by(CalendarSyncLog.started_at.desc())
        .limit(limit)
    )
    logs = logs_result.scalars().all()

    return [SyncLogResponse.model_validate(log) for log in logs]
