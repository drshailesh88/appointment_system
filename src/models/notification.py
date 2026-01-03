"""
Notification model for appointment reminders and alerts.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, generate_uuid, get_utc_now


class NotificationType(str, Enum):
    """Notification type values."""

    REMINDER = "reminder"
    CONFIRMATION = "confirmation"
    CANCELLATION = "cancellation"
    RESCHEDULE = "reschedule"
    PAYMENT = "payment"
    CUSTOM = "custom"


class NotificationChannel(str, Enum):
    """Notification delivery channel."""

    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PUSH = "push"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Notification(Base):
    """
    Notification entity for patient communication.

    Attributes:
        id: Unique identifier (UUID)
        patient_id: Reference to patient
        appointment_id: Reference to appointment (optional)
        type: Notification type
        channel: Delivery channel
        message: Notification content
        status: Delivery status
        scheduled_at: When to send
        sent_at: When actually sent
        error_message: Error details if failed
    """

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # References
    patient_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=True, index=True
    )
    appointment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("appointments.id"), nullable=True
    )

    # Notification Details
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient: Mapped[str] = mapped_column(String(100), nullable=False)  # Phone/email
    message: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status and Timing
    status: Mapped[str] = mapped_column(
        String(20), default=NotificationStatus.PENDING.value
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Delivery Info
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )

    @property
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled for future."""
        if self.scheduled_at:
            return self.scheduled_at > datetime.utcnow()
        return False

    @property
    def can_cancel(self) -> bool:
        """Check if notification can be cancelled."""
        return self.status in [
            NotificationStatus.PENDING.value,
            NotificationStatus.SCHEDULED.value,
        ]

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, "
            f"type={self.type}, "
            f"channel={self.channel}, "
            f"status={self.status})>"
        )
