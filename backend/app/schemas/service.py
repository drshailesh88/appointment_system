"""
Service schemas for clinic services management.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceBase(BaseModel):
    """Base service schema."""

    name: str = Field(..., min_length=2, max_length=200)
    code: str | None = Field(None, max_length=20)
    category: str | None = Field(None, max_length=100)
    description: str | None = None
    price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    duration_minutes: int = Field(default=30, ge=5, le=480)


class ServiceCreate(ServiceBase):
    """Schema for creating a service."""

    clinic_id: UUID


class ServiceUpdate(BaseModel):
    """Schema for updating a service."""

    name: str | None = Field(None, min_length=2, max_length=200)
    code: str | None = None
    category: str | None = None
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    tax_rate: Decimal | None = Field(None, ge=0, le=100)
    duration_minutes: int | None = Field(None, ge=5, le=480)
    is_active: bool | None = None


class ServiceResponse(BaseModel):
    """Schema for service response."""

    id: UUID
    name: str
    code: str | None
    category: str | None
    description: str | None
    price: Decimal
    tax_rate: Decimal
    price_with_tax: Decimal
    duration_minutes: int
    clinic_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceListResponse(BaseModel):
    """Schema for listing services."""

    id: UUID
    name: str
    code: str | None
    category: str | None
    price: Decimal
    duration_minutes: int
    is_active: bool

    model_config = {"from_attributes": True}
