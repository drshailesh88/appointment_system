"""
Tests for insurance claims service.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.insurance import (
    ClaimStatus,
    CoverageType,
    InsuranceClaim,
    InsuranceCompany,
    PatientInsurance,
    PreAuthStatus,
    PreAuthorization,
)
from app.services.insurance_claims import InsuranceClaimsService


@pytest.mark.asyncio
class TestInsuranceClaimsService:
    """Test insurance claims service."""

    @pytest.mark.asyncio


    async def test_generate_claim_number(self, async_session):
        """Test claim number generation."""
        # Create test insurance company
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
        )
        async_session.add(company)
        await async_session.commit()
        await async_session.refresh(company)

        service = InsuranceClaimsService(async_session)
        claim_number = await service.generate_claim_number(company.id)

        today = date.today()
        expected_prefix = f"CLM-{today.strftime('%Y%m%d')}-TEST"
        assert claim_number.startswith(expected_prefix)
        assert claim_number.endswith("-0001")

    @pytest.mark.asyncio


    async def test_create_claim_success(self, async_session, test_patient, test_invoice):
        """Test creating a valid insurance claim."""
        # Create insurance company and patient insurance
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
        )
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123456",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        # Create claim
        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
            notes="Test claim",
        )

        assert claim is not None
        assert claim.patient_id == test_patient.id
        assert claim.claimed_amount == Decimal("10000.00")
        assert claim.status == ClaimStatus.DRAFT.value
        assert claim.internal_claim_number is not None

    @pytest.mark.asyncio


    async def test_create_claim_invalid_insurance(self, async_session, test_patient, test_invoice):
        """Test creating claim with invalid insurance ID."""
        service = InsuranceClaimsService(async_session)

        with pytest.raises(ValueError, match="Patient insurance not found"):
            await service.create_claim(
                patient_id=test_patient.id,
                invoice_id=test_invoice.id,
                patient_insurance_id=uuid4(),  # Non-existent
                claimed_amount=Decimal("10000.00"),
            )

    @pytest.mark.asyncio


    async def test_create_claim_expired_insurance(self, async_session, test_patient, test_invoice):
        """Test creating claim with expired insurance."""
        # Create expired insurance
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
        )
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123456",
            valid_from=date(2020, 1, 1),
            valid_to=date(2021, 12, 31),  # Expired
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)

        with pytest.raises(ValueError, match="not valid"):
            await service.create_claim(
                patient_id=test_patient.id,
                invoice_id=test_invoice.id,
                patient_insurance_id=patient_insurance.id,
                claimed_amount=Decimal("10000.00"),
            )

    @pytest.mark.asyncio


    async def test_submit_claim(self, async_session, test_patient, test_invoice):
        """Test submitting a claim."""
        # Setup
        company = InsuranceCompany(name="Test Insurance", code="TEST", is_active=True)
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        # Submit claim
        submitted_claim = await service.submit_claim(
            claim_id=claim.id,
            submitted_by="Dr. Test",
        )

        assert submitted_claim.status == ClaimStatus.SUBMITTED.value
        assert submitted_claim.submitted_at is not None
        assert submitted_claim.submitted_by == "Dr. Test"

    @pytest.mark.asyncio


    async def test_update_claim_status(self, async_session, test_patient, test_invoice):
        """Test updating claim status."""
        # Setup
        company = InsuranceCompany(name="Test Insurance", code="TEST", is_active=True)
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        # Update to approved
        updated_claim = await service.update_claim_status(
            claim_id=claim.id,
            status=ClaimStatus.APPROVED,
            approved_amount=Decimal("9000.00"),
            claim_number="INS-12345",
        )

        assert updated_claim.status == ClaimStatus.APPROVED.value
        assert updated_claim.approved_amount == Decimal("9000.00")
        assert updated_claim.claim_number == "INS-12345"
        assert updated_claim.approved_at is not None
        assert updated_claim.patient_liability == Decimal("1000.00")  # 10000 - 9000

    @pytest.mark.asyncio


    async def test_appeal_rejected_claim(self, async_session, test_patient, test_invoice):
        """Test appealing a rejected claim."""
        # Setup
        company = InsuranceCompany(name="Test Insurance", code="TEST", is_active=True)
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        # Reject claim
        await service.update_claim_status(
            claim_id=claim.id,
            status=ClaimStatus.REJECTED,
            rejection_reason="Insufficient documentation",
        )

        # Appeal
        appealed_claim = await service.appeal_claim(
            claim_id=claim.id,
            appeal_notes="Additional documents attached",
        )

        assert appealed_claim.status == ClaimStatus.APPEALED.value
        assert appealed_claim.appeal_submitted_at is not None
        assert appealed_claim.appeal_notes == "Additional documents attached"

    @pytest.mark.asyncio


    async def test_generate_preauth_number(self, async_session):
        """Test pre-auth number generation."""
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
        )
        async_session.add(company)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        preauth_number = await service.generate_preauth_number(company.id)

        today = date.today()
        expected_prefix = f"PA-{today.strftime('%Y%m%d')}-TEST"
        assert preauth_number.startswith(expected_prefix)
        assert preauth_number.endswith("-0001")

    @pytest.mark.asyncio


    async def test_create_preauthorization(self, async_session, test_patient):
        """Test creating pre-authorization."""
        # Setup
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
            preauth_required=True,
            preauth_threshold=Decimal("50000.00"),
        )
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        # Create pre-auth
        service = InsuranceClaimsService(async_session)
        preauth = await service.create_preauthorization(
            patient_id=test_patient.id,
            patient_insurance_id=patient_insurance.id,
            procedure_name="Angioplasty",
            requested_amount=Decimal("100000.00"),
            requested_date=date.today(),
            diagnosis="Coronary artery disease",
            requested_by="Dr. Cardiologist",
        )

        assert preauth is not None
        assert preauth.procedure_name == "Angioplasty"
        assert preauth.requested_amount == Decimal("100000.00")
        assert preauth.status == PreAuthStatus.PENDING.value
        assert preauth.internal_ref_number is not None

    @pytest.mark.asyncio


    async def test_preauth_below_threshold_fails(self, async_session, test_patient):
        """Test pre-auth below threshold is rejected."""
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
            preauth_required=True,
            preauth_threshold=Decimal("50000.00"),
        )
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)

        with pytest.raises(ValueError, match="not required"):
            await service.create_preauthorization(
                patient_id=test_patient.id,
                patient_insurance_id=patient_insurance.id,
                procedure_name="Minor Surgery",
                requested_amount=Decimal("30000.00"),  # Below threshold
                requested_date=date.today(),
            )

    @pytest.mark.asyncio


    async def test_submit_preauthorization(self, async_session, test_patient):
        """Test submitting pre-authorization."""
        # Setup
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
            preauth_required=True,
            preauth_threshold=Decimal("50000.00"),
        )
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        preauth = await service.create_preauthorization(
            patient_id=test_patient.id,
            patient_insurance_id=patient_insurance.id,
            procedure_name="Bypass Surgery",
            requested_amount=Decimal("200000.00"),
            requested_date=date.today(),
        )

        # Submit
        submitted_preauth = await service.submit_preauthorization(
            preauth_id=preauth.id,
        )

        assert submitted_preauth.status == PreAuthStatus.REQUESTED.value
        assert submitted_preauth.submitted_at is not None

    @pytest.mark.asyncio


    async def test_check_preauth_validity(self, async_session, test_patient):
        """Test checking pre-auth validity."""
        # Setup
        company = InsuranceCompany(
            name="Test Insurance",
            code="TEST",
            is_active=True,
        )
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        # Create and approve pre-auth
        preauth = PreAuthorization(
            patient_id=test_patient.id,
            patient_insurance_id=patient_insurance.id,
            insurance_company_id=company.id,
            internal_ref_number="PA-TEST-001",
            procedure_name="Test Procedure",
            requested_amount=Decimal("100000.00"),
            approved_amount=Decimal("90000.00"),
            requested_date=date.today(),
            status=PreAuthStatus.APPROVED.value,
            auth_number="AUTH-12345",
            valid_from=date.today(),
            valid_to=date(2027, 1, 31),
        )
        async_session.add(preauth)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        validity = await service.check_preauth_validity(preauth.id)

        assert validity["is_valid"] is True
        assert validity["auth_number"] == "AUTH-12345"
        assert validity["approved_amount"] == 90000.0

    @pytest.mark.asyncio


    async def test_get_claim_summary(self, async_session, test_patient, test_invoice):
        """Test getting claim summary."""
        # Setup
        company = InsuranceCompany(name="Test Insurance", code="TEST", is_active=True)
        async_session.add(company)
        await async_session.commit()

        patient_insurance = PatientInsurance(
            patient_id=test_patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date(2027, 12, 31),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        # Create multiple claims
        service = InsuranceClaimsService(async_session)

        claim1 = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )
        await service.update_claim_status(
            claim_id=claim1.id,
            status=ClaimStatus.APPROVED,
            approved_amount=Decimal("9000.00"),
        )

        claim2 = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=patient_insurance.id,
            claimed_amount=Decimal("5000.00"),
        )
        await service.update_claim_status(
            claim_id=claim2.id,
            status=ClaimStatus.REJECTED,
        )

        # Get summary
        summary = await service.get_claim_summary(patient_id=test_patient.id)

        assert summary["total_claims"] == 2
        assert summary["total_claimed"] == 15000.0
        assert summary["total_approved"] == 9000.0
        assert summary["approved_count"] == 1
        assert summary["rejected_count"] == 1
