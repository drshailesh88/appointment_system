"""
Insurance schemas for insurance verification API.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ==================
# Base Schemas
# ==================


class InsuranceInfoBase(BaseModel):
    """Base insurance information schema."""

    provider_name: str = Field(..., min_length=1, max_length=200)
    policy_number: str = Field(..., min_length=1, max_length=100)
    group_number: str | None = Field(None, max_length=100)
    insurance_type: str = Field(default="health", max_length=50)
    plan_name: str | None = Field(None, max_length=200)
    coverage_start_date: date | None = None
    coverage_end_date: date | None = None
    is_primary: bool = True
    subscriber_name: str | None = Field(None, max_length=200)
    subscriber_relationship: str | None = Field(
        None,
        max_length=50,
    )  # self, spouse, parent, child
    tpa_name: str | None = Field(None, max_length=200)
    tpa_id: str | None = Field(None, max_length=100)
    cashless_enabled: bool = False
    network_type: str | None = Field(None, max_length=50)
    copay_amount: float | None = Field(None, ge=0)
    deductible_amount: float | None = Field(None, ge=0)
    out_of_pocket_max: float | None = Field(None, ge=0)
    additional_info: dict | None = None

    @field_validator("insurance_type")
    @classmethod
    def validate_insurance_type(cls, v: str) -> str:
        """Validate insurance type."""
        allowed_types = ["health", "dental", "vision", "accident", "critical_illness"]
        if v.lower() not in allowed_types:
            raise ValueError(f"Insurance type must be one of: {', '.join(allowed_types)}")
        return v.lower()

    @field_validator("subscriber_relationship")
    @classmethod
    def validate_relationship(cls, v: str | None) -> str | None:
        """Validate subscriber relationship."""
        if v is None:
            return v
        allowed = ["self", "spouse", "parent", "child", "other"]
        if v.lower() not in allowed:
            raise ValueError(f"Relationship must be one of: {', '.join(allowed)}")
        return v.lower()


class InsuranceInfoCreate(InsuranceInfoBase):
    """Schema for creating insurance information."""

    patient_id: UUID


class InsuranceInfoUpdate(BaseModel):
    """Schema for updating insurance information."""

    provider_name: str | None = Field(None, min_length=1, max_length=200)
    policy_number: str | None = Field(None, min_length=1, max_length=100)
    group_number: str | None = None
    insurance_type: str | None = None
    plan_name: str | None = None
    coverage_start_date: date | None = None
    coverage_end_date: date | None = None
    is_primary: bool | None = None
    subscriber_name: str | None = None
    subscriber_relationship: str | None = None
    tpa_name: str | None = None
    tpa_id: str | None = None
    cashless_enabled: bool | None = None
    network_type: str | None = None
    copay_amount: float | None = None
    deductible_amount: float | None = None
    out_of_pocket_max: float | None = None
    additional_info: dict | None = None
    is_active: bool | None = None


class InsuranceInfoResponse(InsuranceInfoBase):
    """Schema for insurance information response."""

    id: UUID
    patient_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==================
# Verification Schemas
# ==================


class VerificationRequest(BaseModel):
    """Request to verify insurance eligibility."""

    insurance_id: UUID
    service_date: date | None = None
    procedure_codes: list[str] | None = Field(
        None,
        description="List of procedure codes to check coverage for",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force new verification even if cached result exists",
    )


class CopayInfo(BaseModel):
    """Copay information."""

    amount: float | None = None
    percentage: float | None = None
    description: str | None = None
    applies_to: str | None = None  # consultation, procedures, etc.


class DeductibleInfo(BaseModel):
    """Deductible information."""

    total_deductible: float | None = None
    remaining_deductible: float | None = None
    met_amount: float | None = None
    family_deductible: float | None = None
    reset_date: date | None = None


class CoverageDetails(BaseModel):
    """Detailed coverage information."""

    plan_name: str | None = None
    coverage_level: str | None = None  # individual, family
    network_status: str | None = None  # in-network, out-of-network
    covered_services: list[str] | None = None
    excluded_services: list[str] | None = None
    max_coverage_amount: float | None = None
    remaining_coverage: float | None = None


class VerificationResult(BaseModel):
    """Insurance verification result."""

    id: UUID
    insurance_id: UUID
    verified_at: datetime
    verified_by: str | None
    status: str  # success, failed, pending
    is_eligible: bool | None
    eligibility_start_date: date | None
    eligibility_end_date: date | None
    coverage_details: CoverageDetails | None = None
    copay_info: CopayInfo | None = None
    deductible_info: DeductibleInfo | None = None
    benefits: dict | None = None
    limitations: str | None = None
    error_message: str | None = None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


# ==================
# List Schemas
# ==================


class InsuranceListItem(BaseModel):
    """Minimal insurance info for listing."""

    id: UUID
    provider_name: str
    policy_number: str
    insurance_type: str
    is_primary: bool
    is_active: bool
    coverage_end_date: date | None
    last_verified: datetime | None = None

    model_config = {"from_attributes": True}


class PatientInsuranceList(BaseModel):
    """List of patient's insurance policies."""

    patient_id: UUID
    insurances: list[InsuranceListItem]


# ==================
# Provider Schemas
# ==================


class InsuranceProvider(BaseModel):
    """Supported insurance provider."""

    code: str = Field(..., description="Provider code for API integration")
    name: str = Field(..., description="Display name")
    country: str = Field(default="IN", description="Country code")
    supports_verification: bool = Field(
        default=False,
        description="Whether verification API is available",
    )
    supports_claims: bool = Field(
        default=False,
        description="Whether claims API is available",
    )
    tpa_required: bool = Field(
        default=False,
        description="Whether TPA information is required",
    )
    documentation_url: str | None = Field(
        None,
        description="URL to provider documentation",
    )


class InsuranceProviderList(BaseModel):
    """List of supported insurance providers."""

    providers: list[InsuranceProvider]


# ==================
# Claim Schemas (Future)
# ==================


class ClaimCreate(BaseModel):
    """Schema for creating an insurance claim."""

    insurance_id: UUID
    service_date: date
    claimed_amount: float = Field(..., gt=0)
    procedure_codes: list[str] | None = None
    diagnosis_codes: list[str] | None = None
    notes: str | None = None


class ClaimResponse(BaseModel):
    """Schema for claim response."""

    id: UUID
    insurance_id: UUID
    claim_number: str
    service_date: date
    submission_date: date | None
    status: str
    claimed_amount: float
    approved_amount: float | None
    paid_amount: float | None
    patient_responsibility: float | None
    denial_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
