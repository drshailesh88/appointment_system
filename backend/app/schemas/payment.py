"""
Payment schemas for transaction management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentBase(BaseModel):
    """Base payment schema."""

    invoice_id: UUID
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod = PaymentMethod.CASH
    payment_date: datetime
    notes: str | None = None


class PaymentCreate(PaymentBase):
    """Schema for creating a payment."""

    transaction_id: str | None = None
    receipt_number: str | None = None
    collected_by: str | None = None

    # UPI specific
    upi_transaction_id: str | None = None
    upi_vpa: str | None = None


class PaymentUpdate(BaseModel):
    """Schema for updating a payment."""

    status: PaymentStatus | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    """Schema for payment response."""

    id: UUID
    invoice_id: UUID
    amount: Decimal
    payment_method: str
    status: str
    transaction_id: str | None
    payment_gateway: str | None
    razorpay_payment_id: str | None
    razorpay_order_id: str | None
    upi_transaction_id: str | None
    upi_vpa: str | None
    payment_date: datetime
    notes: str | None
    receipt_number: str | None
    refund_amount: Decimal
    refund_reason: str | None
    refund_date: datetime | None
    net_amount: Decimal
    collected_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    """Schema for listing payments."""

    id: UUID
    invoice_id: UUID
    invoice_number: str | None = None
    amount: Decimal
    payment_method: str
    status: str
    payment_date: datetime
    receipt_number: str | None

    model_config = {"from_attributes": True}


class RefundRequest(BaseModel):
    """Schema for refund request."""

    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=5, max_length=500)


class RazorpayOrderRequest(BaseModel):
    """Schema for creating Razorpay order."""

    invoice_id: UUID
    amount: Decimal = Field(..., gt=0)


class RazorpayOrderResponse(BaseModel):
    """Schema for Razorpay order response."""

    order_id: str
    amount: int  # In paise
    currency: str
    receipt: str


class RazorpayVerifyRequest(BaseModel):
    """Schema for verifying Razorpay payment."""

    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    invoice_id: UUID


class PaymentSummary(BaseModel):
    """Schema for payment summary/stats."""

    total_collected: Decimal
    cash_collected: Decimal
    upi_collected: Decimal
    card_collected: Decimal
    pending_amount: Decimal
    refunded_amount: Decimal
    transaction_count: int
