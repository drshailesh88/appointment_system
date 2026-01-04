"""
Insurance claims service for managing claims and pre-authorizations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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


class InsuranceClaimsService:
    """Service for managing insurance claims and pre-authorizations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_claim_number(self, insurance_company_id: UUID) -> str:
        """
        Generate internal claim number.

        Format: CLM-YYYYMMDD-COMPANY-XXXX
        """
        today = date.today()

        # Get company code
        result = await self.db.execute(
            select(InsuranceCompany).where(InsuranceCompany.id == insurance_company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError("Insurance company not found")

        prefix = f"CLM-{today.strftime('%Y%m%d')}-{company.code}"

        # Get count for today
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(InsuranceClaim.id)).where(
                InsuranceClaim.internal_claim_number.like(f"{prefix}%")
            )
        )
        count = result.scalar() or 0

        return f"{prefix}-{count + 1:04d}"

    async def create_claim(
        self,
        patient_id: UUID,
        invoice_id: UUID,
        patient_insurance_id: UUID,
        claimed_amount: Decimal,
        preauthorization_id: UUID | None = None,
        documents: list[str] | None = None,
        notes: str | None = None,
    ) -> InsuranceClaim:
        """
        Create a new insurance claim.

        Args:
            patient_id: Patient ID
            invoice_id: Invoice ID
            patient_insurance_id: Patient's insurance policy ID
            claimed_amount: Amount being claimed
            preauthorization_id: Pre-authorization reference (if applicable)
            documents: List of document paths/URLs
            notes: Additional notes

        Returns:
            Created InsuranceClaim object
        """
        # Verify patient insurance is valid
        result = await self.db.execute(
            select(PatientInsurance)
            .options(selectinload(PatientInsurance.insurance_company))
            .where(PatientInsurance.id == patient_insurance_id)
        )
        patient_insurance = result.scalar_one_or_none()
        if not patient_insurance:
            raise ValueError("Patient insurance not found")

        if not patient_insurance.is_valid:
            raise ValueError("Patient insurance is not valid (expired or inactive)")

        # Generate internal claim number
        claim_number = await self.generate_claim_number(patient_insurance.insurance_company_id)

        # Create claim
        claim = InsuranceClaim(
            patient_id=patient_id,
            invoice_id=invoice_id,
            patient_insurance_id=patient_insurance_id,
            insurance_company_id=patient_insurance.insurance_company_id,
            preauthorization_id=preauthorization_id,
            internal_claim_number=claim_number,
            claimed_amount=claimed_amount,
            status=ClaimStatus.DRAFT.value,
            documents_submitted=documents or [],
            notes=notes,
        )

        self.db.add(claim)
        await self.db.commit()
        await self.db.refresh(claim)

        return claim

    async def submit_claim(
        self,
        claim_id: UUID,
        documents: list[str] | None = None,
        submitted_by: str | None = None,
    ) -> InsuranceClaim:
        """
        Submit a claim to insurance/TPA.

        Args:
            claim_id: Claim ID
            documents: Additional documents to attach
            submitted_by: Name of person submitting

        Returns:
            Updated InsuranceClaim object
        """
        result = await self.db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise ValueError("Claim not found")

        if claim.status not in [ClaimStatus.DRAFT.value]:
            raise ValueError(f"Cannot submit claim with status: {claim.status}")

        # Update claim
        claim.status = ClaimStatus.SUBMITTED.value
        claim.submitted_at = datetime.now()
        claim.submitted_by = submitted_by

        if documents:
            existing_docs = claim.documents_submitted or []
            claim.documents_submitted = existing_docs + documents

        await self.db.commit()
        await self.db.refresh(claim)

        return claim

    async def update_claim_status(
        self,
        claim_id: UUID,
        status: ClaimStatus,
        approved_amount: Decimal | None = None,
        settled_amount: Decimal | None = None,
        claim_number: str | None = None,
        rejection_reason: str | None = None,
        rejection_code: str | None = None,
        tpa_reference: str | None = None,
        notes: str | None = None,
    ) -> InsuranceClaim:
        """
        Update claim status and details.

        Args:
            claim_id: Claim ID
            status: New status
            approved_amount: Approved amount (if applicable)
            settled_amount: Settled amount (if applicable)
            claim_number: TPA/Insurance claim number
            rejection_reason: Reason for rejection (if rejected)
            rejection_code: Rejection code from TPA
            tpa_reference: TPA reference number
            notes: Processing notes

        Returns:
            Updated InsuranceClaim object
        """
        result = await self.db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise ValueError("Claim not found")

        # Update status
        claim.status = status.value

        # Update timestamps based on status
        now = datetime.now()
        if status == ClaimStatus.UNDER_REVIEW:
            claim.acknowledged_at = now
        elif status == ClaimStatus.APPROVED or status == ClaimStatus.PARTIALLY_APPROVED:
            claim.approved_at = now
            if approved_amount is not None:
                claim.approved_amount = approved_amount
        elif status == ClaimStatus.SETTLED:
            claim.settled_at = now
            if settled_amount is not None:
                claim.settled_amount = settled_amount
        elif status == ClaimStatus.REJECTED:
            claim.rejection_reason = rejection_reason
            claim.rejection_code = rejection_code

        # Update other fields
        if claim_number:
            claim.claim_number = claim_number
        if tpa_reference:
            claim.tpa_reference_number = tpa_reference
        if notes:
            claim.processing_notes = notes

        # Calculate patient liability
        if claim.approved_amount > 0:
            claim.patient_liability = claim.claimed_amount - claim.approved_amount

        await self.db.commit()
        await self.db.refresh(claim)

        return claim

    async def appeal_claim(
        self,
        claim_id: UUID,
        appeal_notes: str,
    ) -> InsuranceClaim:
        """
        Appeal a rejected claim.

        Args:
            claim_id: Claim ID
            appeal_notes: Reason for appeal

        Returns:
            Updated InsuranceClaim object
        """
        result = await self.db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise ValueError("Claim not found")

        if claim.status != ClaimStatus.REJECTED.value:
            raise ValueError("Can only appeal rejected claims")

        claim.status = ClaimStatus.APPEALED.value
        claim.appeal_submitted_at = datetime.now()
        claim.appeal_notes = appeal_notes

        await self.db.commit()
        await self.db.refresh(claim)

        return claim

    async def generate_preauth_number(self, insurance_company_id: UUID) -> str:
        """
        Generate internal pre-authorization number.

        Format: PA-YYYYMMDD-COMPANY-XXXX
        """
        today = date.today()

        # Get company code
        result = await self.db.execute(
            select(InsuranceCompany).where(InsuranceCompany.id == insurance_company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError("Insurance company not found")

        prefix = f"PA-{today.strftime('%Y%m%d')}-{company.code}"

        # Get count for today
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(PreAuthorization.id)).where(
                PreAuthorization.internal_ref_number.like(f"{prefix}%")
            )
        )
        count = result.scalar() or 0

        return f"{prefix}-{count + 1:04d}"

    async def create_preauthorization(
        self,
        patient_id: UUID,
        patient_insurance_id: UUID,
        procedure_name: str,
        requested_amount: Decimal,
        requested_date: date,
        procedure_id: UUID | None = None,
        procedure_code: str | None = None,
        diagnosis: str | None = None,
        planned_procedure_date: date | None = None,
        documents: list[str] | None = None,
        notes: str | None = None,
        requested_by: str | None = None,
    ) -> PreAuthorization:
        """
        Create a pre-authorization request.

        Args:
            patient_id: Patient ID
            patient_insurance_id: Patient's insurance policy ID
            procedure_name: Name of procedure
            requested_amount: Estimated cost
            requested_date: Date of request
            procedure_id: Linked procedure ID (if exists)
            procedure_code: CPT/ICD code
            diagnosis: Diagnosis requiring procedure
            planned_procedure_date: When procedure is planned
            documents: Supporting documents
            notes: Additional notes
            requested_by: Doctor/staff requesting

        Returns:
            Created PreAuthorization object
        """
        # Verify patient insurance
        result = await self.db.execute(
            select(PatientInsurance)
            .options(selectinload(PatientInsurance.insurance_company))
            .where(PatientInsurance.id == patient_insurance_id)
        )
        patient_insurance = result.scalar_one_or_none()
        if not patient_insurance:
            raise ValueError("Patient insurance not found")

        if not patient_insurance.is_valid:
            raise ValueError("Patient insurance is not valid")

        # Check if pre-auth is required
        company = patient_insurance.insurance_company
        if company.preauth_required and company.preauth_threshold:
            if requested_amount < company.preauth_threshold:
                raise ValueError(
                    f"Pre-authorization not required for amounts below {company.preauth_threshold}"
                )

        # Generate internal ref number
        ref_number = await self.generate_preauth_number(patient_insurance.insurance_company_id)

        # Create pre-auth
        preauth = PreAuthorization(
            patient_id=patient_id,
            patient_insurance_id=patient_insurance_id,
            insurance_company_id=patient_insurance.insurance_company_id,
            procedure_id=procedure_id,
            internal_ref_number=ref_number,
            procedure_name=procedure_name,
            procedure_code=procedure_code,
            diagnosis=diagnosis,
            requested_amount=requested_amount,
            requested_date=requested_date,
            planned_procedure_date=planned_procedure_date,
            documents_submitted=documents or [],
            notes=notes,
            requested_by=requested_by,
            status=PreAuthStatus.PENDING.value,
        )

        self.db.add(preauth)
        await self.db.commit()
        await self.db.refresh(preauth)

        return preauth

    async def submit_preauthorization(
        self,
        preauth_id: UUID,
        documents: list[str] | None = None,
    ) -> PreAuthorization:
        """
        Submit pre-authorization request to insurance/TPA.

        Args:
            preauth_id: Pre-authorization ID
            documents: Additional documents

        Returns:
            Updated PreAuthorization object
        """
        result = await self.db.execute(
            select(PreAuthorization).where(PreAuthorization.id == preauth_id)
        )
        preauth = result.scalar_one_or_none()
        if not preauth:
            raise ValueError("Pre-authorization not found")

        if preauth.status != PreAuthStatus.PENDING.value:
            raise ValueError(f"Cannot submit pre-auth with status: {preauth.status}")

        preauth.status = PreAuthStatus.REQUESTED.value
        preauth.submitted_at = datetime.now()

        if documents:
            existing_docs = preauth.documents_submitted or []
            preauth.documents_submitted = existing_docs + documents

        await self.db.commit()
        await self.db.refresh(preauth)

        return preauth

    async def update_preauth_status(
        self,
        preauth_id: UUID,
        status: PreAuthStatus,
        auth_number: str | None = None,
        approved_amount: Decimal | None = None,
        valid_from: date | None = None,
        valid_to: date | None = None,
        rejection_reason: str | None = None,
        rejection_code: str | None = None,
        tpa_notes: str | None = None,
    ) -> PreAuthorization:
        """
        Update pre-authorization status.

        Args:
            preauth_id: Pre-authorization ID
            status: New status
            auth_number: Authorization number from TPA
            approved_amount: Approved amount
            valid_from: Validity start date
            valid_to: Validity end date
            rejection_reason: Reason for rejection
            rejection_code: Rejection code
            tpa_notes: Notes from TPA

        Returns:
            Updated PreAuthorization object
        """
        result = await self.db.execute(
            select(PreAuthorization).where(PreAuthorization.id == preauth_id)
        )
        preauth = result.scalar_one_or_none()
        if not preauth:
            raise ValueError("Pre-authorization not found")

        preauth.status = status.value

        # Update based on status
        now = datetime.now()
        if status == PreAuthStatus.APPROVED or status == PreAuthStatus.PARTIALLY_APPROVED:
            preauth.approved_at = now
            if auth_number:
                preauth.auth_number = auth_number
            if approved_amount is not None:
                preauth.approved_amount = approved_amount
            if valid_from:
                preauth.valid_from = valid_from
            if valid_to:
                preauth.valid_to = valid_to
        elif status == PreAuthStatus.REJECTED:
            preauth.rejected_at = now
            preauth.rejection_reason = rejection_reason
            preauth.rejection_code = rejection_code

        if tpa_notes:
            preauth.tpa_notes = tpa_notes

        await self.db.commit()
        await self.db.refresh(preauth)

        return preauth

    async def check_preauth_validity(self, preauth_id: UUID) -> dict[str, Any]:
        """
        Check if pre-authorization is valid and can be used for claims.

        Args:
            preauth_id: Pre-authorization ID

        Returns:
            Dictionary with validity status and details
        """
        result = await self.db.execute(
            select(PreAuthorization).where(PreAuthorization.id == preauth_id)
        )
        preauth = result.scalar_one_or_none()
        if not preauth:
            raise ValueError("Pre-authorization not found")

        is_valid = preauth.is_valid
        reasons = []

        if preauth.status != PreAuthStatus.APPROVED.value:
            reasons.append(f"Status is {preauth.status}, not approved")

        if not preauth.valid_from or not preauth.valid_to:
            reasons.append("Validity dates not set")
        else:
            today = date.today()
            if today < preauth.valid_from:
                reasons.append(f"Not valid until {preauth.valid_from}")
            if today > preauth.valid_to:
                reasons.append(f"Expired on {preauth.valid_to}")

        return {
            "is_valid": is_valid,
            "preauth_id": preauth_id,
            "auth_number": preauth.auth_number,
            "approved_amount": float(preauth.approved_amount) if preauth.approved_amount else 0,
            "valid_from": preauth.valid_from,
            "valid_to": preauth.valid_to,
            "status": preauth.status,
            "reasons": reasons if not is_valid else [],
        }

    async def get_claim_summary(
        self,
        patient_id: UUID | None = None,
        insurance_company_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """
        Get summary of claims for reporting.

        Args:
            patient_id: Filter by patient
            insurance_company_id: Filter by insurance company
            date_from: Filter by date range start
            date_to: Filter by date range end

        Returns:
            Summary statistics
        """
        query = select(InsuranceClaim)

        if patient_id:
            query = query.where(InsuranceClaim.patient_id == patient_id)
        if insurance_company_id:
            query = query.where(InsuranceClaim.insurance_company_id == insurance_company_id)
        if date_from:
            query = query.where(InsuranceClaim.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.where(InsuranceClaim.created_at <= datetime.combine(date_to, datetime.max.time()))

        result = await self.db.execute(query)
        claims = result.scalars().all()

        total_claims = len(claims)
        total_claimed = sum(c.claimed_amount for c in claims)
        total_approved = sum(c.approved_amount for c in claims)
        total_settled = sum(c.settled_amount for c in claims)

        pending_count = sum(1 for c in claims if c.status in [ClaimStatus.DRAFT.value, ClaimStatus.SUBMITTED.value, ClaimStatus.UNDER_REVIEW.value])
        approved_count = sum(1 for c in claims if c.status in [ClaimStatus.APPROVED.value, ClaimStatus.PARTIALLY_APPROVED.value])
        rejected_count = sum(1 for c in claims if c.status == ClaimStatus.REJECTED.value)

        return {
            "total_claims": total_claims,
            "total_claimed": float(total_claimed),
            "total_approved": float(total_approved),
            "total_settled": float(total_settled),
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
        }
