"""
Invoice and InvoiceItem models for billing.
"""

import uuid
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, UUID

if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.doctor import Doctor
    from app.models.patient import Patient
    from app.models.payment import Payment
    from app.models.service import Service


class InvoiceStatus(str, Enum):
    """Invoice status types."""

    DRAFT = "draft"
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Invoice(BaseModel):
    """
    Invoice model for billing.

    Attributes:
        invoice_number: Unique invoice number (auto-generated)
        patient_id: Patient being billed
        doctor_id: Doctor who provided service
        clinic_id: Clinic issuing invoice
        subtotal: Total before tax
        tax_amount: Tax amount
        discount_amount: Discount applied
        total_amount: Final amount
        paid_amount: Amount paid so far
        status: Invoice status
        due_date: Payment due date
        notes: Invoice notes
    """

    __tablename__ = "invoices"

    # Invoice Number
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Relations
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(),
        ForeignKey("doctors.id"),
        nullable=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )

    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    discount_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=InvoiceStatus.DRAFT.value,
        index=True,
    )

    # Dates
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # GST Details (for Indian compliance)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    # Cancellation
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="invoices")
    doctor: Mapped["Doctor | None"] = relationship("Doctor")
    items: Mapped[list["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
    )

    @property
    def balance_due(self) -> Decimal:
        """Calculate remaining balance."""
        return self.total_amount - self.paid_amount

    @property
    def is_fully_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.paid_amount >= self.total_amount

    def calculate_totals(self) -> None:
        """Recalculate invoice totals from items."""
        self.subtotal = sum(item.total for item in self.items)
        self.tax_amount = sum(item.tax_amount for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number} (₹{self.total_amount})>"


class InvoiceItem(BaseModel):
    """
    Invoice line item.

    Attributes:
        invoice_id: Parent invoice
        service_id: Related service (optional)
        description: Item description
        quantity: Number of units
        unit_price: Price per unit
        tax_rate: Tax percentage
        total: Line total
    """

    __tablename__ = "invoice_items"

    # Relations
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(),
        ForeignKey("services.id"),
        nullable=True,
    )

    # Item Details
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Tax
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))

    # Calculated
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # HSN/SAC Code (for GST)
    hsn_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")
    service: Mapped["Service | None"] = relationship("Service", back_populates="invoice_items")

    def calculate_totals(self) -> None:
        """Calculate line item totals."""
        self.subtotal = self.unit_price * self.quantity
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount

    def __repr__(self) -> str:
        return f"<InvoiceItem {self.description} x{self.quantity}>"
