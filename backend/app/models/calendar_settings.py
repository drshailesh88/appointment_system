"""
Doctor Calendar Settings model for Google Calendar integration.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.doctor import Doctor


class DoctorCalendarSettings(BaseModel):
    """
    Doctor Calendar Settings for Google Calendar sync.

    Attributes:
        doctor_id: Doctor associated with these settings
        google_calendar_id: Google Calendar ID to sync with
        google_refresh_token: Encrypted OAuth refresh token
        sync_enabled: Whether calendar sync is enabled
        last_synced_at: Last successful sync timestamp
        sync_interval_minutes: How often to sync (in minutes)
        event_visibility: Calendar event visibility (private, public, default)
        event_reminders: Custom event reminders configuration
        total_synced: Total events successfully synced
        total_failed: Total events that failed to sync
        last_sync_error: Last sync error message
    """

    __tablename__ = "doctor_calendar_settings"

    # Relations
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Google Calendar settings
    google_calendar_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    google_refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,  # This will be encrypted before storage
    )
    sync_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sync_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        default=15,
        nullable=False,
    )

    # Event customization
    event_visibility: Mapped[str] = mapped_column(
        String(20),
        default="private",
        nullable=False,
    )
    event_reminders: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Sync statistics
    total_synced: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_sync_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="calendar_settings")

    def __repr__(self) -> str:
        return f"<DoctorCalendarSettings doctor_id={self.doctor_id} calendar={self.google_calendar_id}>"
