"""
Organization model for multi-location practice management.

An Organization is a parent entity that can own multiple Clinics,
enabling hospital chains and multi-location practices.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.models.base import BaseModel, UUID

if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.user import User
    from app.models.staff import StaffRole


class Organization(BaseModel):
    """
    Organization model for multi-location practice groups.

    Represents a parent entity (e.g., hospital chain, clinic network)
    that can manage multiple clinics/branches under one umbrella.

    Attributes:
        name: Organization name (e.g., "Apollo Hospitals", "HealthCare Plus")
        slug: URL-friendly unique identifier
        owner_user_id: Primary owner/admin user
        subscription_tier: Plan level (free, basic, premium, enterprise)
        max_clinics: Maximum number of clinics allowed
        max_users: Maximum staff/users allowed
        logo_url: Organization logo
        primary_color: Brand color (hex)
        is_active: Whether organization is active
        settings: JSON settings for org-wide preferences
    """

    __tablename__ = "organizations"

    # Basic Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Owner
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Subscription & Limits
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free")
    subscription_expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_clinics: Mapped[int] = mapped_column(Integer, default=1)
    max_users: Mapped[int] = mapped_column(Integer, default=5)

    # Branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), default="#1976D2")  # Hex color

    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    clinics: Mapped[list["Clinic"]] = relationship(
        "Clinic",
        back_populates="organization",
        foreign_keys="Clinic.organization_id",
    )
    staff_roles: Mapped[list["StaffRole"]] = relationship(
        "StaffRole",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"
