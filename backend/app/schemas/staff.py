"""
Staff management schemas for role-based access control.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StaffRoleBase(BaseModel):
    """Base staff role schema."""

    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class StaffRoleCreate(StaffRoleBase):
    """Schema for creating a staff role."""

    organization_id: UUID | None = None
    is_system: bool = False

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        """Validate permission format."""
        valid_patterns = [
            r"^[a-z_]+\.[a-z_*]+$",  # e.g., appointments.view, appointments.*
            r"^\*$",  # Global admin
        ]
        import re

        for perm in v:
            if not any(re.match(pattern, perm) for pattern in valid_patterns):
                raise ValueError(
                    f"Invalid permission format: {perm}. "
                    f"Must be in format 'resource.action' or 'resource.*' or '*'"
                )
        return v


class StaffRoleUpdate(BaseModel):
    """Schema for updating a staff role."""

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None
    permissions: list[str] | None = None
    is_active: bool | None = None


class StaffRoleResponse(BaseModel):
    """Schema for staff role response."""

    id: UUID
    name: str
    description: str | None
    permissions: list[str]
    organization_id: UUID | None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StaffAssignmentBase(BaseModel):
    """Base staff assignment schema."""

    user_id: UUID
    clinic_id: UUID
    role_id: UUID
    is_primary_location: bool = False
    notes: str | None = None


class StaffAssignmentCreate(StaffAssignmentBase):
    """Schema for creating a staff assignment."""

    start_date: datetime | None = None  # Defaults to now


class StaffAssignmentUpdate(BaseModel):
    """Schema for updating a staff assignment."""

    role_id: UUID | None = None
    is_primary_location: bool | None = None
    end_date: datetime | None = None
    is_active: bool | None = None
    notes: str | None = None


class StaffAssignmentResponse(BaseModel):
    """Schema for staff assignment response."""

    id: UUID
    user_id: UUID
    clinic_id: UUID
    role_id: UUID
    is_primary_location: bool
    start_date: datetime
    end_date: datetime | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Nested data (when loaded)
    user_name: str | None = None
    clinic_name: str | None = None
    role_name: str | None = None

    model_config = {"from_attributes": True}


class StaffPerformanceMetrics(BaseModel):
    """Schema for staff performance metrics."""

    user_id: UUID
    user_name: str
    clinic_id: UUID
    clinic_name: str
    period_start: datetime
    period_end: datetime

    # Metrics
    total_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    total_revenue: float
    average_rating: float | None
    patients_seen: int


class PermissionCheckRequest(BaseModel):
    """Schema for checking if a user has a permission."""

    user_id: UUID
    clinic_id: UUID
    permission: str


class PermissionCheckResponse(BaseModel):
    """Schema for permission check response."""

    has_permission: bool
    role_name: str | None
    matched_permission: str | None  # The permission rule that matched


class StaffTransferRequest(BaseModel):
    """Schema for transferring staff between locations."""

    user_id: UUID
    from_clinic_id: UUID
    to_clinic_id: UUID
    role_id: UUID | None = None  # If None, keep same role
    make_primary: bool = False
    transfer_date: datetime | None = None
