"""
Payment model for transaction tracking.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSONB, UUID


if TYPE_CHECKING:
    from app.models.invoice import Invoice


class PaymentMethod(str, Enum):
    """Payment method types."""

    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    CHEQUE = "cheque"
    INSURANCE = "insurance"


class PaymentStatus(str, Enum):
    """Payment status types."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class Payment(BaseModel):
    """
    Payment model for transaction tracking.

    Attributes:
        invoice_id: Related invoice
        amount: Payment amount
        payment_method: How payment was made
        status: Payment status
        transaction_id: External transaction ID (Razorpay, etc.)
        payment_date: When payment was made
        notes: Payment notes
        refund_amount: If partially/fully refunded
    """

    __tablename__ = "payments"

    # Relations
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("invoices.id"),
        nullable=False,
        index=True,
    )

    # Payment Details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(20),
        default=PaymentMethod.CASH.value,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=PaymentStatus.PENDING.value,
        index=True,
    )

    # Transaction Info
    transaction_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    payment_gateway: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Razorpay specific
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    razorpay_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # UPI specific
    upi_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    upi_vpa: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Dates
    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Refund
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    refund_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refund_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Gateway Response (for debugging)
    gateway_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Collected by
    collected_by: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")

    @property
    def net_amount(self) -> Decimal:
        """Calculate net amount after refunds."""
        return self.amount - self.refund_amount

    @property
    def is_refunded(self) -> bool:
        """Check if payment has any refund."""
        return self.refund_amount > 0

    def __repr__(self) -> str:
        return f"<Payment {self.id} ₹{self.amount} ({self.payment_method})>"
