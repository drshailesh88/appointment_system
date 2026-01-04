"""
Insurance schemas for API validation.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.insurance import ClaimStatus, CoverageType, PreAuthStatus


# ============= Insurance Company Schemas =============

class InsuranceCompanyBase(BaseModel):
    """Base insurance company schema."""

    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=20)


class InsuranceCompanyCreate(InsuranceCompanyBase):
    """Schema for creating an insurance company."""

    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    contact_address: str | None = None
    tpa_name: str | None = Field(None, max_length=200)
    tpa_email: str | None = Field(None, max_length=255)
    tpa_phone: str | None = Field(None, max_length=20)
    claim_submission_url: str | None = Field(None, max_length=500)
    claim_submission_email: str | None = Field(None, max_length=255)
    cashless_available: bool = False
    preauth_required: bool = False
    preauth_threshold: Decimal | None = Field(None, ge=0)
    network_type: str | None = Field(None, max_length=50)
    is_active: bool = True
    notes: str | None = None
    claim_process_notes: str | None = None


class InsuranceCompanyUpdate(BaseModel):
    """Schema for updating an insurance company."""

    name: str | None = Field(None, min_length=1, max_length=200)
    code: str | None = Field(None, min_length=1, max_length=20)
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_address: str | None = None
    tpa_name: str | None = None
    tpa_email: str | None = None
    tpa_phone: str | None = None
    claim_submission_url: str | None = None
    claim_submission_email: str | None = None
    cashless_available: bool | None = None
    preauth_required: bool | None = None
    preauth_threshold: Decimal | None = None
    network_type: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    claim_process_notes: str | None = None


class InsuranceCompanyResponse(BaseModel):
    """Schema for insurance company response."""

    id: UUID
    name: str
    code: str
    contact_email: str | None
    contact_phone: str | None
    contact_address: str | None
    tpa_name: str | None
    tpa_email: str | None
    tpa_phone: str | None
    claim_submission_url: str | None
    claim_submission_email: str | None
    cashless_available: bool
    preauth_required: bool
    preauth_threshold: Decimal | None
    network_type: str | None
    is_active: bool
    notes: str | None
    claim_process_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InsuranceCompanyListResponse(BaseModel):
    """Schema for listing insurance companies."""

    id: UUID
    name: str
    code: str
    tpa_name: str | None
    cashless_available: bool
    preauth_required: bool
    is_active: bool

    model_config = {"from_attributes": True}


# ============= Patient Insurance Schemas =============

class PatientInsuranceBase(BaseModel):
    """Base patient insurance schema."""

    patient_id: UUID
    insurance_company_id: UUID
    policy_number: str = Field(..., min_length=1, max_length=100)
    valid_from: date
    valid_to: date
    coverage_type: CoverageType = CoverageType.INDIVIDUAL
    sum_insured: Decimal = Field(..., gt=0)


class PatientInsuranceCreate(PatientInsuranceBase):
    """Schema for creating patient insurance."""

    group_number: str | None = Field(None, max_length=100)
    member_id: str | None = Field(None, max_length=100)
    copay_percentage: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    deductible_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    is_primary: bool = True
    priority_order: int = Field(default=1, ge=1)
    policyholder_name: str | None = Field(None, max_length=200)
    policyholder_relationship: str | None = Field(None, max_length=50)
    notes: str | None = None


class PatientInsuranceUpdate(BaseModel):
    """Schema for updating patient insurance."""

    policy_number: str | None = None
    group_number: str | None = None
    member_id: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    coverage_type: CoverageType | None = None
    sum_insured: Decimal | None = Field(None, gt=0)
    copay_percentage: Decimal | None = Field(None, ge=0, le=100)
    deductible_amount: Decimal | None = Field(None, ge=0)
    is_primary: bool | None = None
    priority_order: int | None = Field(None, ge=1)
    policyholder_name: str | None = None
    policyholder_relationship: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class PatientInsuranceResponse(BaseModel):
    """Schema for patient insurance response."""

    id: UUID
    patient_id: UUID
    insurance_company_id: UUID
    policy_number: str
    group_number: str | None
    member_id: str | None
    valid_from: date
    valid_to: date
    coverage_type: str
    sum_insured: Decimal
    copay_percentage: Decimal
    deductible_amount: Decimal
    is_primary: bool
    priority_order: int
    policyholder_name: str | None
    policyholder_relationship: str | None
    is_active: bool
    verification_status: str | None
    last_verified_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Nested details
    insurance_company_name: str | None = None
    patient_name: str | None = None
    is_valid: bool = False

    model_config = {"from_attributes": True}


class PatientInsuranceListResponse(BaseModel):
    """Schema for listing patient insurance."""

    id: UUID
    patient_id: UUID
    insurance_company_id: UUID
    insurance_company_name: str
    policy_number: str
    valid_from: date
    valid_to: date
    is_active: bool
    is_valid: bool

    model_config = {"from_attributes": True}


# ============= Insurance Claim Schemas =============

class InsuranceClaimBase(BaseModel):
    """Base insurance claim schema."""

    patient_id: UUID
    invoice_id: UUID
    patient_insurance_id: UUID
    claimed_amount: Decimal = Field(..., gt=0)


class InsuranceClaimCreate(InsuranceClaimBase):
    """Schema for creating an insurance claim."""

    preauthorization_id: UUID | None = None
    notes: str | None = None
    documents_submitted: list[str] | None = None


class InsuranceClaimUpdate(BaseModel):
    """Schema for updating an insurance claim."""

    claim_number: str | None = None
    status: ClaimStatus | None = None
    approved_amount: Decimal | None = Field(None, ge=0)
    settled_amount: Decimal | None = Field(None, ge=0)
    patient_liability: Decimal | None = Field(None, ge=0)
    rejection_reason: str | None = None
    rejection_code: str | None = None
    appeal_notes: str | None = None
    tpa_reference_number: str | None = None
    processing_notes: str | None = None
    notes: str | None = None


class InsuranceClaimSubmit(BaseModel):
    """Schema for submitting a claim to insurance."""

    claim_id: UUID
    documents_submitted: list[str] | None = None
    submitted_by: str | None = None


class InsuranceClaimResponse(BaseModel):
    """Schema for insurance claim response."""

    id: UUID
    patient_id: UUID
    invoice_id: UUID
    patient_insurance_id: UUID
    insurance_company_id: UUID
    preauthorization_id: UUID | None
    claim_number: str | None
    internal_claim_number: str
    claimed_amount: Decimal
    approved_amount: Decimal
    settled_amount: Decimal
    patient_liability: Decimal
    status: str
    submitted_at: datetime | None
    acknowledged_at: datetime | None
    reviewed_at: datetime | None
    approved_at: datetime | None
    settled_at: datetime | None
    rejection_reason: str | None
    rejection_code: str | None
    appeal_submitted_at: datetime | None
    appeal_notes: str | None
    documents_submitted: list[str] | None
    notes: str | None
    tpa_reference_number: str | None
    processing_notes: str | None
    submitted_by: str | None
    created_at: datetime
    updated_at: datetime

    # Nested details
    patient_name: str | None = None
    insurance_company_name: str | None = None
    invoice_number: str | None = None
    rejection_amount: Decimal = Decimal("0.00")

    model_config = {"from_attributes": True}


class InsuranceClaimListResponse(BaseModel):
    """Schema for listing insurance claims."""

    id: UUID
    internal_claim_number: str
    claim_number: str | None
    patient_name: str
    insurance_company_name: str
    invoice_number: str
    claimed_amount: Decimal
    approved_amount: Decimal
    status: str
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimSummary(BaseModel):
    """Schema for claim summary/stats."""

    total_claims: int
    total_claimed: Decimal
    total_approved: Decimal
    total_settled: Decimal
    pending_count: int
    approved_count: int
    rejected_count: int


# ============= Pre-Authorization Schemas =============

class PreAuthorizationBase(BaseModel):
    """Base pre-authorization schema."""

    patient_id: UUID
    patient_insurance_id: UUID
    procedure_name: str = Field(..., min_length=1, max_length=500)
    requested_amount: Decimal = Field(..., gt=0)
    requested_date: date


class PreAuthorizationCreate(PreAuthorizationBase):
    """Schema for creating a pre-authorization request."""

    procedure_id: UUID | None = None
    procedure_code: str | None = Field(None, max_length=50)
    diagnosis: str | None = None
    planned_procedure_date: date | None = None
    notes: str | None = None
    documents_submitted: list[str] | None = None
    requested_by: str | None = None


class PreAuthorizationUpdate(BaseModel):
    """Schema for updating a pre-authorization."""

    auth_number: str | None = None
    status: PreAuthStatus | None = None
    approved_amount: Decimal | None = Field(None, ge=0)
    valid_from: date | None = None
    valid_to: date | None = None
    planned_procedure_date: date | None = None
    rejection_reason: str | None = None
    rejection_code: str | None = None
    tpa_notes: str | None = None
    notes: str | None = None


class PreAuthorizationSubmit(BaseModel):
    """Schema for submitting a pre-authorization request."""

    preauth_id: UUID
    documents_submitted: list[str] | None = None


class PreAuthorizationResponse(BaseModel):
    """Schema for pre-authorization response."""

    id: UUID
    patient_id: UUID
    patient_insurance_id: UUID
    insurance_company_id: UUID
    procedure_id: UUID | None
    auth_number: str | None
    internal_ref_number: str
    procedure_name: str
    procedure_code: str | None
    diagnosis: str | None
    requested_amount: Decimal
    approved_amount: Decimal
    status: str
    requested_date: date
    planned_procedure_date: date | None
    valid_from: date | None
    valid_to: date | None
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    rejection_code: str | None
    documents_submitted: list[str] | None
    notes: str | None
    tpa_notes: str | None
    requested_by: str | None
    created_at: datetime
    updated_at: datetime

    # Nested details
    patient_name: str | None = None
    insurance_company_name: str | None = None
    is_valid: bool = False

    model_config = {"from_attributes": True}


class PreAuthorizationListResponse(BaseModel):
    """Schema for listing pre-authorizations."""

    id: UUID
    internal_ref_number: str
    auth_number: str | None
    patient_name: str
    insurance_company_name: str
    procedure_name: str
    requested_amount: Decimal
    approved_amount: Decimal
    status: str
    requested_date: date
    is_valid: bool

    model_config = {"from_attributes": True}


class PreAuthSummary(BaseModel):
    """Schema for pre-auth summary/stats."""

    total_requests: int
    total_requested: Decimal
    total_approved: Decimal
    pending_count: int
    approved_count: int
    rejected_count: int
    expired_count: int
