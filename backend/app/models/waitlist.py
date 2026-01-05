"""
Waitlist model for managing appointment queues.

Patients can join a waitlist when:
- Their preferred doctor has no available slots
- They want to be notified when a slot opens
- They need an emergency appointment

Features:
- Priority queue (emergency, urgent, normal)
- Auto-notification when slots open
- Estimated wait time tracking
- Multiple notification channels (SMS, WhatsApp)
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUID


class WaitlistPriority(str, Enum):
    """Priority levels for waitlist entries."""
    EMERGENCY = "emergency"  # Medical emergency, needs immediate slot
    URGENT = "urgent"        # Urgent but not emergency
    NORMAL = "normal"        # Standard priority
    FLEXIBLE = "flexible"    # Can wait, flexible on timing


class WaitlistStatus(str, Enum):
    """Status of a waitlist entry."""
    WAITING = "waiting"      # In queue, waiting for slot
    NOTIFIED = "notified"    # Slot available, patient notified
    BOOKED = "booked"        # Patient booked the slot
    EXPIRED = "expired"      # Entry expired (too old)
    CANCELLED = "cancelled"  # Patient cancelled


class NotificationChannel(str, Enum):
    """Preferred notification channels."""
    SMS = "sms"
    WHATSAPP = "whatsapp"
    BOTH = "both"
    APP = "app"  # Push notification


class Waitlist(Base, TimestampMixin):
    """
    Waitlist entry for appointment queue.

    Tracks patients waiting for appointments when slots are unavailable.
    """

    __tablename__ = "waitlist"

    id: Mapped[UUID] = mapped_column(
        PGUUID(),
        primary_key=True,
        default=uuid4,
    )

    # Clinic and doctor
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(),
        ForeignKey("doctors.id"),
        nullable=True,  # Can be any available doctor
        index=True,
    )

    # Patient info
    patient_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(),
        ForeignKey("patients.id"),
        nullable=True,  # New patient might not have ID yet
    )
    patient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    patient_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Preferred dates
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    alternate_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    preferred_time_slot: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "morning", "afternoon", "10:00-12:00"

    # Priority and status
    priority: Mapped[str] = mapped_column(
        String(20),
        default=WaitlistPriority.NORMAL.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=WaitlistStatus.WAITING.value,
        index=True,
    )

    # Queue position (1 = first in line)
    queue_position: Mapped[int] = mapped_column(Integer, default=0)

    # Reason for visit
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notification preferences
    notification_channel: Mapped[str] = mapped_column(
        String(20),
        default=NotificationChannel.SMS.value,
    )
    notification_count: Mapped[int] = mapped_column(Integer, default=0)
    last_notified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Booking tracking
    offered_slot_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    slot_offer_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    booked_appointment_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(),
        ForeignKey("appointments.id"),
        nullable=True,
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    clinic = relationship("Clinic", backref="waitlist_entries")
    doctor = relationship("Doctor", backref="waitlist_entries")
    patient = relationship("Patient", backref="waitlist_entries")
    booked_appointment = relationship("Appointment")

    def __repr__(self) -> str:
        return f"<Waitlist {self.patient_name} for {self.preferred_date} ({self.status})>"

    @property
    def is_waiting(self) -> bool:
        """Check if entry is still waiting."""
        return self.status == WaitlistStatus.WAITING.value

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.status == WaitlistStatus.EXPIRED.value:
            return True
        # Auto-expire if preferred date is past
        if self.preferred_date < date.today():
            return True
        return False

    @property
    def can_be_notified(self) -> bool:
        """Check if patient can receive another notification."""
        if not self.is_waiting:
            return False
        # Limit to 3 notifications
        if self.notification_count >= 3:
            return False
        return True

    def mark_notified(self, offered_slot: datetime, expires_in_minutes: int = 30):
        """Mark entry as notified with slot offer."""
        from datetime import timedelta
        self.status = WaitlistStatus.NOTIFIED.value
        self.offered_slot_time = offered_slot
        self.slot_offer_expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        self.notification_count += 1
        self.last_notified_at = datetime.now(timezone.utc)

    def mark_booked(self, appointment_id: UUID):
        """Mark entry as booked."""
        self.status = WaitlistStatus.BOOKED.value
        self.booked_appointment_id = appointment_id

    def mark_expired(self):
        """Mark entry as expired."""
        self.status = WaitlistStatus.EXPIRED.value

    def mark_cancelled(self):
        """Mark entry as cancelled."""
        self.status = WaitlistStatus.CANCELLED.value
