"""
Patients API endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbSession
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientSearch,
    PatientUpdate,
)

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    db: DbSession,
    current_user: CurrentUser,
    patient_in: PatientCreate,
) -> Patient:
    """Create a new patient."""
    # Check access to clinic
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient_in.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this clinic",
        )

    # Check if patient with same phone exists in clinic
    result = await db.execute(
        select(Patient).where(
            Patient.clinic_id == patient_in.clinic_id,
            Patient.phone == patient_in.phone,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient with this phone number already exists",
        )

    patient = Patient(
        first_name=patient_in.first_name,
        last_name=patient_in.last_name,
        phone=patient_in.phone,
        email=patient_in.email,
        date_of_birth=patient_in.date_of_birth,
        gender=patient_in.gender,
        address=patient_in.address,
        city=patient_in.city,
        state=patient_in.state,
        pincode=patient_in.pincode,
        aadhaar_last_four=patient_in.aadhaar_last_four,
        blood_group=patient_in.blood_group,
        allergies=patient_in.allergies,
        emergency_contact_name=patient_in.emergency_contact_name,
        emergency_contact_phone=patient_in.emergency_contact_phone,
        preferred_language=patient_in.preferred_language,
        sms_consent=patient_in.sms_consent,
        whatsapp_consent=patient_in.whatsapp_consent,
        clinic_id=patient_in.clinic_id,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    return patient


@router.get("/", response_model=list[PatientListResponse])
async def list_patients(
    db: DbSession,
    current_user: CurrentUser,
    clinic_id: UUID | None = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> list[Patient]:
    """List patients with optional filters."""
    query = select(Patient)

    # Filter by clinic
    if clinic_id:
        if (
            current_user.role != UserRole.ADMIN.value
            and current_user.clinic_id != clinic_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clinic",
            )
        query = query.where(Patient.clinic_id == clinic_id)
    elif current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.where(Patient.clinic_id == current_user.clinic_id)

    if active_only:
        query = query.where(Patient.is_active == True)

    query = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)

    return list(result.scalars().all())


@router.get("/search", response_model=list[PatientListResponse])
async def search_patients(
    db: DbSession,
    current_user: CurrentUser,
    q: str,
    clinic_id: UUID | None = None,
    limit: int = 20,
) -> list[Patient]:
    """Search patients by name, phone, or email."""
    if len(q) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters",
        )

    query = select(Patient)

    # Filter by clinic
    if clinic_id:
        if (
            current_user.role != UserRole.ADMIN.value
            and current_user.clinic_id != clinic_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        query = query.where(Patient.clinic_id == clinic_id)
    elif current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.where(Patient.clinic_id == current_user.clinic_id)

    # Search in name, phone, email
    search_term = f"%{q}%"
    query = query.where(
        or_(
            Patient.first_name.ilike(search_term),
            Patient.last_name.ilike(search_term),
            Patient.phone.ilike(search_term),
            Patient.email.ilike(search_term),
        )
    )

    query = query.where(Patient.is_active == True).limit(limit)
    result = await db.execute(query)

    return list(result.scalars().all())


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID,
) -> Patient:
    """Get a specific patient."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return patient


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID,
    patient_in: PatientUpdate,
) -> Patient:
    """Update a patient."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    update_data = patient_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)

    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID,
) -> None:
    """Deactivate a patient (soft delete)."""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    patient.is_active = False
    await db.commit()


@router.get("/phone/{phone}", response_model=PatientResponse)
async def get_patient_by_phone(
    db: DbSession,
    current_user: CurrentUser,
    phone: str,
    clinic_id: UUID,
) -> Patient:
    """Find patient by phone number in a specific clinic."""
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Normalize phone
    phone = phone.replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+91" + phone[1:]
        else:
            phone = "+91" + phone

    result = await db.execute(
        select(Patient).where(
            Patient.clinic_id == clinic_id,
            Patient.phone == phone,
        )
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return patient
