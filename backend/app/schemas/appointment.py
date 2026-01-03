"""
Appointment schemas for scheduling.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.appointment import AppointmentStatus, AppointmentType, BookingSource


class AppointmentBase(BaseModel):
    """Base appointment schema."""

    patient_id: UUID
    doctor_id: UUID
    scheduled_start: datetime
    duration_minutes: int = Field(default=15, ge=5, le=120)
    appointment_type: AppointmentType = AppointmentType.NEW_CONSULTATION
    chief_complaint: str | None = Field(None, max_length=500)
    notes: str | None = None


class AppointmentCreate(AppointmentBase):
    """Schema for creating an appointment."""

    booking_source: BookingSource = BookingSource.WALK_IN
    service_id: UUID | None = None
    voice_booking_metadata: dict[str, Any] | None = None

    @field_validator("scheduled_start")
    @classmethod
    def validate_future_time(cls, v: datetime) -> datetime:
        """Ensure appointment is in the future (with 5 min buffer)."""
        # Allow some flexibility for walk-ins
        return v


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""

    scheduled_start: datetime | None = None
    duration_minutes: int | None = Field(None, ge=5, le=120)
    status: AppointmentStatus | None = None
    appointment_type: AppointmentType | None = None
    chief_complaint: str | None = None
    notes: str | None = None
    token_number: int | None = None
    cancellation_reason: str | None = None
    service_id: UUID | None = None


class AppointmentCheckIn(BaseModel):
    """Schema for patient check-in."""

    token_number: int | None = None


class AppointmentComplete(BaseModel):
    """Schema for completing an appointment."""

    notes: str | None = None
    emr_visit_id: str | None = None


class AppointmentResponse(BaseModel):
    """Schema for appointment response."""

    id: UUID
    patient_id: UUID
    doctor_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    status: str
    appointment_type: str
    booking_source: str
    chief_complaint: str | None
    notes: str | None
    token_number: int | None
    check_in_time: datetime | None
    start_time: datetime | None
    end_time: datetime | None
    wait_time_minutes: int | None
    consultation_duration_minutes: int | None
    cancellation_reason: str | None
    cancelled_by: str | None
    reminder_sent: bool
    service_id: UUID | None
    emr_visit_id: str | None
    created_at: datetime
    updated_at: datetime

    # Nested details (optional, populated when needed)
    patient_name: str | None = None
    doctor_name: str | None = None

    model_config = {"from_attributes": True}


class AppointmentListResponse(BaseModel):
    """Schema for listing appointments."""

    id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    doctor_name: str
    scheduled_start: datetime
    duration_minutes: int
    status: str
    appointment_type: str
    token_number: int | None
    chief_complaint: str | None

    model_config = {"from_attributes": True}


class AppointmentSlot(BaseModel):
    """Schema for an available time slot."""

    start_time: datetime
    end_time: datetime
    is_available: bool = True


class SlotAvailabilityRequest(BaseModel):
    """Schema for checking slot availability."""

    doctor_id: UUID
    date: date
    duration_minutes: int = 15


class SlotAvailabilityResponse(BaseModel):
    """Schema for slot availability response."""

    doctor_id: UUID
    date: date
    slots: list[AppointmentSlot]


class DailySchedule(BaseModel):
    """Schema for a doctor's daily schedule."""

    doctor_id: UUID
    date: date
    appointments: list[AppointmentListResponse]
    total_appointments: int
    completed: int
    pending: int
    cancelled: int


class RescheduleRequest(BaseModel):
    """Schema for rescheduling an appointment."""

    new_start_time: datetime
    reason: str | None = None
