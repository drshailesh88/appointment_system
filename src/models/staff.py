"""
Staff model for user management and access control.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, generate_uuid, get_utc_now


class StaffRole(str, Enum):
    """Predefined staff roles."""

    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    BILLING = "billing"
    NURSE = "nurse"


class Staff(Base):
    """
    Staff entity for access control.

    Attributes:
        id: Unique identifier (UUID)
        name: Staff member's full name
        role: Predefined or custom role
        phone: Contact number
        email: Email address
        username: Login username
        password_hash: Hashed password
        permissions: Custom permission overrides
        is_active: Whether account is active
        last_login: Last login timestamp
        created_at: Record creation timestamp
    """

    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Personal Info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Role and Permissions
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    permissions: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Authentication
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Doctor Reference (if staff is a doctor)
    doctor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=get_utc_now, nullable=False
    )

    def has_permission(self, permission: str) -> bool:
        """
        Check if staff has a specific permission.

        Args:
            permission: Permission key to check

        Returns:
            True if has permission, False otherwise
        """
        # Admin has all permissions
        if self.role == StaffRole.ADMIN.value:
            return True

        # Check custom permissions
        if self.permissions and permission in self.permissions:
            return bool(self.permissions[permission])

        # Default permissions by role
        role_permissions = {
            StaffRole.DOCTOR.value: [
                "view_patients",
                "view_appointments",
                "edit_appointments",
                "view_analytics",
            ],
            StaffRole.RECEPTIONIST.value: [
                "view_patients",
                "create_patients",
                "view_appointments",
                "create_appointments",
                "edit_appointments",
            ],
            StaffRole.BILLING.value: [
                "view_patients",
                "view_appointments",
                "create_invoices",
                "record_payments",
                "view_analytics",
            ],
            StaffRole.NURSE.value: [
                "view_patients",
                "view_appointments",
            ],
        }

        allowed = role_permissions.get(self.role, [])
        return permission in allowed

    def __repr__(self) -> str:
        return f"<Staff(id={self.id}, name={self.name}, role={self.role})>"
