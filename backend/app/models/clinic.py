"""
Clinic model for multi-tenant support.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.patient import Patient
    from app.models.service import Service
    from app.models.user import User


class Clinic(BaseModel):
    """
    Clinic model for practice/organization.

    Supports multi-location practices with a single subscription.

    Attributes:
        name: Clinic name
        address: Full address
        city: City
        state: State
        pincode: Postal code
        phone: Contact number
        email: Contact email
        gst_number: GST registration (for invoicing)
        logo_url: Clinic logo
        subscription_tier: Current subscription plan
        is_active: Whether clinic is active
    """

    __tablename__ = "clinics"

    # Basic Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Address
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Contact
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Business Details
    gst_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), default="#1976D2")  # Hex color

    # Subscription
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free")
    subscription_expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Settings
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="clinic")
    doctors: Mapped[list["Doctor"]] = relationship("Doctor", back_populates="clinic")
    patients: Mapped[list["Patient"]] = relationship("Patient", back_populates="clinic")
    services: Mapped[list["Service"]] = relationship("Service", back_populates="clinic")

    def __repr__(self) -> str:
        return f"<Clinic {self.name}>"
