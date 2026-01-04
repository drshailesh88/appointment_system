"""
Insurance models for patient insurance and verification.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.patient import Patient


class PatientInsurance(BaseModel):
    """
    Patient insurance information.

    Stores insurance policy details for patients.
    Supports multiple insurance policies per patient (primary, secondary, etc.).

    Attributes:
        patient_id: Associated patient
        provider_name: Insurance provider (e.g., Star Health, ICICI Lombard, Max Bupa)
        policy_number: Insurance policy number
        group_number: Group policy number (optional)
        insurance_type: Type (e.g., health, dental, vision)
        plan_name: Name of the insurance plan
        coverage_start_date: Policy start date
        coverage_end_date: Policy expiry date
        is_primary: Whether this is the primary insurance
        subscriber_name: Policy holder name
        subscriber_relationship: Relationship to patient
        tpa_name: Third-party administrator (TPA) name (Indian insurance)
        tpa_id: TPA ID number
        cashless_enabled: Whether cashless treatment is available
        network_type: PPO, HMO, etc. (or TPA network for India)
        copay_amount: Fixed copay amount per visit
        deductible_amount: Annual deductible
        out_of_pocket_max: Maximum out-of-pocket expense
        additional_info: JSON field for custom data
        is_active: Whether policy is currently active
    """

    __tablename__ = "patient_insurances"

    # Patient Reference
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider Information
    provider_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    policy_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    group_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insurance_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="health",
    )  # health, dental, vision
    plan_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Coverage Dates
    coverage_start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    coverage_end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    # Policy Priority
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)

    # Subscriber Information
    subscriber_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subscriber_relationship: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # self, spouse, parent, child

    # Indian Insurance - TPA Information
    tpa_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )  # e.g., Medi Assist, Paramount Health
    tpa_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cashless_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Network and Benefits
    network_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # PPO, HMO, or TPA network
    copay_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    deductible_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    out_of_pocket_max: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Additional Info
    additional_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="insurances")
    verifications: Mapped[list["InsuranceVerification"]] = relationship(
        "InsuranceVerification",
        back_populates="insurance",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PatientInsurance {self.provider_name} - {self.policy_number}>"


class InsuranceVerification(BaseModel):
    """
    Insurance eligibility verification results.

    Stores results from insurance verification API calls.
    Cached to avoid repeated calls within validity period.

    Attributes:
        insurance_id: Associated patient insurance
        verified_at: When verification was performed
        verified_by: User who initiated verification
        status: Verification status
        is_eligible: Whether patient is eligible
        eligibility_start_date: Coverage start date from verification
        eligibility_end_date: Coverage end date from verification
        coverage_details: JSON with detailed coverage info
        copay_info: JSON with copay details
        deductible_info: JSON with deductible details
        benefits: JSON with covered benefits/procedures
        limitations: Text describing coverage limitations
        error_message: Error message if verification failed
        provider_response: Full API response (for debugging)
        expires_at: When this verification expires (typically 24-72 hours)
    """

    __tablename__ = "insurance_verifications"

    # Insurance Reference
    insurance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patient_insurances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Verification Metadata
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    verified_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # User ID or "system"

    # Verification Result
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # success, failed, pending
    is_eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Eligibility Dates
    eligibility_start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    eligibility_end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    # Coverage Information
    coverage_details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )  # Detailed coverage info
    copay_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deductible_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    benefits: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )  # List of covered procedures

    # Limitations and Errors
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw Response
    provider_response: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )  # Full API response

    # Cache Expiry
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    insurance: Mapped["PatientInsurance"] = relationship(
        "PatientInsurance",
        back_populates="verifications",
    )

    def __repr__(self) -> str:
        return f"<InsuranceVerification {self.status} at {self.verified_at}>"


class InsuranceClaim(BaseModel):
    """
    Insurance claim tracking (for future integration).

    Placeholder model for future claims management integration.
    Can be used to track claim submissions, status, and payments.

    Attributes:
        insurance_id: Associated patient insurance
        claim_number: Unique claim identifier
        service_date: Date of service
        submission_date: When claim was submitted
        status: Claim status (submitted, approved, denied, paid)
        claimed_amount: Amount claimed
        approved_amount: Amount approved by insurance
        paid_amount: Amount paid by insurance
        patient_responsibility: Amount patient needs to pay
        denial_reason: Reason for denial (if denied)
        notes: Additional notes
    """

    __tablename__ = "insurance_claims"

    # Insurance Reference
    insurance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patient_insurances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Claim Information
    claim_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    service_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    submission_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="submitted",
        index=True,
    )

    # Amounts
    claimed_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    approved_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    paid_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    patient_responsibility: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Additional Information
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    insurance: Mapped["PatientInsurance"] = relationship("PatientInsurance")

    def __repr__(self) -> str:
        return f"<InsuranceClaim {self.claim_number} - {self.status}>"
