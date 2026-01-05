"""
Insurance-related models for billing and claims management.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSONB, UUID


if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.patient import Patient
    from app.models.procedure import Procedure


class CoverageType(str, Enum):
    """Insurance coverage types."""

    INDIVIDUAL = "individual"
    FAMILY_FLOATER = "family_floater"
    GROUP = "group"
    SENIOR_CITIZEN = "senior_citizen"
    CRITICAL_ILLNESS = "critical_illness"
    MATERNITY = "maternity"


class ClaimStatus(str, Enum):
    """Insurance claim status types."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"
    SETTLED = "settled"
    APPEALED = "appealed"


class PreAuthStatus(str, Enum):
    """Pre-authorization status types."""

    PENDING = "pending"
    REQUESTED = "requested"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InsuranceCompany(BaseModel):
    """
    Insurance company/TPA master data.

    Attributes:
        name: Company name (e.g., Star Health, HDFC Ergo)
        code: Short code for the company
        contact_email: Email for claims submission
        contact_phone: Phone number for queries
        claim_submission_url: URL for online claim submission
        tpa_name: Third Party Administrator name
        cashless_available: Whether cashless treatment is available
        is_active: Whether company is active for new claims
    """

    __tablename__ = "insurance_companies"

    # Company Details
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    # Contact Information
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # TPA Details
    tpa_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tpa_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tpa_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Claim Submission
    claim_submission_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    claim_submission_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Features
    cashless_available: Mapped[bool] = mapped_column(Boolean, default=False)
    preauth_required: Mapped[bool] = mapped_column(Boolean, default=False)
    preauth_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Pre-auth required for procedures above this amount"
    )

    # Network
    network_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="PPO, HMO, etc."
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim_process_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes about claim submission process"
    )

    # Relationships
    patient_insurances: Mapped[list["PatientInsurance"]] = relationship(
        "PatientInsurance",
        back_populates="insurance_company",
    )
    claims: Mapped[list["InsuranceClaim"]] = relationship(
        "InsuranceClaim",
        back_populates="insurance_company",
    )

    def __repr__(self) -> str:
        return f"<InsuranceCompany {self.name} ({self.code})>"


class PatientInsurance(BaseModel):
    """
    Patient's insurance policy details.

    Attributes:
        patient_id: Patient who owns the policy
        insurance_company_id: Insurance provider
        policy_number: Unique policy number
        group_number: Group policy number (for corporate/family)
        valid_from: Policy start date
        valid_to: Policy end date
        coverage_type: Type of coverage
        sum_insured: Maximum coverage amount
        is_primary: Whether this is the primary insurance
    """

    __tablename__ = "patient_insurances"

    # Relations
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    insurance_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("insurance_companies.id"),
        nullable=False,
        index=True,
    )

    # Policy Details
    policy_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    group_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    member_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Validity
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)

    # Coverage
    coverage_type: Mapped[str] = mapped_column(
        String(50),
        default=CoverageType.INDIVIDUAL.value,
    )
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    copay_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        comment="Patient's share percentage (e.g., 10% copay)"
    )
    deductible_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        comment="Amount patient must pay before insurance kicks in"
    )

    # Priority
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Primary insurance is billed first"
    )
    priority_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Billing order for multiple insurances"
    )

    # Policyholder (if different from patient)
    policyholder_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    policyholder_relationship: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Self, Spouse, Parent, Child, etc."
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    verification_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="verified, pending, failed"
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="insurances")
    insurance_company: Mapped["InsuranceCompany"] = relationship(
        "InsuranceCompany",
        back_populates="patient_insurances",
    )
    claims: Mapped[list["InsuranceClaim"]] = relationship(
        "InsuranceClaim",
        back_populates="patient_insurance",
    )
    preauthorizations: Mapped[list["PreAuthorization"]] = relationship(
        "PreAuthorization",
        back_populates="patient_insurance",
    )

    @property
    def is_valid(self) -> bool:
        """Check if policy is currently valid."""
        today = date.today()
        return self.valid_from <= today <= self.valid_to and self.is_active

    def __repr__(self) -> str:
        return f"<PatientInsurance {self.policy_number}>"


