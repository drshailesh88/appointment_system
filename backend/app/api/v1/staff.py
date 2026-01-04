"""
Staff Management API endpoints for role-based access control.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.schemas.staff import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    StaffAssignmentCreate,
    StaffAssignmentResponse,
    StaffAssignmentUpdate,
    StaffRoleCreate,
    StaffRoleResponse,
    StaffRoleUpdate,
    StaffTransferRequest,
)
from app.services.multi_location import MultiLocationService

router = APIRouter()


# ==================== Staff Roles ====================


@router.post("/roles", response_model=StaffRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_role(
    db: DbSession,
    current_user: CurrentAdmin,
    role_in: StaffRoleCreate,
) -> StaffRoleResponse:
    """
    Create a new staff role.

    Requires admin privileges. Defines a role with specific permissions.
    """
    service = MultiLocationService(db)

    try:
        role = await service.create_staff_role(
            name=role_in.name,
            permissions=role_in.permissions,
            organization_id=role_in.organization_id,
            description=role_in.description,
            is_system=role_in.is_system,
        )
        return StaffRoleResponse.model_validate(role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/roles", response_model=list[StaffRoleResponse])
async def list_staff_roles(
    db: DbSession,
    current_user: CurrentUser,
    organization_id: UUID | None = Query(None),
    include_system: bool = Query(True),
) -> list[StaffRoleResponse]:
    """
    List staff roles.

    Can filter by organization and optionally include system-wide roles.
    """
    service = MultiLocationService(db)
    roles = await service.list_staff_roles(
        organization_id=organization_id,
        include_system=include_system,
    )
    return [StaffRoleResponse.model_validate(role) for role in roles]


@router.get("/roles/{role_id}", response_model=StaffRoleResponse)
async def get_staff_role(
    db: DbSession,
    current_user: CurrentUser,
    role_id: UUID,
) -> StaffRoleResponse:
    """Get a specific staff role by ID."""
    service = MultiLocationService(db)
    role = await service.get_staff_role(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return StaffRoleResponse.model_validate(role)


@router.patch("/roles/{role_id}", response_model=StaffRoleResponse)
async def update_staff_role(
    db: DbSession,
    current_user: CurrentAdmin,
    role_id: UUID,
    role_update: StaffRoleUpdate,
) -> StaffRoleResponse:
    """
    Update a staff role.

    Requires admin privileges. Cannot modify system roles.
    """
    service = MultiLocationService(db)

    try:
        updates = role_update.model_dump(exclude_unset=True)
        role = await service.update_staff_role(role_id, **updates)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )

        return StaffRoleResponse.model_validate(role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_200_OK)
async def delete_staff_role(
    db: DbSession,
    current_user: CurrentAdmin,
    role_id: UUID,
) -> dict:
    """
    Delete a staff role.

    Requires admin privileges. Cannot delete system roles or roles in use.
    """
    service = MultiLocationService(db)

    try:
        success = await service.delete_staff_role(role_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )

        return {"message": "Role deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==================== Staff Assignments ====================


@router.post("/assignments", response_model=StaffAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_assignment(
    db: DbSession,
    current_user: CurrentAdmin,
    assignment_in: StaffAssignmentCreate,
) -> StaffAssignmentResponse:
    """
    Assign a staff member to a clinic with a role.

    Requires admin privileges.
    """
    service = MultiLocationService(db)

    try:
        assignment = await service.assign_staff(
            user_id=assignment_in.user_id,
            clinic_id=assignment_in.clinic_id,
            role_id=assignment_in.role_id,
            is_primary_location=assignment_in.is_primary_location,
            start_date=assignment_in.start_date,
            notes=assignment_in.notes,
        )

        # Enrich response with related data
        assignment_response = StaffAssignmentResponse.model_validate(assignment)
        if assignment.user:
            assignment_response.user_name = assignment.user.name
        if assignment.clinic:
            assignment_response.clinic_name = assignment.clinic.name
        if assignment.role:
            assignment_response.role_name = assignment.role.name

        return assignment_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/assignments/{assignment_id}", response_model=StaffAssignmentResponse)
async def get_staff_assignment(
    db: DbSession,
    current_user: CurrentUser,
    assignment_id: UUID,
) -> StaffAssignmentResponse:
    """Get a specific staff assignment."""
    service = MultiLocationService(db)
    assignment = await service.get_staff_assignment(assignment_id)

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    assignment_response = StaffAssignmentResponse.model_validate(assignment)
    if assignment.user:
        assignment_response.user_name = assignment.user.name
    if assignment.clinic:
        assignment_response.clinic_name = assignment.clinic.name
    if assignment.role:
        assignment_response.role_name = assignment.role.name

    return assignment_response


@router.patch("/assignments/{assignment_id}", response_model=StaffAssignmentResponse)
async def update_staff_assignment(
    db: DbSession,
    current_user: CurrentAdmin,
    assignment_id: UUID,
    assignment_update: StaffAssignmentUpdate,
) -> StaffAssignmentResponse:
    """
    Update a staff assignment.

    Requires admin privileges.
    """
    service = MultiLocationService(db)

    updates = assignment_update.model_dump(exclude_unset=True)
    assignment = await service.update_staff_assignment(assignment_id, **updates)

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    assignment_response = StaffAssignmentResponse.model_validate(assignment)
    if assignment.user:
        assignment_response.user_name = assignment.user.name
    if assignment.clinic:
        assignment_response.clinic_name = assignment.clinic.name
    if assignment.role:
        assignment_response.role_name = assignment.role.name

    return assignment_response


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_200_OK)
async def end_staff_assignment(
    db: DbSession,
    current_user: CurrentAdmin,
    assignment_id: UUID,
    end_date: datetime | None = None,
) -> dict:
    """
    End a staff assignment.

    Requires admin privileges. Sets end_date and marks as inactive.
    """
    service = MultiLocationService(db)

    success = await service.end_staff_assignment(assignment_id, end_date)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    return {"message": "Assignment ended successfully"}


@router.get("/users/{user_id}/assignments", response_model=list[StaffAssignmentResponse])
async def get_user_assignments(
    db: DbSession,
    current_user: CurrentUser,
    user_id: UUID,
    active_only: bool = Query(True),
) -> list[StaffAssignmentResponse]:
    """
    Get all assignments for a user.

    Users can view their own assignments. Admins can view any user's assignments.
    """
    from app.models.user import UserRole

    # Check access
    if current_user.role != UserRole.ADMIN.value and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    service = MultiLocationService(db)
    assignments = await service.get_user_assignments(user_id, active_only)

    responses = []
    for assignment in assignments:
        assignment_response = StaffAssignmentResponse.model_validate(assignment)
        if assignment.user:
            assignment_response.user_name = assignment.user.name
        if assignment.clinic:
            assignment_response.clinic_name = assignment.clinic.name
        if assignment.role:
            assignment_response.role_name = assignment.role.name
        responses.append(assignment_response)

    return responses


@router.get("/clinics/{clinic_id}/staff", response_model=list[StaffAssignmentResponse])
async def get_clinic_staff(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID,
    active_only: bool = Query(True),
) -> list[StaffAssignmentResponse]:
    """
    Get all staff assigned to a clinic.

    Users can view staff at their clinic. Admins can view any clinic's staff.
    """
    from app.models.user import UserRole

    # Check access
    if current_user.role != UserRole.ADMIN.value and current_user.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this clinic",
        )

    service = MultiLocationService(db)
    assignments = await service.get_clinic_staff(clinic_id, active_only)

    responses = []
    for assignment in assignments:
        assignment_response = StaffAssignmentResponse.model_validate(assignment)
        if assignment.user:
            assignment_response.user_name = assignment.user.name
        if assignment.clinic:
            assignment_response.clinic_name = assignment.clinic.name
        if assignment.role:
            assignment_response.role_name = assignment.role.name
        responses.append(assignment_response)

    return responses


@router.post("/transfer", response_model=StaffAssignmentResponse)
async def transfer_staff(
    db: DbSession,
    current_user: CurrentAdmin,
    transfer_request: StaffTransferRequest,
) -> StaffAssignmentResponse:
    """
    Transfer a staff member from one clinic to another.

    Requires admin privileges. Ends current assignment and creates new one.
    """
    service = MultiLocationService(db)

    try:
        assignment = await service.transfer_staff(
            user_id=transfer_request.user_id,
            from_clinic_id=transfer_request.from_clinic_id,
            to_clinic_id=transfer_request.to_clinic_id,
            role_id=transfer_request.role_id,
            make_primary=transfer_request.make_primary,
            transfer_date=transfer_request.transfer_date,
        )

        assignment_response = StaffAssignmentResponse.model_validate(assignment)
        if assignment.user:
            assignment_response.user_name = assignment.user.name
        if assignment.clinic:
            assignment_response.clinic_name = assignment.clinic.name
        if assignment.role:
            assignment_response.role_name = assignment.role.name

        return assignment_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==================== Permission Management ====================


@router.post("/permissions/check", response_model=PermissionCheckResponse)
async def check_permission(
    db: DbSession,
    current_user: CurrentUser,
    permission_request: PermissionCheckRequest,
) -> PermissionCheckResponse:
    """
    Check if a user has a specific permission at a clinic.

    Useful for frontend permission checks.
    """
    from app.models.user import UserRole

    # Only admins or the user themselves can check permissions
    if current_user.role != UserRole.ADMIN.value and current_user.id != permission_request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    service = MultiLocationService(db)
    has_permission, matched_perm = await service.check_permission(
        user_id=permission_request.user_id,
        clinic_id=permission_request.clinic_id,
        permission=permission_request.permission,
    )

    # Get role name if permission granted
    role_name = None
    if has_permission:
        assignments = await service.get_user_assignments(permission_request.user_id, active_only=True)
        for assignment in assignments:
            if assignment.clinic_id == permission_request.clinic_id:
                role_name = assignment.role.name if assignment.role else None
                break

    return PermissionCheckResponse(
        has_permission=has_permission,
        role_name=role_name,
        matched_permission=matched_perm,
    )


# ==================== Seed Default Roles ====================


@router.post("/roles/seed", status_code=status.HTTP_201_CREATED)
async def seed_default_roles(
    db: DbSession,
    current_user: CurrentAdmin,
    organization_id: UUID | None = Query(None),
) -> dict:
    """
    Seed default staff roles.

    Requires admin privileges. Creates system-wide or organization-specific default roles.
    """
    service = MultiLocationService(db)
    roles = await service.seed_default_roles(organization_id)

    return {
        "message": f"Created {len(roles)} default roles",
        "roles": [{"id": str(role.id), "name": role.name} for role in roles],
    }
