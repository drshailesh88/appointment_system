"""
Consultation schemas for telemedicine.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.consultation import (
    ConnectionQuality,
    ConnectionType,
    ConsultationStatus,
    ParticipantRole,
)


class ConsultationBase(BaseModel):
    """Base consultation schema."""

    appointment_id: UUID


class ConsultationCreate(ConsultationBase):
    """Schema for creating a consultation."""

    pass


class JoinRoomResponse(BaseModel):
    """Response when joining a consultation room."""

    room_url: str
    jwt_token: str
    room_name: str
    consultation_id: UUID
    role: ParticipantRole


class WaitingRoomStatus(BaseModel):
    """Status of patient in waiting room."""

    status: ConsultationStatus
    position: int | None = Field(
        None,
        description="Position in queue (1 = next)",
    )
    estimated_wait_minutes: int | None = Field(
        None,
        description="Estimated wait time in minutes",
    )
    patient_joined_at: datetime | None = None


class WaitingRoomJoinResponse(BaseModel):
    """Response when patient joins waiting room."""

    consultation_id: UUID
    status: ConsultationStatus
    message: str = "You are in the waiting room"
    position: int | None = None
    estimated_wait_minutes: int | None = None


class RecordingConsentRequest(BaseModel):
    """Request to submit recording consent."""

    consent: bool = Field(
        ...,
        description="Whether user consents to recording",
    )
    consent_text: str | None = Field(
        None,
        description="Legal consent text shown to user",
    )


class RecordingConsentResponse(BaseModel):
    """Response after submitting consent."""

    consultation_id: UUID
    user_role: ParticipantRole
    consent_given: bool
    consent_timestamp: datetime
    can_start_recording: bool = Field(
        ...,
        description="Whether recording can start (requires both parties)",
    )


class RatingRequest(BaseModel):
    """Request to submit post-consultation rating."""

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating from 1 (poor) to 5 (excellent)",
    )
    feedback: str | None = Field(
        None,
        max_length=500,
        description="Optional feedback text",
    )


class ConsultationParticipantResponse(BaseModel):
    """Schema for consultation participant."""

    id: UUID
    user_id: UUID
    role: str
    joined_at: datetime | None
    left_at: datetime | None
    device_type: str | None
    connection_type: str | None
    session_duration_minutes: int | None

    model_config = {"from_attributes": True}


class ConsultationRecordingResponse(BaseModel):
    """Schema for consultation recording."""

    id: UUID
    consultation_id: UUID
    patient_consent_at: datetime | None
    doctor_consent_at: datetime | None
    file_path: str | None
    file_size_mb: int | None
    duration_seconds: int | None
    uploaded_to_emr: bool
    expires_at: datetime | None
    has_full_consent: bool

    model_config = {"from_attributes": True}


class ConsultationResponse(BaseModel):
    """Schema for consultation response."""

    id: UUID
    appointment_id: UUID
    room_name: str
    room_url: str | None
    status: str
    scheduled_start: datetime | None
    patient_joined_at: datetime | None
    doctor_joined_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_minutes: int | None
    wait_time_minutes: int | None
    recording_consent: bool
    recording_url: str | None
    patient_rating: int | None
    doctor_rating: int | None
    connection_quality: str | None
    created_at: datetime
    updated_at: datetime

    # Nested relationships (optional)
    participants: list[ConsultationParticipantResponse] | None = None
    recording: ConsultationRecordingResponse | None = None

    model_config = {"from_attributes": True}


class ConsultationListResponse(BaseModel):
    """Schema for listing consultations."""

    id: UUID
    appointment_id: UUID
    status: str
    scheduled_start: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_minutes: int | None
    patient_rating: int | None

    model_config = {"from_attributes": True}


class DoctorQueueItem(BaseModel):
    """Schema for a patient in doctor's waiting queue."""

    consultation_id: UUID
    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    patient_joined_at: datetime
    wait_time_minutes: int
    chief_complaint: str | None
    is_emergency: bool = False


class DoctorQueueResponse(BaseModel):
    """Schema for doctor's waiting room queue."""

    doctor_id: UUID
    queue: list[DoctorQueueItem]
    total_waiting: int


class ConnectionQualityUpdate(BaseModel):
    """Schema for updating connection quality."""

    quality: ConnectionQuality
    device_type: str | None = None
    connection_type: ConnectionType | None = None


class ConsultationEndRequest(BaseModel):
    """Request to end a consultation."""

    notes: str | None = Field(
        None,
        max_length=1000,
        description="Optional notes about the consultation",
    )
    connection_quality: ConnectionQuality | None = None
