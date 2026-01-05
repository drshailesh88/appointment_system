"""
Phone call and voice bot models.

Phase 18: Voice Bot / Phone Automation
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.clinic import Clinic
    from app.models.patient import Patient


class CallStatus(str, Enum):
    """Call status types."""

    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    VOICEMAIL = "voicemail"


class CallDirection(str, Enum):
    """Call direction."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallIntent(str, Enum):
    """Detected call intent."""

    BOOK_APPOINTMENT = "book_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    CHECK_AVAILABILITY = "check_availability"
    GENERAL_INQUIRY = "general_inquiry"
    UNKNOWN = "unknown"


class PhoneCall(BaseModel):
    """Phone call record."""

    __tablename__ = "phone_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Call identifiers
    call_sid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), default=CallDirection.INBOUND)

    # Status
    status: Mapped[str] = mapped_column(String(50), default=CallStatus.RINGING)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Voice bot session
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    transcript: Mapped[Optional[str]] = mapped_column(Text)

    # Outcome
    intent_detected: Mapped[Optional[str]] = mapped_column(String(100))
    action_taken: Mapped[Optional[str]] = mapped_column(String(100))

    # Foreign keys
    appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Quality metrics
    language_detected: Mapped[Optional[str]] = mapped_column(String(20))
    sentiment: Mapped[Optional[str]] = mapped_column(String(20))

    # Recording
    recording_url: Mapped[Optional[str]] = mapped_column(String(500))
    recording_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    call_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    appointment: Mapped[Optional["Appointment"]] = relationship(
        "Appointment",
        back_populates="phone_calls",
        foreign_keys=[appointment_id],
    )
    patient: Mapped[Optional["Patient"]] = relationship(
        "Patient",
        back_populates="phone_calls",
        foreign_keys=[patient_id],
    )
    clinic: Mapped["Clinic"] = relationship(
        "Clinic",
        back_populates="phone_calls",
        foreign_keys=[clinic_id],
    )
    transcript_segments: Mapped[list["CallTranscriptSegment"]] = relationship(
        "CallTranscriptSegment",
        back_populates="call",
        cascade="all, delete-orphan",
        order_by="CallTranscriptSegment.start_time_ms",
    )

    def __repr__(self) -> str:
        return f"<PhoneCall {self.call_sid} {self.direction} {self.status}>"


class CallTranscriptSegment(BaseModel):
    """Individual segments of call transcript."""

    __tablename__ = "call_transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("phone_calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Speaker
    speaker: Mapped[str] = mapped_column(String(20))  # "bot" or "caller"
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(String(10))
    confidence: Mapped[Optional[float]] = mapped_column(Float)

    # Timing
    start_time_ms: Mapped[int] = mapped_column(Integer)
    end_time_ms: Mapped[int] = mapped_column(Integer)

    # Entities extracted from this segment
    entities: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationship
    call: Mapped["PhoneCall"] = relationship(
        "PhoneCall",
        back_populates="transcript_segments",
        foreign_keys=[call_id],
    )

    def __repr__(self) -> str:
        return f"<CallTranscriptSegment {self.speaker}: {self.text[:50]}...>"
