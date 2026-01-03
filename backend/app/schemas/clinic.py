"""
Clinic schemas for multi-tenant support.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class ClinicBase(BaseModel):
    """Base clinic schema."""

    name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., min_length=10, max_length=15)
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    website: str | None = Field(None, max_length=255)
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"


class ClinicCreate(ClinicBase):
    """Schema for creating a clinic."""

    slug: str | None = Field(None, min_length=3, max_length=100)
    gst_number: str | None = Field(None, max_length=20)
    registration_number: str | None = Field(None, max_length=50)
    logo_url: str | None = None
    primary_color: str | None = "#1976D2"

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        """Validate slug format."""
        if v is None:
            return v
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v

    @field_validator("gst_number")
    @classmethod
    def validate_gst(cls, v: str | None) -> str | None:
        """Validate GST number format (basic)."""
        if v is None:
            return v
        v = v.upper()
        if len(v) != 15:
            raise ValueError("GST number must be 15 characters")
        return v


class ClinicUpdate(BaseModel):
    """Schema for updating a clinic."""

    name: str | None = Field(None, min_length=2, max_length=200)
    phone: str | None = Field(None, min_length=10, max_length=15)
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    website: str | None = None
    gst_number: str | None = None
    registration_number: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


class ClinicResponse(BaseModel):
    """Schema for clinic response."""

    id: UUID
    name: str
    slug: str
    phone: str
    email: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    website: str | None
    gst_number: str | None
    registration_number: str | None
    logo_url: str | None
    primary_color: str | None
    subscription_tier: str
    subscription_expires_at: str | None
    timezone: str
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClinicStats(BaseModel):
    """Schema for clinic statistics."""

    total_patients: int
    total_doctors: int
    total_appointments_today: int
    total_revenue_month: float
    pending_appointments: int
