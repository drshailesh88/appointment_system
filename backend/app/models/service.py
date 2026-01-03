"""
Service model for clinic services and procedures.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.clinic import Clinic
    from app.models.invoice import InvoiceItem


class Service(BaseModel):
    """
    Service model for clinic services/procedures.

    Attributes:
        name: Service name (e.g., "Blood Test", "X-Ray", "Dental Cleaning")
        category: Service category
        description: Detailed description
        price: Base price
        duration_minutes: How long the service takes
        clinic_id: Associated clinic
        is_active: Whether service is offered
    """

    __tablename__ = "services"

    # Basic Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))

    # Duration
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)

    # Clinic Association
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="services")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="service",
    )
    invoice_items: Mapped[list["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="service",
    )

    @property
    def price_with_tax(self) -> Decimal:
        """Calculate price including tax."""
        return self.price * (1 + self.tax_rate / 100)

    def __repr__(self) -> str:
        return f"<Service {self.name} (₹{self.price})>"
