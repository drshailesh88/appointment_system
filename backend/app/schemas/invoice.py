"""
Invoice schemas for billing.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.invoice import InvoiceStatus


class InvoiceItemBase(BaseModel):
    """Base invoice item schema."""

    description: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    hsn_code: str | None = Field(None, max_length=10)


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating an invoice item."""

    service_id: UUID | None = None


class InvoiceItemUpdate(BaseModel):
    """Schema for updating an invoice item."""

    description: str | None = Field(None, min_length=1, max_length=500)
    quantity: int | None = Field(None, ge=1)
    unit_price: Decimal | None = Field(None, ge=0)
    tax_rate: Decimal | None = Field(None, ge=0, le=100)
    hsn_code: str | None = None


class InvoiceItemResponse(BaseModel):
    """Schema for invoice item response."""

    id: UUID
    invoice_id: UUID
    service_id: UUID | None
    description: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    hsn_code: str | None

    model_config = {"from_attributes": True}


class InvoiceBase(BaseModel):
    """Base invoice schema."""

    patient_id: UUID
    doctor_id: UUID | None = None
    invoice_date: date
    due_date: date | None = None
    notes: str | None = None


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice."""

    clinic_id: UUID
    items: list[InvoiceItemCreate] = Field(..., min_length=1)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    discount_reason: str | None = None
    gstin: str | None = Field(None, max_length=20)


class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice."""

    status: InvoiceStatus | None = None
    due_date: date | None = None
    notes: str | None = None
    discount_amount: Decimal | None = Field(None, ge=0)
    discount_reason: str | None = None


class InvoiceResponse(BaseModel):
    """Schema for invoice response."""

    id: UUID
    invoice_number: str
    patient_id: UUID
    doctor_id: UUID | None
    clinic_id: UUID
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    discount_reason: str | None
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    status: str
    invoice_date: date
    due_date: date | None
    notes: str | None
    gstin: str | None
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    is_cancelled: bool
    cancellation_reason: str | None
    items: list[InvoiceItemResponse]
    created_at: datetime
    updated_at: datetime

    # Nested details (populated when needed)
    patient_name: str | None = None
    doctor_name: str | None = None

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    """Schema for listing invoices."""

    id: UUID
    invoice_number: str
    patient_id: UUID
    patient_name: str
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    status: str
    invoice_date: date
    due_date: date | None

    model_config = {"from_attributes": True}


class InvoiceSummary(BaseModel):
    """Schema for invoice summary/stats."""

    total_invoices: int
    total_amount: Decimal
    paid_amount: Decimal
    pending_amount: Decimal
    overdue_count: int
