"""
Schemas for public API endpoints (patient booking portal).
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# OTP Schemas
class OTPSendRequest(BaseModel):
    """Request to send OTP to phone."""

    phone: str = Field(..., min_length=10, max_length=15, description="Phone number")


class OTPSendResponse(BaseModel):
    """Response after sending OTP."""

    message: str
    expires_in_seconds: int


class OTPVerifyRequest(BaseModel):
    """Request to verify OTP."""

    phone: str = Field(..., min_length=10, max_length=15)
    otp_code: str = Field(..., min_length=6, max_length=6)


class OTPVerifyResponse(BaseModel):
    """Response after successful OTP verification."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


# Public Doctor Schemas
class PublicDoctorListItem(BaseModel):
    """Doctor list item for public view."""

    id: UUID
    name: str
    specialization: str | None
    qualification: str | None
    experience_years: int | None
    consultation_fee: Decimal
    photo_url: str | None
    languages: list[str] | None
    clinic_name: str | None = None
    clinic_address: str | None = None

    class Config:
        from_attributes = True


class PublicDoctorDetail(PublicDoctorListItem):
    """Detailed doctor info for public view."""

    bio: str | None
    registration_number: str | None
    slot_duration: int
    working_hours: dict | None


# Slot Schemas
class PublicSlot(BaseModel):
    """Available time slot."""

    start_time: datetime
    end_time: datetime
    is_available: bool


class PublicSlotsResponse(BaseModel):
    """Available slots for a doctor on a date."""

    doctor_id: UUID
    date: date
    slots: list[PublicSlot]


# Appointment Booking Schemas
class PublicBookingRequest(BaseModel):
    """Request to book an appointment (public portal)."""

    doctor_id: UUID
    scheduled_start: datetime
    duration_minutes: int = 15

    # Patient info (create if new)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    email: str | None = Field(None, max_length=255)
    date_of_birth: date | None = None
    gender: str | None = Field(None, pattern="^[MFO]$")

    # Appointment details
    chief_complaint: str | None = Field(None, max_length=500)
    notes: str | None = None


class PublicAppointmentResponse(BaseModel):
    """Appointment details for public portal."""

    id: UUID
    doctor_id: UUID
    doctor_name: str
    scheduled_start: datetime
    duration_minutes: int
    status: str
    appointment_type: str
    token_number: int | None
    chief_complaint: str | None
    patient_name: str

    class Config:
        from_attributes = True


class PublicCancelRequest(BaseModel):
    """Request to cancel appointment."""

    reason: str | None = Field(None, max_length=500)
