"""
Invoice and InvoiceItem models for billing.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, generate_uuid, get_utc_now

if TYPE_CHECKING:
    from src.models.appointment import Appointment
    from src.models.patient import Patient
    from src.models.payment import Payment
    from src.models.service import Service


class InvoiceStatus(str, Enum):
    """Invoice status values."""

    DRAFT = "draft"
    PENDING = "pending"
    PARTIAL = "partial"  # Partially paid
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    """
    Invoice entity for billing.

    Attributes:
        id: Unique identifier (UUID)
        invoice_number: Human-readable invoice number
        patient_id: Reference to patient
        appointment_id: Reference to appointment (optional)
        subtotal: Total before tax and discounts
        tax_amount: Total tax
        discount_amount: Total discount
        total_amount: Final amount due
        status: Invoice status
        due_date: Payment due date
        notes: Additional notes
        created_at: Record creation timestamp
    """

    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Invoice Number (e.g., INV-2026-0001)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relationships
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=False, index=True
    )
    appointment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("appointments.id"), nullable=True
    )

    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    discount_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), default=InvoiceStatus.PENDING.value)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Additional Info
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )

    # ORM Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="invoices")
    appointment: Mapped[Optional["Appointment"]] = relationship(
        "Appointment", back_populates="invoices"
    )
    items: Mapped[list["InvoiceItem"]] = relationship(
        "InvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="invoice", lazy="dynamic"
    )

    @property
    def amount_paid(self) -> Decimal:
        """Calculate total amount paid."""
        return sum((p.amount for p in self.payments), Decimal("0.00"))

    @property
    def amount_due(self) -> Decimal:
        """Calculate remaining amount due."""
        return self.total_amount - self.amount_paid

    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.amount_due <= Decimal("0.00")

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.due_date and not self.is_paid:
            return date.today() > self.due_date
        return False

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, number={self.invoice_number}, total={self.total_amount})>"


class InvoiceItem(Base):
    """
    Invoice line item.

    Attributes:
        id: Unique identifier (UUID)
        invoice_id: Reference to parent invoice
        service_id: Reference to service (optional)
        description: Item description
        quantity: Number of items
        unit_price: Price per unit
        tax_rate: Tax rate for this item
        amount: Total amount for line item
    """

    __tablename__ = "invoice_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Parent Invoice
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False
    )

    # Service Reference (optional)
    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id"), nullable=True
    )

    # Item Details
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # ORM Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")
    service: Mapped[Optional["Service"]] = relationship("Service")

    @property
    def tax_amount(self) -> Decimal:
        """Calculate tax for this item."""
        return self.amount * (self.tax_rate / Decimal("100"))

    @property
    def amount_with_tax(self) -> Decimal:
        """Calculate amount including tax."""
        return self.amount + self.tax_amount

    def __repr__(self) -> str:
        return f"<InvoiceItem(id={self.id}, description={self.description}, amount={self.amount})>"
