"""
Appointment model - core scheduling entity.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, generate_uuid, get_utc_now

if TYPE_CHECKING:
    from src.models.doctor import Doctor
    from src.models.invoice import Invoice
    from src.models.patient import Patient
    from src.models.service import Service


class AppointmentStatus(str, Enum):
    """Appointment status values."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class AppointmentType(str, Enum):
    """Appointment type values."""

    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    PROCEDURE = "procedure"
    EMERGENCY = "emergency"
    TELEMEDICINE = "telemedicine"


class AppointmentSource(str, Enum):
    """How the appointment was booked."""

    MANUAL = "manual"  # Receptionist booked
    ONLINE = "online"  # Patient self-booked online
    PHONE = "phone"  # Phone booking
    VOICE = "voice"  # Voice agent booking
    WALK_IN = "walk_in"  # Walk-in patient


class Appointment(Base):
    """
    Appointment entity for scheduling.

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to patient
        doctor_id: Reference to doctor
        service_id: Reference to service (optional)
        start_time: Appointment start datetime
        end_time: Appointment end datetime
        status: Current status (scheduled, completed, etc.)
        type: Appointment type (consultation, follow_up, etc.)
        source: How the appointment was booked
        notes: Additional notes
        created_by: User who created the appointment
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Relationships
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=False, index=True
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("doctors.id"), nullable=False, index=True
    )
    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id"), nullable=True
    )

    # Timing
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Status and Type
    status: Mapped[str] = mapped_column(
        String(20), default=AppointmentStatus.SCHEDULED.value
    )
    type: Mapped[str] = mapped_column(
        String(20), default=AppointmentType.CONSULTATION.value
    )
    source: Mapped[str] = mapped_column(
        String(20), default=AppointmentSource.MANUAL.value
    )

    # Additional Info
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    # ORM Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    service: Mapped[Optional["Service"]] = relationship("Service")
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", back_populates="appointment", lazy="dynamic"
    )

    @property
    def duration_minutes(self) -> int:
        """Calculate appointment duration in minutes."""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    @property
    def is_past(self) -> bool:
        """Check if appointment is in the past."""
        return self.end_time < datetime.utcnow()

    @property
    def is_today(self) -> bool:
        """Check if appointment is today."""
        today = datetime.utcnow().date()
        return self.start_time.date() == today

    @property
    def can_cancel(self) -> bool:
        """Check if appointment can be cancelled."""
        return self.status in [
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value,
        ]

    @property
    def can_reschedule(self) -> bool:
        """Check if appointment can be rescheduled."""
        return self.can_cancel

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, "
            f"patient_id={self.patient_id}, "
            f"start_time={self.start_time}, "
            f"status={self.status})>"
        )
