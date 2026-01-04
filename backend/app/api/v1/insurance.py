"""
Insurance API endpoints.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession
from app.integrations.insurance_verification import (
    INDIAN_INSURANCE_PROVIDERS,
    INDIAN_TPAS,
    get_insurance_service,
)
from app.models.insurance import (
    InsuranceVerification,
    PatientInsurance,
)
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.insurance import (
    InsuranceInfoCreate,
    InsuranceInfoResponse,
    InsuranceInfoUpdate,
    InsuranceListItem,
    InsuranceProvider,
    InsuranceProviderList,
    PatientInsuranceList,
    VerificationRequest,
    VerificationResult,
)

router = APIRouter()


# ==================
# Insurance Info Endpoints
# ==================


@router.post("/", response_model=InsuranceInfoResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance(
    db: DbSession,
    current_user: CurrentUser,
    insurance_in: InsuranceInfoCreate,
) -> PatientInsurance:
    """Create insurance information for a patient."""
    # Verify patient exists and user has access
    result = await db.execute(
        select(Patient).where(Patient.id == insurance_in.patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this patient",
        )

    # Check if primary insurance already exists if this is being set as primary
    if insurance_in.is_primary:
        result = await db.execute(
            select(PatientInsurance).where(
                PatientInsurance.patient_id == insurance_in.patient_id,
                PatientInsurance.is_primary == True,
                PatientInsurance.is_active == True,
            )
        )
        existing_primary = result.scalar_one_or_none()
        if existing_primary:
            # Make existing primary secondary
            existing_primary.is_primary = False

    insurance = PatientInsurance(
        patient_id=insurance_in.patient_id,
        provider_name=insurance_in.provider_name,
        policy_number=insurance_in.policy_number,
        group_number=insurance_in.group_number,
        insurance_type=insurance_in.insurance_type,
        plan_name=insurance_in.plan_name,
        coverage_start_date=insurance_in.coverage_start_date,
        coverage_end_date=insurance_in.coverage_end_date,
        is_primary=insurance_in.is_primary,
        subscriber_name=insurance_in.subscriber_name,
        subscriber_relationship=insurance_in.subscriber_relationship,
        tpa_name=insurance_in.tpa_name,
        tpa_id=insurance_in.tpa_id,
        cashless_enabled=insurance_in.cashless_enabled,
        network_type=insurance_in.network_type,
        copay_amount=insurance_in.copay_amount,
        deductible_amount=insurance_in.deductible_amount,
        out_of_pocket_max=insurance_in.out_of_pocket_max,
        additional_info=insurance_in.additional_info,
    )

    db.add(insurance)
    await db.commit()
    await db.refresh(insurance)

    return insurance


@router.get("/patient/{patient_id}", response_model=PatientInsuranceList)
async def get_patient_insurance(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID,
    active_only: bool = True,
) -> PatientInsuranceList:
    """Get all insurance policies for a patient."""
    # Verify patient exists and user has access
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get insurance policies
    query = select(PatientInsurance).where(PatientInsurance.patient_id == patient_id)

    if active_only:
        query = query.where(PatientInsurance.is_active == True)

    query = query.order_by(
        PatientInsurance.is_primary.desc(),
        PatientInsurance.created_at.desc(),
    )

    result = await db.execute(query)
    insurances = list(result.scalars().all())

    # Get last verification date for each
    insurance_list = []
    for insurance in insurances:
        # Get most recent verification
        ver_result = await db.execute(
            select(InsuranceVerification)
            .where(InsuranceVerification.insurance_id == insurance.id)
            .order_by(InsuranceVerification.verified_at.desc())
            .limit(1)
        )
        last_verification = ver_result.scalar_one_or_none()

        insurance_list.append(
            InsuranceListItem(
                id=insurance.id,
                provider_name=insurance.provider_name,
                policy_number=insurance.policy_number,
                insurance_type=insurance.insurance_type,
                is_primary=insurance.is_primary,
                is_active=insurance.is_active,
                coverage_end_date=insurance.coverage_end_date,
                last_verified=last_verification.verified_at if last_verification else None,
            )
        )

    return PatientInsuranceList(patient_id=patient_id, insurances=insurance_list)


@router.get("/{insurance_id}", response_model=InsuranceInfoResponse)
async def get_insurance(
    db: DbSession,
    current_user: CurrentUser,
    insurance_id: UUID,
) -> PatientInsurance:
    """Get insurance details."""
    result = await db.execute(
        select(PatientInsurance)
        .options(joinedload(PatientInsurance.patient))
        .where(PatientInsurance.id == insurance_id)
    )
    insurance = result.scalar_one_or_none()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != insurance.patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return insurance


@router.put("/{insurance_id}", response_model=InsuranceInfoResponse)
async def update_insurance(
    db: DbSession,
    current_user: CurrentUser,
    insurance_id: UUID,
    insurance_in: InsuranceInfoUpdate,
) -> PatientInsurance:
    """Update insurance information."""
    result = await db.execute(
        select(PatientInsurance)
        .options(joinedload(PatientInsurance.patient))
        .where(PatientInsurance.id == insurance_id)
    )
    insurance = result.scalar_one_or_none()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != insurance.patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # If setting as primary, unset other primary insurances
    if insurance_in.is_primary and not insurance.is_primary:
        result = await db.execute(
            select(PatientInsurance).where(
                PatientInsurance.patient_id == insurance.patient_id,
                PatientInsurance.is_primary == True,
                PatientInsurance.is_active == True,
                PatientInsurance.id != insurance_id,
            )
        )
        existing_primary = result.scalar_one_or_none()
        if existing_primary:
            existing_primary.is_primary = False

    # Update fields
    update_data = insurance_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(insurance, field, value)

    await db.commit()
    await db.refresh(insurance)

    return insurance


@router.delete("/{insurance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurance(
    db: DbSession,
    current_user: CurrentUser,
    insurance_id: UUID,
):
    """Delete (deactivate) insurance information."""
    result = await db.execute(
        select(PatientInsurance)
        .options(joinedload(PatientInsurance.patient))
        .where(PatientInsurance.id == insurance_id)
    )
    insurance = result.scalar_one_or_none()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != insurance.patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Soft delete
    insurance.is_active = False
    await db.commit()


# ==================
# Verification Endpoints
# ==================


@router.post("/verify", response_model=VerificationResult)
async def verify_insurance(
    db: DbSession,
    current_user: CurrentUser,
    verification_req: VerificationRequest,
) -> VerificationResult:
    """Verify patient insurance eligibility."""
    # Get insurance info
    result = await db.execute(
        select(PatientInsurance)
        .options(joinedload(PatientInsurance.patient))
        .where(PatientInsurance.id == verification_req.insurance_id)
    )
    insurance = result.scalar_one_or_none()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != insurance.patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Check for recent verification if not forcing refresh
    if not verification_req.force_refresh:
        result = await db.execute(
            select(InsuranceVerification)
            .where(
                InsuranceVerification.insurance_id == verification_req.insurance_id,
                InsuranceVerification.status == "success",
                InsuranceVerification.expires_at > datetime.now(timezone.utc),
            )
            .order_by(InsuranceVerification.verified_at.desc())
            .limit(1)
        )
        cached_verification = result.scalar_one_or_none()

        if cached_verification:
            # Return cached result
            return VerificationResult.model_validate(cached_verification)

    # Get patient DOB
    patient = insurance.patient
    if not patient.date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient date of birth required for verification",
        )

    # Build additional info
    additional_info = insurance.additional_info or {}
    if insurance.group_number:
        additional_info["group_number"] = insurance.group_number
    if insurance.tpa_id:
        additional_info["tpa_id"] = insurance.tpa_id
    if insurance.tpa_name:
        additional_info["tpa_name"] = insurance.tpa_name

    # Perform verification
    verification_service = get_insurance_service()
    result = await verification_service.verify_eligibility(
        policy_number=insurance.policy_number,
        provider_name=insurance.provider_name,
        patient_dob=patient.date_of_birth,
        service_date=verification_req.service_date,
        procedure_codes=verification_req.procedure_codes,
        additional_info=additional_info,
    )

    # Save verification result
    verification = InsuranceVerification(
        insurance_id=insurance.id,
        verified_at=datetime.now(timezone.utc),
        verified_by=str(current_user.id),
        status=result.status.value,
        is_eligible=result.is_eligible,
        eligibility_start_date=result.eligibility_start_date,
        eligibility_end_date=result.eligibility_end_date,
        coverage_details=result.coverage_details,
        copay_info=result.copay_info,
        deductible_info=result.deductible_info,
        benefits=result.benefits,
        limitations=result.limitations,
        error_message=result.error_message,
        provider_response=result.provider_response,
        expires_at=result.expires_at,
    )

    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    return VerificationResult.model_validate(verification)


@router.get("/verification/{verification_id}", response_model=VerificationResult)
async def get_verification(
    db: DbSession,
    current_user: CurrentUser,
    verification_id: UUID,
) -> VerificationResult:
    """Get verification details."""
    result = await db.execute(
        select(InsuranceVerification)
        .options(
            joinedload(InsuranceVerification.insurance).joinedload(
                PatientInsurance.patient
            )
        )
        .where(InsuranceVerification.id == verification_id)
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found",
        )

    # Check access
    patient = verification.insurance.patient
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return VerificationResult.model_validate(verification)


@router.get("/verification/history/{insurance_id}", response_model=list[VerificationResult])
async def get_verification_history(
    db: DbSession,
    current_user: CurrentUser,
    insurance_id: UUID,
    limit: int = 10,
) -> list[VerificationResult]:
    """Get verification history for an insurance policy."""
    # Verify access to insurance
    result = await db.execute(
        select(PatientInsurance)
        .options(joinedload(PatientInsurance.patient))
        .where(PatientInsurance.id == insurance_id)
    )
    insurance = result.scalar_one_or_none()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance not found",
        )

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != insurance.patient.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get verification history
    result = await db.execute(
        select(InsuranceVerification)
        .where(InsuranceVerification.insurance_id == insurance_id)
        .order_by(InsuranceVerification.verified_at.desc())
        .limit(limit)
    )
    verifications = list(result.scalars().all())

    return [VerificationResult.model_validate(v) for v in verifications]


# ==================
# Provider List
# ==================


@router.get("/providers/list", response_model=InsuranceProviderList)
async def list_providers(
    current_user: CurrentUser,
    country: str = "IN",
) -> InsuranceProviderList:
    """Get list of supported insurance providers."""
    if country.upper() == "IN":
        providers = [InsuranceProvider(**p) for p in INDIAN_INSURANCE_PROVIDERS]
    else:
        providers = []

    return InsuranceProviderList(providers=providers)


@router.get("/providers/tpas", response_model=list[dict])
async def list_tpas(
    current_user: CurrentUser,
    country: str = "IN",
) -> list[dict]:
    """Get list of common TPAs (Third-Party Administrators)."""
    if country.upper() == "IN":
        return INDIAN_TPAS
    else:
        return []
