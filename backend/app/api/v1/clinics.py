"""
Clinics API endpoints.
"""

import re
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.models.clinic import Clinic
from app.models.user import UserRole
from app.schemas.clinic import (
    ClinicCreate,
    ClinicResponse,
    ClinicStats,
    ClinicUpdate,
)

router = APIRouter()


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from clinic name."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:100]


@router.post("/", response_model=ClinicResponse, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    db: DbSession,
    current_user: CurrentAdmin,
    clinic_in: ClinicCreate,
) -> Clinic:
    """Create a new clinic (admin only)."""
    # Generate slug if not provided
    slug = clinic_in.slug or generate_slug(clinic_in.name)

    # Check if slug exists
    result = await db.execute(select(Clinic).where(Clinic.slug == slug))
    if result.scalar_one_or_none():
        # Append number to make unique
        count = 1
        while True:
            new_slug = f"{slug}-{count}"
            result = await db.execute(select(Clinic).where(Clinic.slug == new_slug))
            if not result.scalar_one_or_none():
                slug = new_slug
                break
            count += 1

    clinic = Clinic(
        name=clinic_in.name,
        slug=slug,
        phone=clinic_in.phone,
        email=clinic_in.email,
        address=clinic_in.address,
        city=clinic_in.city,
        state=clinic_in.state,
        pincode=clinic_in.pincode,
        website=clinic_in.website,
        gst_number=clinic_in.gst_number,
        registration_number=clinic_in.registration_number,
        logo_url=clinic_in.logo_url,
        primary_color=clinic_in.primary_color,
        timezone=clinic_in.timezone,
        currency=clinic_in.currency,
    )
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)

    return clinic


@router.get("/", response_model=list[ClinicResponse])
async def list_clinics(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
) -> list[Clinic]:
    """List all clinics."""
    query = select(Clinic)

    if active_only:
        query = query.where(Clinic.is_active == True)

    # Non-admin users only see their own clinic
    if current_user.role != UserRole.ADMIN.value:
        if current_user.clinic_id:
            query = query.where(Clinic.id == current_user.clinic_id)
        else:
            return []

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{clinic_id}", response_model=ClinicResponse)
async def get_clinic(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID,
) -> Clinic:
    """Get a specific clinic."""
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()

    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )

    # Non-admin users can only see their own clinic
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return clinic


@router.get("/slug/{slug}", response_model=ClinicResponse)
async def get_clinic_by_slug(
    db: DbSession,
    slug: str,
) -> Clinic:
    """Get a clinic by its slug (public endpoint for booking)."""
    result = await db.execute(select(Clinic).where(Clinic.slug == slug))
    clinic = result.scalar_one_or_none()

    if not clinic or not clinic.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )

    return clinic


@router.patch("/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(
    db: DbSession,
    current_user: CurrentAdmin,
    clinic_id: UUID,
    clinic_in: ClinicUpdate,
) -> Clinic:
    """Update a clinic (admin only)."""
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()

    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )

    update_data = clinic_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clinic, field, value)

    await db.commit()
    await db.refresh(clinic)

    return clinic


@router.delete("/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinic(
    db: DbSession,
    current_user: CurrentAdmin,
    clinic_id: UUID,
) -> None:
    """Deactivate a clinic (admin only)."""
    result = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()

    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )

    clinic.is_active = False
    await db.commit()


@router.get("/{clinic_id}/stats", response_model=ClinicStats)
async def get_clinic_stats(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID,
) -> dict:
    """Get clinic statistics."""
    # Verify access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Import here to avoid circular imports
    from app.models.appointment import Appointment
    from app.models.doctor import Doctor
    from app.models.patient import Patient

    # Get counts
    patients_result = await db.execute(
        select(func.count(Patient.id)).where(Patient.clinic_id == clinic_id)
    )
    doctors_result = await db.execute(
        select(func.count(Doctor.id)).where(Doctor.clinic_id == clinic_id)
    )

    # Today's appointments would require more complex query
    # Simplified for now

    return {
        "total_patients": patients_result.scalar() or 0,
        "total_doctors": doctors_result.scalar() or 0,
        "total_appointments_today": 0,  # TODO: Implement
        "total_revenue_month": 0.0,  # TODO: Implement
        "pending_appointments": 0,  # TODO: Implement
    }
