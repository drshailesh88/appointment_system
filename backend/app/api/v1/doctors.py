"""
Doctors API endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.models.doctor import Doctor
from app.models.user import UserRole
from app.schemas.doctor import (
    DoctorCreate,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
)

router = APIRouter()


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    db: DbSession,
    current_user: CurrentAdmin,
    doctor_in: DoctorCreate,
) -> Doctor:
    """Create a new doctor (admin only)."""
    doctor = Doctor(
        name=doctor_in.name,
        specialization=doctor_in.specialization,
        qualification=doctor_in.qualification,
        registration_number=doctor_in.registration_number,
        experience_years=doctor_in.experience_years,
        phone=doctor_in.phone,
        email=doctor_in.email,
        clinic_id=doctor_in.clinic_id,
        consultation_fee=doctor_in.consultation_fee,
        followup_fee=doctor_in.followup_fee,
        slot_duration=doctor_in.slot_duration,
        working_hours=doctor_in.working_hours,
        break_slots=doctor_in.break_slots,
        bio=doctor_in.bio,
        photo_url=doctor_in.photo_url,
        languages=doctor_in.languages,
    )
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)

    return doctor


@router.get("/", response_model=list[DoctorListResponse])
async def list_doctors(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID | None = None,
    specialization: str | None = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[Doctor]:
    """List doctors with optional filters."""
    query = select(Doctor)

    # Filter by clinic
    if clinic_id:
        query = query.where(Doctor.clinic_id == clinic_id)
    elif current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.where(Doctor.clinic_id == current_user.clinic_id)

    if specialization:
        query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))

    if active_only:
        query = query.where(Doctor.is_active == True)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return list(result.scalars().all())


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: UUID,
) -> Doctor:
    """Get a specific doctor."""
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return doctor


@router.patch("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    db: DbSession,
    current_user: CurrentAdmin,
    doctor_id: UUID,
    doctor_in: DoctorUpdate,
) -> Doctor:
    """Update a doctor (admin only)."""
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    update_data = doctor_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)

    await db.commit()
    await db.refresh(doctor)

    return doctor


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    db: DbSession,
    current_user: CurrentAdmin,
    doctor_id: UUID,
) -> None:
    """Deactivate a doctor (admin only)."""
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    doctor.is_active = False
    await db.commit()


@router.get("/clinic/{clinic_id}/public", response_model=list[DoctorListResponse])
async def list_doctors_public(
    db: DbSession,
    clinic_id: UUID,
) -> list[Doctor]:
    """List active doctors for a clinic (public endpoint for booking)."""
    query = (
        select(Doctor)
        .where(Doctor.clinic_id == clinic_id)
        .where(Doctor.is_active == True)
        .where(Doctor.accepting_new_patients == True)
    )
    result = await db.execute(query)

    return list(result.scalars().all())
