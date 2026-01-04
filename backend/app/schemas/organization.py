"""
Organization schemas for multi-location practice management.
"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class OrganizationBase(BaseModel):
    """Base organization schema."""

    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=10, max_length=15)
    website: str | None = Field(None, max_length=255)


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""

    slug: str | None = Field(None, min_length=3, max_length=100)
    owner_user_id: UUID
    subscription_tier: str = "free"
    max_clinics: int = Field(1, ge=1, le=100)
    max_users: int = Field(5, ge=1, le=1000)
    logo_url: str | None = None
    primary_color: str = "#1976D2"

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        """Validate slug format."""
        if v is None:
            return v
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v

    @field_validator("subscription_tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        """Validate subscription tier."""
        valid_tiers = {"free", "basic", "premium", "enterprise"}
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")
        return v


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    subscription_tier: str | None = None
    max_clinics: int | None = Field(None, ge=1, le=100)
    max_users: int | None = Field(None, ge=1, le=1000)
    is_active: bool | None = None


class OrganizationResponse(BaseModel):
    """Schema for organization response."""

    id: UUID
    name: str
    slug: str
    description: str | None
    owner_user_id: UUID
    subscription_tier: str
    subscription_expires_at: str | None
    max_clinics: int
    max_users: int
    logo_url: str | None
    primary_color: str
    email: str | None
    phone: str | None
    website: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields
    clinic_count: int = 0
    user_count: int = 0

    model_config = {"from_attributes": True}


class OrganizationStats(BaseModel):
    """Schema for organization-wide statistics."""

    total_clinics: int
    total_users: int
    total_patients: int
    total_appointments_today: int
    total_revenue_month: float
    revenue_by_clinic: dict[str, float]  # clinic_id -> revenue
    appointments_by_clinic: dict[str, int]  # clinic_id -> count
    top_performing_clinic: str | None


class OrganizationAddClinic(BaseModel):
    """Schema for adding a clinic to an organization."""

    clinic_id: UUID


class OrganizationRemoveClinic(BaseModel):
    """Schema for removing a clinic from an organization."""

    clinic_id: UUID
    transfer_data_to_clinic_id: UUID | None = None  # Optional data migration
