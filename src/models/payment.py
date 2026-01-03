"""
Payment model for tracking payments.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, generate_uuid, get_utc_now

if TYPE_CHECKING:
    from src.models.invoice import Invoice


class PaymentMode(str, Enum):
    """Payment mode values."""

    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    CHEQUE = "cheque"
    INSURANCE = "insurance"


class Payment(Base):
    """
    Payment entity for tracking payments.

    Attributes:
        id: Unique identifier (UUID)
        invoice_id: Reference to invoice
        amount: Payment amount
        payment_mode: Method of payment
        payment_reference: Transaction ID or reference
        payment_date: When payment was received
        notes: Additional notes
        created_by: Staff who recorded the payment
    """

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Invoice Reference
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False, index=True
    )

    # Payment Details
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timing
    payment_date: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )

    # Additional Info
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # ORM Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, mode={self.payment_mode})>"
