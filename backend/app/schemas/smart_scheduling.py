"""
Smart Scheduling schemas for AI-powered appointment suggestions.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.appointment import AppointmentType


class SlotSuggestion(BaseModel):
    """A suggested appointment slot with confidence score."""

    slot_time: datetime = Field(..., description="Suggested appointment time")
    score: float = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    reasons: list[str] = Field(..., description="Reasons for this suggestion")
    doctor_id: str = Field(..., description="Doctor ID")
    duration_minutes: int = Field(..., ge=5, le=120, description="Appointment duration")

    model_config = {"from_attributes": True}


class SlotSuggestionsRequest(BaseModel):
    """Request for slot suggestions."""

    patient_id: UUID
    doctor_id: UUID
    appointment_type: AppointmentType = AppointmentType.NEW_CONSULTATION
    preferred_date: date | None = Field(None, description="Preferred date (optional)")
    duration_minutes: int = Field(15, ge=5, le=120, description="Required duration")
    max_suggestions: int = Field(5, ge=1, le=10, description="Maximum suggestions to return")


class SlotSuggestionsResponse(BaseModel):
    """Response with suggested slots."""

    patient_id: str
    doctor_id: str
    suggestions: list[SlotSuggestion]
    total_analyzed: int = Field(..., description="Total slots analyzed")

    model_config = {"from_attributes": True}


class OptimalWindow(BaseModel):
    """An optimal booking time window."""

    hour: int = Field(..., ge=0, le=23)
    time_range: str = Field(..., description="Time range (e.g., '09:00 - 10:00')")
    appointment_count: int = Field(..., description="Historical appointment count")
    average_wait_minutes: float = Field(..., description="Average wait time")
    is_optimal: bool = Field(..., description="Whether this is an optimal window")


class OptimalTimesResponse(BaseModel):
    """Response with optimal booking windows."""

    doctor_id: str
    analyzed_period_days: int
    optimal_windows: list[OptimalWindow]
    total_appointments_analyzed: int

    model_config = {"from_attributes": True}


class HourlyPattern(BaseModel):
    """Hourly booking pattern."""

    hour: int
    count: int


class DailyPattern(BaseModel):
    """Daily booking pattern."""

    day: str
    count: int


class SchedulingPatterns(BaseModel):
    """Booking pattern analysis for a doctor."""

    doctor_id: str
    period: dict[str, str] = Field(..., description="Start and end dates")
    total_appointments: int
    patterns: dict = Field(..., description="Detailed pattern breakdown")
    recommendations: list[str] = Field(
        default_factory=list,
        description="AI-generated recommendations",
    )

    model_config = {"from_attributes": True}


class SuggestionFeedback(BaseModel):
    """Feedback on suggestion quality for ML improvement."""

    suggestion_id: str | None = Field(
        None,
        description="ID of the suggestion (can be timestamp+patient_id)",
    )
    patient_id: UUID
    doctor_id: UUID
    suggested_slot: datetime
    was_accepted: bool = Field(..., description="Whether suggestion was accepted")
    actual_slot: datetime | None = Field(
        None,
        description="Actual slot booked (if different)",
    )
    feedback_notes: str | None = Field(None, description="Optional feedback text")


class SuggestionFeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    success: bool
    message: str


class PatternSummary(BaseModel):
    """Summary of scheduling patterns."""

    peak_hour: int
    peak_hour_range: str
    peak_day: str
    busiest_day_count: int
    hourly_distribution: dict[str, int]
    daily_distribution: dict[str, int]
    appointment_types: dict[str, int]
