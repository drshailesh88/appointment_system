"""
Calendar sync models for Google Calendar integration.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.types import JSONB

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.clinic import Clinic


class SyncDirection(str, Enum):
    """Calendar sync direction."""

    ONE_WAY_TO_GOOGLE = "one_way_to_google"
    ONE_WAY_FROM_GOOGLE = "one_way_from_google"
    TWO_WAY = "two_way"


class SyncStatus(str, Enum):
    """Sync status types."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ConflictResolution(str, Enum):
    """How to resolve sync conflicts."""

    GOOGLE_WINS = "google_wins"
    APP_WINS = "app_wins"
    LATEST_WINS = "latest_wins"
    MANUAL = "manual"


class CalendarConnection(BaseModel):
    """
    Google Calendar connection for a user.

    Stores OAuth credentials and sync settings for connecting
    a doctor's/clinic's appointments to Google Calendar.

    Attributes:
        user_id: User who connected the calendar
        clinic_id: Associated clinic
        google_calendar_id: Google Calendar ID (e.g., "primary" or specific calendar ID)
        access_token: OAuth2 access token (encrypted in production)
        refresh_token: OAuth2 refresh token (encrypted in production)
        token_expires_at: When the access token expires
        calendar_name: Display name of the calendar
        calendar_timezone: Calendar timezone (e.g., "Asia/Kolkata")
        sync_direction: One-way or two-way sync
        conflict_resolution: How to handle conflicts
        auto_sync_enabled: Enable automatic background sync
        sync_interval_minutes: How often to sync (if auto-sync enabled)
        last_sync_at: Last successful sync timestamp
        is_active: Connection active status
    """

    __tablename__ = "calendar_connections"

    # Relations
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )

    # Google Calendar Info
    google_calendar_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="primary",
    )
    calendar_name: Mapped[str] = mapped_column(String(255), nullable=False)
    calendar_timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Asia/Kolkata",
    )

    # OAuth2 Credentials (should be encrypted in production)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    token_scope: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sync Settings
    sync_direction: Mapped[str] = mapped_column(
        String(30),
        default=SyncDirection.TWO_WAY.value,
        nullable=False,
    )
    conflict_resolution: Mapped[str] = mapped_column(
        String(20),
        default=ConflictResolution.LATEST_WINS.value,
        nullable=False,
    )
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)

    # Color coding by appointment type (JSON mapping)
    # Example: {"follow_up": "1", "new_consultation": "2"}
    color_mappings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Sync State
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Google Calendar sync token for incremental sync",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    clinic: Mapped["Clinic"] = relationship("Clinic")
    sync_logs: Mapped[list["CalendarSyncLog"]] = relationship(
        "CalendarSyncLog",
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CalendarConnection {self.user_id} -> {self.google_calendar_id}>"


class CalendarSyncLog(BaseModel):
    """
    Log of calendar sync operations.

    Tracks each sync operation for debugging and conflict resolution.

    Attributes:
        connection_id: Associated calendar connection
        sync_direction: Direction of this sync
        status: Sync operation status
        started_at: When sync started
        completed_at: When sync completed
        events_synced: Number of events synced
        events_created: Number of events created
        events_updated: Number of events updated
        events_deleted: Number of events deleted
        conflicts_found: Number of conflicts detected
        conflicts_resolved: Number of conflicts auto-resolved
        error_message: Error details if failed
        sync_details: Additional sync metadata (JSON)
    """

    __tablename__ = "calendar_sync_logs"

    # Relations
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calendar_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sync Info
    sync_direction: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=SyncStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Statistics
    events_synced: Mapped[int] = mapped_column(Integer, default=0)
    events_created: Mapped[int] = mapped_column(Integer, default=0)
    events_updated: Mapped[int] = mapped_column(Integer, default=0)
    events_deleted: Mapped[int] = mapped_column(Integer, default=0)
    conflicts_found: Mapped[int] = mapped_column(Integer, default=0)
    conflicts_resolved: Mapped[int] = mapped_column(Integer, default=0)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Detailed sync info (appointments synced, conflicts, etc.)
    sync_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    connection: Mapped["CalendarConnection"] = relationship(
        "CalendarConnection",
        back_populates="sync_logs",
    )

    @property
    def duration_seconds(self) -> int | None:
        """Calculate sync duration in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds())
        return None

    def __repr__(self) -> str:
        return f"<CalendarSyncLog {self.id} ({self.status})>"
