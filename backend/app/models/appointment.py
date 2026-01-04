"""
Appointment model for scheduling.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.patient import Patient
    from app.models.procedure import Procedure
    from app.models.service import Service


class AppointmentStatus(str, Enum):
    """Appointment status types."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class AppointmentType(str, Enum):
    """Appointment type."""

    NEW_CONSULTATION = "new_consultation"
    FOLLOW_UP = "follow_up"
    PROCEDURE = "procedure"
    EMERGENCY = "emergency"
    TELECONSULTATION = "teleconsultation"


class BookingSource(str, Enum):
    """How the appointment was booked."""

    WALK_IN = "walk_in"
    PHONE = "phone"
    WEB = "web"
    APP = "app"
    VOICE_AGENT = "voice_agent"
    WHATSAPP = "whatsapp"


class Appointment(BaseModel):
    """
    Appointment model for scheduling.

    Attributes:
        patient_id: Patient being seen
        doctor_id: Doctor providing care
        scheduled_start: Appointment start time
        scheduled_end: Appointment end time
        status: Current appointment status
        appointment_type: Type of visit
        booking_source: How it was booked
        notes: Appointment notes
        chief_complaint: Reason for visit
        token_number: Queue token for the day
        check_in_time: When patient checked in
        start_time: When consultation started
        end_time: When consultation ended
        cancellation_reason: Why cancelled (if applicable)
        reminder_sent: Whether reminder was sent
    """

    __tablename__ = "appointments"

    # Core Relations
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )

    # Scheduling
    scheduled_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    scheduled_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15)

    # Status & Type
    status: Mapped[str] = mapped_column(
        String(20),
        default=AppointmentStatus.SCHEDULED.value,
        index=True,
    )
    appointment_type: Mapped[str] = mapped_column(
        String(20),
        default=AppointmentType.NEW_CONSULTATION.value,
    )
    booking_source: Mapped[str] = mapped_column(
        String(20),
        default=BookingSource.WALK_IN.value,
    )

    # Clinical Info
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Queue Management
    token_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timing Tracking
    check_in_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Cancellation
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Rescheduling
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=True,
    )

    # Reminders
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Service/Procedure
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=True,
    )

    # Voice Agent Metadata
    voice_booking_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # EMR Integration
    emr_visit_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    service: Mapped["Service | None"] = relationship("Service", back_populates="appointments")
    procedure: Mapped["Procedure | None"] = relationship(
        "Procedure",
        back_populates="appointment",
        uselist=False,
    )
    rescheduled_from: Mapped["Appointment | None"] = relationship(
        "Appointment",
        remote_side="Appointment.id",
        backref="rescheduled_to",
    )

    @property
    def wait_time_minutes(self) -> int | None:
        """Calculate wait time from check-in to consultation start."""
        if self.check_in_time and self.start_time:
            delta = self.start_time - self.check_in_time
            return int(delta.total_seconds() / 60)
        return None

    @property
    def consultation_duration_minutes(self) -> int | None:
        """Calculate actual consultation duration."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return None

    def __repr__(self) -> str:
        return f"<Appointment {self.id} ({self.status})>"
