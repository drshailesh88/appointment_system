"""
Service model - catalog of medical services offered.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, generate_uuid, get_utc_now


class Service(Base):
    """
    Medical service entity.

    Attributes:
        id: Unique identifier (UUID)
        name: Service name
        category: Service category (consultation, procedure, etc.)
        description: Detailed description
        duration: Default duration in minutes
        price: Service price
        tax_rate: GST rate (default 18%)
        is_active: Whether service is available
        created_at: Record creation timestamp
    """

    __tablename__ = "services"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Service Details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Service code

    # Duration and Pricing
    duration: Mapped[int] = mapped_column(Integer, default=15)  # minutes
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"))  # GST

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )

    @property
    def price_with_tax(self) -> Decimal:
        """Calculate price including tax."""
        tax_amount = self.price * (self.tax_rate / Decimal("100"))
        return self.price + tax_amount

    @property
    def tax_amount(self) -> Decimal:
        """Calculate tax amount."""
        return self.price * (self.tax_rate / Decimal("100"))

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name}, price={self.price})>"
