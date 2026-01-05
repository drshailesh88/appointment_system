"""
Staff management models for multi-location role-based access control.

Enables assigning staff to multiple locations with granular permissions.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSONB, UUID


if TYPE_CHECKING:
    from app.models.clinic import Clinic
    from app.models.organization import Organization
    from app.models.user import User


# Default permission sets for common roles
DEFAULT_PERMISSIONS = {
    "super_admin": [
        "organizations.*",
        "clinics.*",
        "users.*",
        "appointments.*",
        "patients.*",
        "billing.*",
        "reports.*",
        "settings.*",
    ],
    "clinic_admin": [
        "appointments.*",
        "patients.*",
        "billing.*",
        "reports.view",
        "staff.view",
        "settings.view",
    ],
    "doctor": [
        "appointments.view",
        "appointments.update",
        "appointments.complete",
        "patients.view",
        "patients.create",
        "patients.update",
        "procedures.view",
        "procedures.create",
        "documents.view",
        "documents.create",
    ],
    "receptionist": [
        "appointments.*",
        "patients.view",
        "patients.create",
        "patients.update",
        "billing.create",
        "billing.view",
        "waitlist.*",
    ],
    "billing_staff": [
        "billing.*",
        "patients.view",
        "invoices.*",
        "payments.*",
        "reports.billing",
    ],
    "nurse": [
        "appointments.view",
        "patients.view",
        "procedures.view",
        "procedures.assist",
        "documents.view",
    ],
}


class StaffRole(BaseModel):
    """
    Role definition with granular permissions.

    Enables custom role creation beyond the default UserRole enum.
    Supports organization-level role management.

    Attributes:
        name: Role name (e.g., "Senior Receptionist", "Lead Doctor")
        description: Role description
        permissions: List of permission strings (e.g., ["appointments.*", "patients.view"])
        organization_id: Organization this role belongs to (None = system-wide)
        is_system: Whether this is a built-in role (not deletable)
        is_active: Whether role is active
    """

    __tablename__ = "staff_roles"

    # Basic Info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Permissions (JSON array of permission strings)
    # e.g., ["appointments.view", "appointments.create", "patients.*"]
    permissions: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Organization (nullable for system-wide roles)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )

    # System flags
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # Built-in, non-deletable
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="staff_roles")
    assignments: Mapped[list["StaffAssignment"]] = relationship(
        "StaffAssignment",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    # Unique constraint: role name must be unique within organization
    __table_args__ = (UniqueConstraint("name", "organization_id", name="uq_role_name_org"),)

    def has_permission(self, permission: str) -> bool:
        """
        Check if role has a specific permission.

        Supports wildcards (e.g., "appointments.*" matches "appointments.view").

        Args:
            permission: Permission string to check

        Returns:
            True if role has permission
        """
        if not isinstance(self.permissions, list):
            return False

        # Check for exact match or wildcard
        for perm in self.permissions:
            if perm == permission:
                return True
            # Wildcard support (e.g., "appointments.*" covers all appointment permissions)
            if perm.endswith(".*"):
                prefix = perm[:-2]  # Remove ".*"
                if permission.startswith(f"{prefix}."):
                    return True
            # Global admin
            if perm == "*":
                return True

        return False

    def __repr__(self) -> str:
        return f"<StaffRole {self.name}>"


class StaffAssignment(BaseModel):
    """
    Assignment of a user to a clinic with a specific role.

    Enables staff to work at multiple locations with different roles.

    Attributes:
        user_id: Staff member being assigned
        clinic_id: Clinic/location being assigned to
        role_id: Role for this assignment
        is_primary_location: Whether this is the user's primary clinic
        start_date: Assignment start date
        end_date: Assignment end date (None = active)
        is_active: Whether assignment is currently active
    """

    __tablename__ = "staff_assignments"

    # Assignment
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("staff_roles.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Location preference
    is_primary_location: Mapped[bool] = mapped_column(Boolean, default=False)

    # Employment period
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Additional details
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    clinic: Mapped["Clinic"] = relationship("Clinic", foreign_keys=[clinic_id])
    role: Mapped["StaffRole"] = relationship("StaffRole", back_populates="assignments")

    # Unique constraint: user can only have one active assignment per clinic
    __table_args__ = (UniqueConstraint("user_id", "clinic_id", "is_active", name="uq_user_clinic_active"),)

    def __repr__(self) -> str:
        return f"<StaffAssignment user={self.user_id} clinic={self.clinic_id}>"
