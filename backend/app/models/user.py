"""
User model for authentication and staff management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.device_token import DeviceToken


class UserRole(str, Enum):
    """User role types."""

    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    BILLING = "billing"
    NURSE = "nurse"


class User(BaseModel):
    """
    User model for staff authentication.

    Attributes:
        email: Unique email address
        phone: Phone number (unique, used for OTP login)
        password_hash: Hashed password
        name: Full name
        role: User role (admin, doctor, receptionist, etc.)
        clinic_id: Associated clinic
        is_active: Account status
        is_verified: Email/phone verified
        last_login: Last login timestamp
    """

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(15), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.RECEPTIONIST.value)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Clinic Association
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=True,
    )

    # For doctors, link to doctor profile
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id"),
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Refresh token for JWT
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    clinic: Mapped["Clinic | None"] = relationship("Clinic", back_populates="users")
    device_tokens: Mapped[list["DeviceToken"]] = relationship(
        "DeviceToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