class InsuranceClaim(BaseModel):
    """
    Insurance claim tracking.

    Attributes:
        patient_id: Patient for whom claim is filed
        invoice_id: Invoice being claimed
        patient_insurance_id: Insurance policy used
        claim_number: TPA/Insurance claim number
        claimed_amount: Amount claimed from insurance
        approved_amount: Amount approved by insurance
        settled_amount: Amount actually paid
        status: Claim processing status
    """

    __tablename__ = "insurance_claims"

    # Relations
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("invoices.id"),
        nullable=False,
        index=True,
    )
    patient_insurance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("patient_insurances.id"),
        nullable=False,
        index=True,
    )
    insurance_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("insurance_companies.id"),
        nullable=False,
        index=True,
    )
    preauthorization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(),
        ForeignKey("preauthorizations.id"),
        nullable=True,
    )

    # Claim Details
    claim_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="TPA/Insurance assigned claim number"
    )
    internal_claim_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Our internal tracking number"
    )

    # Amounts
    claimed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        comment="Amount approved by insurance"
    )
    settled_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        comment="Amount actually received"
    )
    patient_liability: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        comment="Amount patient must pay (copay + non-covered)"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default=ClaimStatus.DRAFT.value,
        index=True,
    )

    # Dates
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rejection/Appeals
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    appeal_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    appeal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Documents
    documents_submitted: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of document URLs/paths submitted"
    )

    # Communication
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tpa_reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes about claim processing"
    )

    # Submitted by
    submitted_by: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Staff member who submitted claim"
    )

    # Additional metadata
    claim_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional claim data from TPA"
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    invoice: Mapped["Invoice"] = relationship("Invoice")
    patient_insurance: Mapped["PatientInsurance"] = relationship(
        "PatientInsurance",
        back_populates="claims",
    )
    insurance_company: Mapped["InsuranceCompany"] = relationship(
        "InsuranceCompany",
        back_populates="claims",
    )
    preauthorization: Mapped["PreAuthorization | None"] = relationship(
        "PreAuthorization",
        back_populates="claims",
    )

    @property
    def rejection_amount(self) -> Decimal:
        """Calculate rejected/non-covered amount."""
        return self.claimed_amount - self.approved_amount

    def __repr__(self) -> str:
        return f"<InsuranceClaim {self.internal_claim_number} - {self.status}>"


class PreAuthorization(BaseModel):
    """
    Pre-authorization requests for procedures.

    Attributes:
        patient_id: Patient requiring procedure
        patient_insurance_id: Insurance policy for authorization
        procedure_id: Planned procedure (if linked)
        requested_amount: Estimated procedure cost
        status: Authorization status
        auth_number: Authorization number from insurance
        valid_from: Authorization validity start
        valid_to: Authorization validity end
    """

    __tablename__ = "preauthorizations"

    # Relations
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    patient_insurance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("patient_insurances.id"),
        nullable=False,
        index=True,
    )
    insurance_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        ForeignKey("insurance_companies.id"),
        nullable=False,
        index=True,
    )
    procedure_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(),
        ForeignKey("procedures.id"),
        nullable=True,
    )

    # Authorization Details
    auth_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Authorization number from insurance/TPA"
    )
    internal_ref_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Our internal reference number"
    )

    # Procedure Information
    procedure_name: Mapped[str] = mapped_column(String(500), nullable=False)
    procedure_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="CPT/ICD code"
    )
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Amounts
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        comment="Amount authorized by insurance"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        default=PreAuthStatus.PENDING.value,
        index=True,
    )

    # Validity
    requested_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_procedure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Dates
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rejection
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Documents
    documents_submitted: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of document URLs/paths for pre-auth"
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tpa_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notes from TPA/Insurance"
    )

    # Submitted by
    requested_by: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Doctor/Staff who requested pre-auth"
    )

    # Additional metadata
    preauth_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional pre-auth data"
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    patient_insurance: Mapped["PatientInsurance"] = relationship(
        "PatientInsurance",
        back_populates="preauthorizations",
    )
    insurance_company: Mapped["InsuranceCompany"] = relationship("InsuranceCompany")
    procedure: Mapped["Procedure | None"] = relationship("Procedure")
    claims: Mapped[list["InsuranceClaim"]] = relationship(
        "InsuranceClaim",
        back_populates="preauthorization",
    )

    @property
    def is_valid(self) -> bool:
        """Check if pre-authorization is currently valid."""
        if self.status != PreAuthStatus.APPROVED.value:
            return False
        if not self.valid_from or not self.valid_to:
            return False
        today = date.today()
        return self.valid_from <= today <= self.valid_to

    def __repr__(self) -> str:
        return f"<PreAuthorization {self.internal_ref_number} - {self.status}>"
