"""
Telemedicine consultation models.

Provides video consultation capabilities with JWT-based Jitsi integration,
waiting room management, and recording consent tracking.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.user import User


class ConsultationStatus(str, Enum):
    """Consultation status types."""

    SCHEDULED = "scheduled"
    WAITING = "waiting"  # Patient in waiting room
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ParticipantRole(str, Enum):
    """Participant role in consultation."""

    DOCTOR = "doctor"
    PATIENT = "patient"
    SPECIALIST = "specialist"  # Second opinion
    TRANSLATOR = "translator"  # Language assistance


class ConnectionType(str, Enum):
    """Network connection type."""

    WIFI = "wifi"
    CELLULAR_4G = "4g"
    CELLULAR_3G = "3g"
    CELLULAR_5G = "5g"
    UNKNOWN = "unknown"


class ConnectionQuality(str, Enum):
    """Connection quality rating."""

    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class Consultation(BaseModel):
    """
    Video consultation session.

    Attributes:
        appointment_id: Linked appointment
        room_name: Unique Jitsi room identifier
        room_url: Full URL to join the room
        jwt_token: Encrypted JWT token for authentication
        status: Current consultation status
        scheduled_start: Expected start time
        patient_joined_at: When patient entered waiting room
        doctor_joined_at: When doctor joined consultation
        started_at: When consultation actually began
        ended_at: When consultation ended
        duration_minutes: Actual consultation duration
        recording_consent: Both parties agreed to recording
        recording_url: URL of stored recording
        recording_size_mb: Recording file size
        patient_rating: Patient's satisfaction rating (1-5)
        doctor_rating: Doctor's experience rating (1-5)
        connection_quality: Overall connection quality
    """

    __tablename__ = "consultations"

    # Core Relations
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=False,
        index=True,
        unique=True,  # One consultation per appointment
    )

    # Jitsi Room Details
    room_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    room_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jwt_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # Encrypted, regenerated for each join

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=ConsultationStatus.SCHEDULED.value,
        index=True,
    )

    # Timing
    scheduled_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    patient_joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    doctor_joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Recording
    recording_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recording_size_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Quality Metrics
    patient_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # 1-5
    doctor_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # 1-5
    connection_quality: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Metadata
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    appointment: Mapped["Appointment"] = relationship(
        "Appointment",
        back_populates="consultation",
    )
    participants: Mapped[list["ConsultationParticipant"]] = relationship(
        "ConsultationParticipant",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )
    recording: Mapped["ConsultationRecording | None"] = relationship(
        "ConsultationRecording",
        back_populates="consultation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def wait_time_minutes(self) -> int | None:
        """Calculate wait time from patient joining to consultation start."""
        if self.patient_joined_at and self.started_at:
            delta = self.started_at - self.patient_joined_at
            return int(delta.total_seconds() / 60)
        return None

    def __repr__(self) -> str:
        return f"<Consultation {self.id} ({self.status})>"


class ConsultationParticipant(BaseModel):
    """
    Participants in a video consultation.

    Tracks who joined, when, and from what device/connection.
    """

    __tablename__ = "consultation_participants"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultations.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default=ParticipantRole.PATIENT.value,
    )

    # Timing
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Device Info
    device_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # android, ios, web
    connection_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Relationships
    consultation: Mapped["Consultation"] = relationship(
        "Consultation",
        back_populates="participants",
    )
    user: Mapped["User"] = relationship("User")

    @property
    def session_duration_minutes(self) -> int | None:
        """Calculate how long participant was in the call."""
        if self.joined_at and self.left_at:
            delta = self.left_at - self.joined_at
            return int(delta.total_seconds() / 60)
        return None

    def __repr__(self) -> str:
        return f"<ConsultationParticipant {self.role} in {self.consultation_id}>"


class ConsultationRecording(BaseModel):
    """
    Recording metadata with consent tracking.

    HIPAA-compliant recording storage with encryption and retention policies.
    """

    __tablename__ = "consultation_recordings"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultations.id"),
        nullable=False,
        index=True,
        unique=True,
    )

    # Consent Tracking
    patient_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    doctor_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    consent_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # Legal consent text shown to users

    # Storage
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    encryption_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )  # Encrypted at rest

    # EMR Integration
    uploaded_to_emr: Mapped[bool] = mapped_column(Boolean, default=False)
    emr_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Retention Policy
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )  # Auto-delete after retention period

    # Relationships
    consultation: Mapped["Consultation"] = relationship(
        "Consultation",
        back_populates="recording",
    )

    @property
    def has_full_consent(self) -> bool:
        """Check if both parties consented to recording."""
        return self.patient_consent_at is not None and self.doctor_consent_at is not None

    def __repr__(self) -> str:
        return f"<ConsultationRecording {self.id} for {self.consultation_id}>"
