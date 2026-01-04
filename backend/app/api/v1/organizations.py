"""
Organization API endpoints for multi-location management.
"""

import re
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.models.organization import Organization
from app.schemas.organization import (
    OrganizationAddClinic,
    OrganizationCreate,
    OrganizationRemoveClinic,
    OrganizationResponse,
    OrganizationStats,
    OrganizationUpdate,
)
from app.services.multi_location import MultiLocationService

router = APIRouter()


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from organization name."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:100]


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    db: DbSession,
    current_user: CurrentAdmin,
    org_in: OrganizationCreate,
) -> Organization:
    """
    Create a new organization.

    Requires admin privileges. Creates the organization and sets up default roles.
    """
    service = MultiLocationService(db)

    # Generate slug if not provided
    slug = org_in.slug or generate_slug(org_in.name)

    try:
        org = await service.create_organization(
            name=org_in.name,
            slug=slug,
            owner_user_id=org_in.owner_user_id,
            description=org_in.description,
            email=org_in.email,
            phone=org_in.phone,
            website=org_in.website,
            subscription_tier=org_in.subscription_tier,
            max_clinics=org_in.max_clinics,
            max_users=org_in.max_users,
            logo_url=org_in.logo_url,
            primary_color=org_in.primary_color,
        )

        # Seed default roles for this organization
        await service.seed_default_roles(organization_id=org.id)

        # Reload to get clinic and user counts
        org = await service.get_organization(org.id)

        # Add computed fields
        org_response = OrganizationResponse.model_validate(org)
        org_response.clinic_count = len(org.clinics) if org.clinics else 0
        org_response.user_count = 0  # TODO: Count users across clinics

        return org_response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    db: DbSession,
    current_user: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: bool | None = None,
) -> list[OrganizationResponse]:
    """
    List all organizations.

    Requires admin privileges. Supports pagination and filtering by active status.
    """
    service = MultiLocationService(db)
    orgs = await service.list_organizations(skip=skip, limit=limit, is_active=is_active)

    responses = []
    for org in orgs:
        org_response = OrganizationResponse.model_validate(org)
        org_response.clinic_count = len(org.clinics) if org.clinics else 0
        org_response.user_count = 0  # TODO: Count users
        responses.append(org_response)

    return responses


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    db: DbSession,
    current_user: CurrentUser,
    org_id: UUID,
) -> OrganizationResponse:
    """
    Get organization by ID.

    Users can view organizations they belong to.
    """
    service = MultiLocationService(db)
    org = await service.get_organization(org_id)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check access (admins can view all, others only their own)
    from app.models.user import UserRole

    if current_user.role != UserRole.ADMIN.value:
        # Check if user belongs to this organization
        user_clinic_ids = [current_user.clinic_id] if current_user.clinic_id else []
        org_clinic_ids = [c.id for c in org.clinics] if org.clinics else []

        if not any(cid in org_clinic_ids for cid in user_clinic_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )

    org_response = OrganizationResponse.model_validate(org)
    org_response.clinic_count = len(org.clinics) if org.clinics else 0
    org_response.user_count = 0  # TODO: Count users

    return org_response


@router.get("/slug/{slug}", response_model=OrganizationResponse)
async def get_organization_by_slug(
    db: DbSession,
    current_user: CurrentUser,
    slug: str,
) -> OrganizationResponse:
    """
    Get organization by slug.

    Useful for public-facing URLs.
    """
    service = MultiLocationService(db)
    org = await service.get_organization_by_slug(slug)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    org_response = OrganizationResponse.model_validate(org)
    org_response.clinic_count = len(org.clinics) if org.clinics else 0
    org_response.user_count = 0

    return org_response


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    db: DbSession,
    current_user: CurrentAdmin,
    org_id: UUID,
    org_update: OrganizationUpdate,
) -> OrganizationResponse:
    """
    Update organization details.

    Requires admin privileges.
    """
    service = MultiLocationService(db)

    # Prepare updates (exclude None values)
    updates = org_update.model_dump(exclude_unset=True)

    org = await service.update_organization(org_id, **updates)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    org_response = OrganizationResponse.model_validate(org)
    org_response.clinic_count = len(org.clinics) if org.clinics else 0
    org_response.user_count = 0

    return org_response


@router.post("/{org_id}/clinics", status_code=status.HTTP_200_OK)
async def add_clinic_to_organization(
    db: DbSession,
    current_user: CurrentAdmin,
    org_id: UUID,
    clinic_data: OrganizationAddClinic,
) -> dict:
    """
    Add a clinic to an organization.

    Requires admin privileges. The clinic must not already belong to another organization.
    """
    service = MultiLocationService(db)

    try:
        await service.add_clinic_to_organization(org_id, clinic_data.clinic_id)
        return {"message": "Clinic added successfully", "clinic_id": str(clinic_data.clinic_id)}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{org_id}/clinics/{clinic_id}", status_code=status.HTTP_200_OK)
async def remove_clinic_from_organization(
    db: DbSession,
    current_user: CurrentAdmin,
    org_id: UUID,
    clinic_id: UUID,
) -> dict:
    """
    Remove a clinic from an organization.

    Requires admin privileges. The clinic will become standalone.
    """
    service = MultiLocationService(db)

    try:
        await service.remove_clinic_from_organization(org_id, clinic_id)
        return {"message": "Clinic removed successfully", "clinic_id": str(clinic_id)}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{org_id}/clinics")
async def get_organization_clinics(
    db: DbSession,
    current_user: CurrentUser,
    org_id: UUID,
):
    """
    Get all clinics in an organization.

    Users can view clinics in organizations they belong to.
    """
    service = MultiLocationService(db)

    # Verify access
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    from app.models.user import UserRole

    if current_user.role != UserRole.ADMIN.value:
        # Check if user belongs to this organization
        user_clinic_ids = [current_user.clinic_id] if current_user.clinic_id else []
        org_clinic_ids = [c.id for c in org.clinics] if org.clinics else []

        if not any(cid in org_clinic_ids for cid in user_clinic_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )

    clinics = await service.get_organization_clinics(org_id)

    from app.schemas.clinic import ClinicResponse

    return [ClinicResponse.model_validate(clinic) for clinic in clinics]


@router.get("/{org_id}/analytics", response_model=OrganizationStats)
async def get_organization_analytics(
    db: DbSession,
    current_user: CurrentUser,
    org_id: UUID,
) -> OrganizationStats:
    """
    Get consolidated analytics for an organization.

    Shows metrics across all clinics in the organization.
    """
    service = MultiLocationService(db)

    # Verify access
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    from app.models.user import UserRole

    if current_user.role != UserRole.ADMIN.value:
        # Check if user belongs to this organization
        user_clinic_ids = [current_user.clinic_id] if current_user.clinic_id else []
        org_clinic_ids = [c.id for c in org.clinics] if org.clinics else []

        if not any(cid in org_clinic_ids for cid in user_clinic_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization",
            )

    stats = await service.get_organization_stats(org_id)
    return stats
