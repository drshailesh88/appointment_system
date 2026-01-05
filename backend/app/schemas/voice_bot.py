"""
Voice Bot schemas.

Phase 18: Voice Bot / Phone Automation
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegmentBase(BaseModel):
    """Base transcript segment schema."""

    speaker: str
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    start_time_ms: int
    end_time_ms: int
    entities: dict = Field(default_factory=dict)


class TranscriptSegmentCreate(TranscriptSegmentBase):
    """Create transcript segment."""

    call_id: UUID


class TranscriptSegmentResponse(TranscriptSegmentBase):
    """Transcript segment response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    call_id: UUID
    created_at: datetime


class PhoneCallBase(BaseModel):
    """Base phone call schema."""

    from_number: str
    to_number: str
    direction: str
    status: str = "ringing"


class PhoneCallCreate(PhoneCallBase):
    """Create phone call."""

    call_sid: str
    clinic_id: UUID
    session_id: Optional[str] = None
    started_at: Optional[datetime] = None


class PhoneCallUpdate(BaseModel):
    """Update phone call."""

    status: Optional[str] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    intent_detected: Optional[str] = None
    action_taken: Optional[str] = None
    appointment_id: Optional[UUID] = None
    patient_id: Optional[UUID] = None
    language_detected: Optional[str] = None
    sentiment: Optional[str] = None
    recording_url: Optional[str] = None
    recording_consent: Optional[bool] = None
    metadata: Optional[dict] = None


class PhoneCallResponse(PhoneCallBase):
    """Phone call response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    call_sid: str
    clinic_id: UUID
    started_at: Optional[datetime]
    answered_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    session_id: Optional[str]
    transcript: Optional[str]
    intent_detected: Optional[str]
    action_taken: Optional[str]
    appointment_id: Optional[UUID]
    patient_id: Optional[UUID]
    language_detected: Optional[str]
    sentiment: Optional[str]
    recording_url: Optional[str]
    recording_consent: bool
    metadata: dict
    created_at: datetime
    updated_at: datetime


class PhoneCallWithTranscript(PhoneCallResponse):
    """Phone call with transcript segments."""

    transcript_segments: list[TranscriptSegmentResponse] = Field(default_factory=list)


class OutboundCallRequest(BaseModel):
    """Request to initiate outbound call."""

    to_number: str = Field(..., description="Phone number to call (10 digits)")
    clinic_id: UUID = Field(..., description="Clinic ID")
    purpose: str = Field(
        default="reminder",
        description="Call purpose (reminder, followup, confirmation)",
    )
    appointment_id: Optional[UUID] = Field(
        None,
        description="Associated appointment ID",
    )
    patient_id: Optional[UUID] = Field(None, description="Patient ID")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class OutboundCallResponse(BaseModel):
    """Outbound call response."""

    call_sid: str
    status: str
    call_id: UUID
    message: str = "Call initiated successfully"


class CallStatsResponse(BaseModel):
    """Call statistics response."""

    total_calls: int
    inbound_calls: int
    outbound_calls: int
    completed_calls: int
    failed_calls: int
    average_duration_seconds: float
    appointments_booked: int
    appointments_rescheduled: int
    appointments_cancelled: int
    languages: dict[str, int]  # Language -> count
    intents: dict[str, int]  # Intent -> count


class VoiceBotSessionRequest(BaseModel):
    """Voice bot session request."""

    call_sid: str
    from_number: str
    to_number: str
    clinic_id: UUID


class VoiceBotSessionResponse(BaseModel):
    """Voice bot session response."""

    session_id: str
    greeting: str
    greeting_audio_base64: Optional[str] = None
    language: str = "hi"
