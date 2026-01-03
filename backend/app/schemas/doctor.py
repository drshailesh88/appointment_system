"""
Doctor schemas for medical professional management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TimeSlot(BaseModel):
    """Single time slot."""

    start: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM format
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class WorkingHours(BaseModel):
    """Weekly working hours."""

    monday: list[TimeSlot] | None = None
    tuesday: list[TimeSlot] | None = None
    wednesday: list[TimeSlot] | None = None
    thursday: list[TimeSlot] | None = None
    friday: list[TimeSlot] | None = None
    saturday: list[TimeSlot] | None = None
    sunday: list[TimeSlot] | None = None


class DoctorBase(BaseModel):
    """Base doctor schema."""

    name: str = Field(..., min_length=2, max_length=200)
    specialization: str | None = Field(None, max_length=100)
    qualification: str | None = Field(None, max_length=500)
    registration_number: str | None = Field(None, max_length=50)
    experience_years: int | None = Field(None, ge=0, le=70)
    phone: str | None = Field(None, min_length=10, max_length=15)
    email: EmailStr | None = None


class DoctorCreate(DoctorBase):
    """Schema for creating a doctor."""

    clinic_id: UUID
    consultation_fee: Decimal = Field(default=Decimal("500.00"), ge=0)
    followup_fee: Decimal | None = Field(None, ge=0)
    slot_duration: int = Field(default=15, ge=5, le=120)
    working_hours: dict[str, Any] | None = None
    break_slots: list[dict[str, str]] | None = None
    bio: str | None = None
    photo_url: str | None = None
    languages: list[str] | None = None


class DoctorUpdate(BaseModel):
    """Schema for updating a doctor."""

    name: str | None = Field(None, min_length=2, max_length=200)
    specialization: str | None = None
    qualification: str | None = None
    registration_number: str | None = None
    experience_years: int | None = Field(None, ge=0, le=70)
    phone: str | None = None
    email: EmailStr | None = None
    consultation_fee: Decimal | None = Field(None, ge=0)
    followup_fee: Decimal | None = Field(None, ge=0)
    slot_duration: int | None = Field(None, ge=5, le=120)
    working_hours: dict[str, Any] | None = None
    break_slots: list[dict[str, str]] | None = None
    bio: str | None = None
    photo_url: str | None = None
    languages: list[str] | None = None
    is_active: bool | None = None
    accepting_new_patients: bool | None = None


class DoctorResponse(BaseModel):
    """Schema for doctor response."""

    id: UUID
    name: str
    specialization: str | None
    qualification: str | None
    registration_number: str | None
    experience_years: int | None
    phone: str | None
    email: str | None
    clinic_id: UUID
    consultation_fee: Decimal
    followup_fee: Decimal | None
    slot_duration: int
    working_hours: dict[str, Any] | None
    break_slots: list[dict[str, str]] | None
    bio: str | None
    photo_url: str | None
    languages: list[str] | None
    is_active: bool
    accepting_new_patients: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DoctorListResponse(BaseModel):
    """Schema for listing doctors."""

    id: UUID
    name: str
    specialization: str | None
    photo_url: str | None
    consultation_fee: Decimal
    slot_duration: int
    is_active: bool
    accepting_new_patients: bool

    model_config = {"from_attributes": True}
