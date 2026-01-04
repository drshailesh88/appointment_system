"""
Insurance API endpoints for companies, patient insurance, claims, and pre-authorizations.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.insurance import (
    ClaimStatus,
    InsuranceClaim,
    InsuranceCompany,
    PatientInsurance,
    PreAuthStatus,
    PreAuthorization,
)
from app.models.invoice import Invoice
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.insurance import (
    ClaimSummary,
    InsuranceClaimCreate,
    InsuranceClaimListResponse,
    InsuranceClaimResponse,
    InsuranceClaimSubmit,
    InsuranceClaimUpdate,
    InsuranceCompanyCreate,
    InsuranceCompanyListResponse,
    InsuranceCompanyResponse,
    InsuranceCompanyUpdate,
    PatientInsuranceCreate,
    PatientInsuranceListResponse,
    PatientInsuranceResponse,
    PatientInsuranceUpdate,
    PreAuthorizationCreate,
    PreAuthorizationListResponse,
    PreAuthorizationResponse,
    PreAuthorizationSubmit,
    PreAuthorizationUpdate,
    PreAuthSummary,
)
from app.services.insurance_claims import InsuranceClaimsService

router = APIRouter()


# ============= Insurance Company Endpoints =============

@router.post("/companies", response_model=InsuranceCompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance_company(
    db: DbSession,
    current_user: CurrentUser,
    company_in: InsuranceCompanyCreate,
) -> InsuranceCompany:
    """Create a new insurance company (admin only)."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create insurance companies",
        )

    # Check for duplicate code
    result = await db.execute(
        select(InsuranceCompany).where(InsuranceCompany.code == company_in.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insurance company with code {company_in.code} already exists",
        )

    company = InsuranceCompany(**company_in.model_dump())
    db.add(company)
    await db.commit()
    await db.refresh(company)

    return company


@router.get("/companies", response_model=list[InsuranceCompanyListResponse])
async def list_insurance_companies(
    db: DbSession,
    current_user: CurrentUser,
    active_only: bool = Query(True, description="Show only active companies"),
    skip: int = 0,
    limit: int = 100,
) -> list[InsuranceCompany]:
    """List all insurance companies."""
    query = select(InsuranceCompany)

    if active_only:
        query = query.where(InsuranceCompany.is_active == True)

    query = query.order_by(InsuranceCompany.name).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/companies/{company_id}", response_model=InsuranceCompanyResponse)
async def get_insurance_company(
    db: DbSession,
    current_user: CurrentUser,
    company_id: UUID,
) -> InsuranceCompany:
    """Get insurance company details."""
    result = await db.execute(
        select(InsuranceCompany).where(InsuranceCompany.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance company not found",
        )

    return company


@router.patch("/companies/{company_id}", response_model=InsuranceCompanyResponse)
async def update_insurance_company(
    db: DbSession,
    current_user: CurrentUser,
    company_id: UUID,
    company_in: InsuranceCompanyUpdate,
) -> InsuranceCompany:
    """Update insurance company (admin only)."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update insurance companies",
        )

    result = await db.execute(
        select(InsuranceCompany).where(InsuranceCompany.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance company not found",
        )

    update_data = company_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)

    return company


# ============= Patient Insurance Endpoints =============

@router.post("/patient-insurance", response_model=PatientInsuranceResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_insurance(
    db: DbSession,
    current_user: CurrentUser,
    insurance_in: PatientInsuranceCreate,
) -> PatientInsurance:
    """Create patient insurance record."""
    # Verify patient exists
    result = await db.execute(
        select(Patient).where(Patient.id == insurance_in.patient_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Verify insurance company exists
    result = await db.execute(
        select(InsuranceCompany).where(InsuranceCompany.id == insurance_in.insurance_company_id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance company not found",
        )

    insurance = PatientInsurance(**insurance_in.model_dump())
    db.add(insurance)
    await db.commit()
    await db.refresh(insurance)

    return insurance


@router.get("/patient-insurance", response_model=list[PatientInsuranceListResponse])
async def list_patient_insurance(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID | None = None,
    active_only: bool = Query(True, description="Show only active policies"),
    valid_only: bool = Query(False, description="Show only currently valid policies"),
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List patient insurance policies."""
    query = select(PatientInsurance).options(
        selectinload(PatientInsurance.insurance_company),
        selectinload(PatientInsurance.patient),
    )

    if patient_id:
        query = query.where(PatientInsurance.patient_id == patient_id)

    if active_only:
        query = query.where(PatientInsurance.is_active == True)

    if valid_only:
        today = date.today()
        query = query.where(
            PatientInsurance.valid_from <= today,
            PatientInsurance.valid_to >= today,
            PatientInsurance.is_active == True,
        )

    query = query.order_by(PatientInsurance.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    insurances = result.scalars().all()

    return [
        {
            "id": ins.id,
            "patient_id": ins.patient_id,
            "insurance_company_id": ins.insurance_company_id,
            "insurance_company_name": ins.insurance_company.name,
            "policy_number": ins.policy_number,
            "valid_from": ins.valid_from,
            "valid_to": ins.valid_to,
            "is_active": ins.is_active,
            "is_valid": ins.is_valid,
        }
        for ins in insurances
    ]


@router.get("/patient-insurance/{insurance_id}", response_model=PatientInsuranceResponse)
async def get_patient_insurance(
    db: DbSession,
    current_user: CurrentUser,
    insurance_id: UUID,
) -> dict:
    """Get patient insurance details."""
    result = await db.execute(
        select(PatientInsurance)
        .options(
            selectinload(PatientInsurance.insurance_company),
            selectinload(PatientInsurance.patient),
        )
        .where(PatientInsurance.id == insurance_id)
    )
    insurance = result.scalar_one_or_none()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient insurance not found",
        )

    return {
        **insurance.__dict__,
        "insurance_company_name": insurance.insurance_company.name,
        "patient_name": insurance.patient.full_name,
        "is_valid": insurance.is_valid,
    }


@router.patch("/patient-insurance/{insurance_id}", response_model=PatientInsuranceResponse)
async def update_patient_insurance(
    db: DbSession,
    current_user: CurrentUser,
    insurance_id: UUID,
    insurance_in: PatientInsuranceUpdate,
) -> PatientInsurance:
    """Update patient insurance."""
    result = await db.execute(
        select(PatientInsurance).where(PatientInsurance.id == insurance_id)
    )
    insurance = result.scalar_one_or_none()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient insurance not found",
        )

    update_data = insurance_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "coverage_type" and value:
            setattr(insurance, field, value.value)
        else:
            setattr(insurance, field, value)

    await db.commit()
    await db.refresh(insurance)

    return insurance


# ============= Insurance Claims Endpoints =============

@router.post("/claims", response_model=InsuranceClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance_claim(
    db: DbSession,
    current_user: CurrentUser,
    claim_in: InsuranceClaimCreate,
) -> dict:
    """Create a new insurance claim."""
    service = InsuranceClaimsService(db)

    try:
        claim = await service.create_claim(
            patient_id=claim_in.patient_id,
            invoice_id=claim_in.invoice_id,
            patient_insurance_id=claim_in.patient_insurance_id,
            claimed_amount=claim_in.claimed_amount,
            preauthorization_id=claim_in.preauthorization_id,
            documents=claim_in.documents_submitted,
            notes=claim_in.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Load relationships for response
    await db.refresh(claim)
    result = await db.execute(
        select(InsuranceClaim)
        .options(
            selectinload(InsuranceClaim.patient),
            selectinload(InsuranceClaim.insurance_company),
            selectinload(InsuranceClaim.invoice),
        )
        .where(InsuranceClaim.id == claim.id)
    )
    claim = result.scalar_one()

    return {
        **claim.__dict__,
        "patient_name": claim.patient.full_name,
        "insurance_company_name": claim.insurance_company.name,
        "invoice_number": claim.invoice.invoice_number,
        "rejection_amount": claim.rejection_amount,
    }


@router.post("/claims/{claim_id}/submit", response_model=InsuranceClaimResponse)
async def submit_insurance_claim(
    db: DbSession,
    current_user: CurrentUser,
    claim_id: UUID,
    submit_data: InsuranceClaimSubmit | None = None,
) -> dict:
    """Submit claim to insurance/TPA."""
    service = InsuranceClaimsService(db)

    try:
        claim = await service.submit_claim(
            claim_id=claim_id,
            documents=submit_data.documents_submitted if submit_data else None,
            submitted_by=submit_data.submitted_by if submit_data else current_user.username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Load relationships
    result = await db.execute(
        select(InsuranceClaim)
        .options(
            selectinload(InsuranceClaim.patient),
            selectinload(InsuranceClaim.insurance_company),
            selectinload(InsuranceClaim.invoice),
        )
        .where(InsuranceClaim.id == claim.id)
    )
    claim = result.scalar_one()

    return {
        **claim.__dict__,
        "patient_name": claim.patient.full_name,
        "insurance_company_name": claim.insurance_company.name,
        "invoice_number": claim.invoice.invoice_number,
        "rejection_amount": claim.rejection_amount,
    }


@router.patch("/claims/{claim_id}", response_model=InsuranceClaimResponse)
async def update_insurance_claim(
    db: DbSession,
    current_user: CurrentUser,
    claim_id: UUID,
    claim_in: InsuranceClaimUpdate,
) -> dict:
    """Update claim status and details."""
    service = InsuranceClaimsService(db)

    update_data = claim_in.model_dump(exclude_unset=True)

    # If status is being updated, use service method
    if "status" in update_data:
        try:
            claim = await service.update_claim_status(
                claim_id=claim_id,
                status=update_data["status"],
                approved_amount=update_data.get("approved_amount"),
                settled_amount=update_data.get("settled_amount"),
                claim_number=update_data.get("claim_number"),
                rejection_reason=update_data.get("rejection_reason"),
                rejection_code=update_data.get("rejection_code"),
                tpa_reference=update_data.get("tpa_reference_number"),
                notes=update_data.get("processing_notes"),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    else:
        # Simple update
        result = await db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claim not found",
            )

        for field, value in update_data.items():
            setattr(claim, field, value)

        await db.commit()
        await db.refresh(claim)

    # Load relationships
    result = await db.execute(
        select(InsuranceClaim)
        .options(
            selectinload(InsuranceClaim.patient),
            selectinload(InsuranceClaim.insurance_company),
            selectinload(InsuranceClaim.invoice),
        )
        .where(InsuranceClaim.id == claim.id)
    )
    claim = result.scalar_one()

    return {
        **claim.__dict__,
        "patient_name": claim.patient.full_name,
        "insurance_company_name": claim.insurance_company.name,
        "invoice_number": claim.invoice.invoice_number,
        "rejection_amount": claim.rejection_amount,
    }


@router.get("/claims", response_model=list[InsuranceClaimListResponse])
async def list_insurance_claims(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID | None = None,
    insurance_company_id: UUID | None = None,
    status_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List insurance claims with filters."""
    query = select(InsuranceClaim).options(
        selectinload(InsuranceClaim.patient),
        selectinload(InsuranceClaim.insurance_company),
        selectinload(InsuranceClaim.invoice),
    )

    if patient_id:
        query = query.where(InsuranceClaim.patient_id == patient_id)

    if insurance_company_id:
        query = query.where(InsuranceClaim.insurance_company_id == insurance_company_id)

    if status_filter:
        query = query.where(InsuranceClaim.status == status_filter)

    if date_from:
        from datetime import datetime
        query = query.where(InsuranceClaim.created_at >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        from datetime import datetime
        query = query.where(InsuranceClaim.created_at <= datetime.combine(date_to, datetime.max.time()))

    query = query.order_by(InsuranceClaim.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    claims = result.scalars().all()

    return [
        {
            "id": claim.id,
            "internal_claim_number": claim.internal_claim_number,
            "claim_number": claim.claim_number,
            "patient_name": claim.patient.full_name,
            "insurance_company_name": claim.insurance_company.name,
            "invoice_number": claim.invoice.invoice_number,
            "claimed_amount": claim.claimed_amount,
            "approved_amount": claim.approved_amount,
            "status": claim.status,
            "submitted_at": claim.submitted_at,
            "created_at": claim.created_at,
        }
        for claim in claims
    ]


@router.get("/claims/summary", response_model=ClaimSummary)
async def get_claims_summary(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID | None = None,
    insurance_company_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Get claims summary/statistics."""
    service = InsuranceClaimsService(db)

    summary = await service.get_claim_summary(
        patient_id=patient_id,
        insurance_company_id=insurance_company_id,
        date_from=date_from,
        date_to=date_to,
    )

    return summary


# ============= Pre-Authorization Endpoints =============

@router.post("/preauthorizations", response_model=PreAuthorizationResponse, status_code=status.HTTP_201_CREATED)
async def create_preauthorization(
    db: DbSession,
    current_user: CurrentUser,
    preauth_in: PreAuthorizationCreate,
) -> dict:
    """Create a pre-authorization request."""
    service = InsuranceClaimsService(db)

    try:
        preauth = await service.create_preauthorization(
            patient_id=preauth_in.patient_id,
            patient_insurance_id=preauth_in.patient_insurance_id,
            procedure_name=preauth_in.procedure_name,
            requested_amount=preauth_in.requested_amount,
            requested_date=preauth_in.requested_date,
            procedure_id=preauth_in.procedure_id,
            procedure_code=preauth_in.procedure_code,
            diagnosis=preauth_in.diagnosis,
            planned_procedure_date=preauth_in.planned_procedure_date,
            documents=preauth_in.documents_submitted,
            notes=preauth_in.notes,
            requested_by=preauth_in.requested_by or current_user.username,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Load relationships
    result = await db.execute(
        select(PreAuthorization)
        .options(
            selectinload(PreAuthorization.patient),
            selectinload(PreAuthorization.insurance_company),
        )
        .where(PreAuthorization.id == preauth.id)
    )
    preauth = result.scalar_one()

    return {
        **preauth.__dict__,
        "patient_name": preauth.patient.full_name,
        "insurance_company_name": preauth.insurance_company.name,
        "is_valid": preauth.is_valid,
    }


@router.post("/preauthorizations/{preauth_id}/submit", response_model=PreAuthorizationResponse)
async def submit_preauthorization(
    db: DbSession,
    current_user: CurrentUser,
    preauth_id: UUID,
    submit_data: PreAuthorizationSubmit | None = None,
) -> dict:
    """Submit pre-authorization to insurance/TPA."""
    service = InsuranceClaimsService(db)

    try:
        preauth = await service.submit_preauthorization(
            preauth_id=preauth_id,
            documents=submit_data.documents_submitted if submit_data else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Load relationships
    result = await db.execute(
        select(PreAuthorization)
        .options(
            selectinload(PreAuthorization.patient),
            selectinload(PreAuthorization.insurance_company),
        )
        .where(PreAuthorization.id == preauth.id)
    )
    preauth = result.scalar_one()

    return {
        **preauth.__dict__,
        "patient_name": preauth.patient.full_name,
        "insurance_company_name": preauth.insurance_company.name,
        "is_valid": preauth.is_valid,
    }


@router.patch("/preauthorizations/{preauth_id}", response_model=PreAuthorizationResponse)
async def update_preauthorization(
    db: DbSession,
    current_user: CurrentUser,
    preauth_id: UUID,
    preauth_in: PreAuthorizationUpdate,
) -> dict:
    """Update pre-authorization status."""
    service = InsuranceClaimsService(db)

    update_data = preauth_in.model_dump(exclude_unset=True)

    # If status is being updated, use service method
    if "status" in update_data:
        try:
            preauth = await service.update_preauth_status(
                preauth_id=preauth_id,
                status=update_data["status"],
                auth_number=update_data.get("auth_number"),
                approved_amount=update_data.get("approved_amount"),
                valid_from=update_data.get("valid_from"),
                valid_to=update_data.get("valid_to"),
                rejection_reason=update_data.get("rejection_reason"),
                rejection_code=update_data.get("rejection_code"),
                tpa_notes=update_data.get("tpa_notes"),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    else:
        # Simple update
        result = await db.execute(
            select(PreAuthorization).where(PreAuthorization.id == preauth_id)
        )
        preauth = result.scalar_one_or_none()
        if not preauth:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pre-authorization not found",
            )

        for field, value in update_data.items():
            setattr(preauth, field, value)

        await db.commit()
        await db.refresh(preauth)

    # Load relationships
    result = await db.execute(
        select(PreAuthorization)
        .options(
            selectinload(PreAuthorization.patient),
            selectinload(PreAuthorization.insurance_company),
        )
        .where(PreAuthorization.id == preauth.id)
    )
    preauth = result.scalar_one()

    return {
        **preauth.__dict__,
        "patient_name": preauth.patient.full_name,
        "insurance_company_name": preauth.insurance_company.name,
        "is_valid": preauth.is_valid,
    }


@router.get("/preauthorizations", response_model=list[PreAuthorizationListResponse])
async def list_preauthorizations(
    db: DbSession,
    current_user: CurrentUser,
    patient_id: UUID | None = None,
    insurance_company_id: UUID | None = None,
    status_filter: str | None = None,
    valid_only: bool = Query(False, description="Show only currently valid pre-auths"),
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List pre-authorizations."""
    query = select(PreAuthorization).options(
        selectinload(PreAuthorization.patient),
        selectinload(PreAuthorization.insurance_company),
    )

    if patient_id:
        query = query.where(PreAuthorization.patient_id == patient_id)

    if insurance_company_id:
        query = query.where(PreAuthorization.insurance_company_id == insurance_company_id)

    if status_filter:
        query = query.where(PreAuthorization.status == status_filter)

    if valid_only:
        today = date.today()
        query = query.where(
            PreAuthorization.status == PreAuthStatus.APPROVED.value,
            PreAuthorization.valid_from <= today,
            PreAuthorization.valid_to >= today,
        )

    query = query.order_by(PreAuthorization.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    preauths = result.scalars().all()

    return [
        {
            "id": pa.id,
            "internal_ref_number": pa.internal_ref_number,
            "auth_number": pa.auth_number,
            "patient_name": pa.patient.full_name,
            "insurance_company_name": pa.insurance_company.name,
            "procedure_name": pa.procedure_name,
            "requested_amount": pa.requested_amount,
            "approved_amount": pa.approved_amount,
            "status": pa.status,
            "requested_date": pa.requested_date,
            "is_valid": pa.is_valid,
        }
        for pa in preauths
    ]


@router.get("/preauthorizations/{preauth_id}/validity")
async def check_preauth_validity(
    db: DbSession,
    current_user: CurrentUser,
    preauth_id: UUID,
) -> dict:
    """Check if pre-authorization is valid for use."""
    service = InsuranceClaimsService(db)

    try:
        validity = await service.check_preauth_validity(preauth_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return validity
