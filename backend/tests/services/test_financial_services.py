"""
Comprehensive tests for financial services (Billing and Insurance).

This module tests:
1. Billing Service - GST calculations, invoices, discounts
2. Insurance Claims Service - Claims, pre-authorizations, TPA workflow
3. Edge cases - Zero amounts, large amounts, decimal precision, multiple policies
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.insurance import (
    ClaimStatus,
    CoverageType,
    InsuranceClaim,
    InsuranceCompany,
    PatientInsurance,
    PreAuthStatus,
    PreAuthorization,
)
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.patient import Patient
from app.models.user import User
from app.services.billing import BillingService, GSTType
from app.services.insurance_claims import InsuranceClaimsService


# ============================================================================
# ASYNC FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def async_engine():
    """Create async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_clinic(async_session: AsyncSession) -> Clinic:
    """Create a test clinic."""
    clinic = Clinic(
        id=uuid4(),
        name="Test Clinic",
        slug="test-clinic",
        address="123 Test Street",
        city="Mumbai",
        state="MH",
        pincode="400001",
        phone="+919876543210",
        email="test@clinic.com",
        subscription_tier="professional",
        gst_number="27AABCT1234F1Z5",  # Valid GSTIN
    )
    async_session.add(clinic)
    await async_session.commit()
    await async_session.refresh(clinic)
    return clinic


@pytest_asyncio.fixture
async def test_patient(async_session: AsyncSession, test_clinic: Clinic) -> Patient:
    """Create a test patient."""
    patient = Patient(
        id=uuid4(),
        clinic_id=test_clinic.id,
        name="Test Patient",
        phone="+919876543212",
        email="patient@test.com",
        gender="male",
        date_of_birth=date(1990, 1, 15),
        address="456 Patient Road",
        city="Mumbai",
        state="MH",  # Same state as clinic for intra-state GST
        pincode="400002",
        blood_group="O+",
    )
    async_session.add(patient)
    await async_session.commit()
    await async_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def test_doctor(async_session: AsyncSession, test_clinic: Clinic) -> Doctor:
    """Create a test doctor."""
    # Create user first
    user = User(
        id=uuid4(),
        email="doctor@test.com",
        phone="+919876543211",
        password_hash="hashed_password",
        name="Dr. Test Doctor",
        role="doctor",
        clinic_id=test_clinic.id,
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()

    doctor = Doctor(
        id=uuid4(),
        user_id=user.id,
        clinic_id=test_clinic.id,
        name="Dr. Test Doctor",
        specialization="General Medicine",
        qualification="MBBS, MD",
        registration_number="MH12345",
        consultation_fee=Decimal("500.00"),
        is_active=True,
    )
    async_session.add(doctor)
    await async_session.commit()
    await async_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def test_invoice(
    async_session: AsyncSession,
    test_clinic: Clinic,
    test_patient: Patient,
    test_doctor: Doctor,
) -> Invoice:
    """Create a test invoice."""
    invoice = Invoice(
        id=uuid4(),
        invoice_number="INV-2026-001",
        clinic_id=test_clinic.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        invoice_date=date.today(),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        total_amount=Decimal("1180.00"),
        status=InvoiceStatus.PENDING.value,
    )
    async_session.add(invoice)
    await async_session.commit()
    await async_session.refresh(invoice)
    return invoice


@pytest_asyncio.fixture
async def test_insurance_company(async_session: AsyncSession) -> InsuranceCompany:
    """Create a test insurance company."""
    company = InsuranceCompany(
        id=uuid4(),
        name="Star Health Insurance",
        code="STAR",
        contact_email="claims@starhealth.com",
        contact_phone="+911234567890",
        tpa_name="Medi Assist",
        cashless_available=True,
        preauth_required=True,
        preauth_threshold=Decimal("50000.00"),
        is_active=True,
    )
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)
    return company


@pytest_asyncio.fixture
async def test_patient_insurance(
    async_session: AsyncSession,
    test_patient: Patient,
    test_insurance_company: InsuranceCompany,
) -> PatientInsurance:
    """Create a test patient insurance policy."""
    insurance = PatientInsurance(
        id=uuid4(),
        patient_id=test_patient.id,
        insurance_company_id=test_insurance_company.id,
        policy_number="POL-2026-12345",
        valid_from=date.today() - timedelta(days=30),
        valid_to=date.today() + timedelta(days=335),  # ~1 year
        coverage_type=CoverageType.INDIVIDUAL.value,
        sum_insured=Decimal("500000.00"),
        copay_percentage=Decimal("10.00"),
        deductible_amount=Decimal("5000.00"),
        is_primary=True,
        is_active=True,
    )
    async_session.add(insurance)
    await async_session.commit()
    await async_session.refresh(insurance)
    return insurance


# ============================================================================
# BILLING SERVICE TESTS
# ============================================================================


class TestGSTCalculation:
    """Test GST calculation logic."""

    def test_intra_state_gst(self):
        """Test CGST+SGST for intra-state transaction."""
        result = BillingService.calculate_gst(
            amount=Decimal("10000.00"),
            clinic_state="MH",
            patient_state="MH",
            is_exempt=False,
        )

        assert result["gst_type"] == GSTType.INTRA_STATE.value
        assert result["cgst"] == Decimal("900.00")  # 9%
        assert result["sgst"] == Decimal("900.00")  # 9%
        assert result["igst"] == Decimal("0.00")
        assert result["total_tax"] == Decimal("1800.00")  # 18% total

    def test_inter_state_gst(self):
        """Test IGST for inter-state transaction."""
        result = BillingService.calculate_gst(
            amount=Decimal("10000.00"),
            clinic_state="MH",
            patient_state="KA",
            is_exempt=False,
        )

        assert result["gst_type"] == GSTType.INTER_STATE.value
        assert result["cgst"] == Decimal("0.00")
        assert result["sgst"] == Decimal("0.00")
        assert result["igst"] == Decimal("1800.00")  # 18%
        assert result["total_tax"] == Decimal("1800.00")

    def test_exempt_service(self):
        """Test GST exempt service."""
        result = BillingService.calculate_gst(
            amount=Decimal("10000.00"),
            clinic_state="MH",
            patient_state="MH",
            is_exempt=True,
        )

        assert result["gst_type"] == GSTType.EXEMPT.value
        assert result["cgst"] == Decimal("0.00")
        assert result["sgst"] == Decimal("0.00")
        assert result["igst"] == Decimal("0.00")
        assert result["total_tax"] == Decimal("0.00")

    def test_custom_gst_rate(self):
        """Test custom GST rate."""
        result = BillingService.calculate_gst(
            amount=Decimal("10000.00"),
            clinic_state="MH",
            patient_state="MH",
            custom_rate=Decimal("12.00"),  # 12% instead of 18%
        )

        assert result["cgst"] == Decimal("600.00")  # 6%
        assert result["sgst"] == Decimal("600.00")  # 6%
        assert result["total_tax"] == Decimal("1200.00")

    def test_case_insensitive_state_codes(self):
        """Test that state codes are case-insensitive."""
        result1 = BillingService.calculate_gst(
            amount=Decimal("1000.00"),
            clinic_state="mh",
            patient_state="MH",
        )

        result2 = BillingService.calculate_gst(
            amount=Decimal("1000.00"),
            clinic_state="MH",
            patient_state="mh",
        )

        assert result1["gst_type"] == result2["gst_type"] == GSTType.INTRA_STATE.value

    def test_decimal_precision_paisa(self):
        """Test decimal precision handling (paisa)."""
        # Test amount that would result in decimal paisa
        result = BillingService.calculate_gst(
            amount=Decimal("1234.56"),
            clinic_state="MH",
            patient_state="MH",
        )

        # 9% CGST of 1234.56 = 111.1104, should round to 111.11
        assert result["cgst"] == Decimal("111.11")
        assert result["sgst"] == Decimal("111.11")
        assert result["total_tax"] == Decimal("222.22")

    def test_zero_amount(self):
        """Test GST calculation with zero amount."""
        result = BillingService.calculate_gst(
            amount=Decimal("0.00"),
            clinic_state="MH",
            patient_state="MH",
        )

        assert result["cgst"] == Decimal("0.00")
        assert result["sgst"] == Decimal("0.00")
        assert result["total_tax"] == Decimal("0.00")

    def test_large_amount_crore_range(self):
        """Test GST calculation with large amounts (crore range)."""
        # 1 crore = 10,000,000
        result = BillingService.calculate_gst(
            amount=Decimal("10000000.00"),
            clinic_state="MH",
            patient_state="MH",
        )

        # 9% of 1 crore = 900,000
        assert result["cgst"] == Decimal("900000.00")
        assert result["sgst"] == Decimal("900000.00")
        assert result["total_tax"] == Decimal("1800000.00")

    def test_lakh_range_amount(self):
        """Test GST calculation with lakh range amounts."""
        # 5 lakh = 500,000
        result = BillingService.calculate_gst(
            amount=Decimal("500000.00"),
            clinic_state="KA",
            patient_state="TN",  # Inter-state
        )

        # 18% of 5 lakh = 90,000
        assert result["igst"] == Decimal("90000.00")
        assert result["total_tax"] == Decimal("90000.00")


class TestInvoiceTotalsCalculation:
    """Test invoice totals calculation."""

    def test_invoice_totals_without_discount(self):
        """Test invoice calculation without discount."""
        items = [
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="Consultation",
                quantity=1,
                unit_price=Decimal("1000.00"),
                tax_rate=Decimal("18.00"),
                subtotal=Decimal("1000.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("1000.00"),
            ),
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="ECG",
                quantity=1,
                unit_price=Decimal("500.00"),
                tax_rate=Decimal("18.00"),
                subtotal=Decimal("500.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("500.00"),
            ),
        ]

        result = BillingService.calculate_invoice_totals(
            items=items,
            clinic_state="MH",
            patient_state="MH",
        )

        assert result["subtotal"] == Decimal("1500.00")
        assert result["discount_amount"] == Decimal("0.00")
        assert result["taxable_amount"] == Decimal("1500.00")
        assert result["tax_amount"] == Decimal("270.00")  # 18% of 1500
        assert result["total_amount"] == Decimal("1770.00")

    def test_invoice_totals_with_discount(self):
        """Test invoice calculation with discount."""
        items = [
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="Consultation",
                quantity=1,
                unit_price=Decimal("1000.00"),
                tax_rate=Decimal("18.00"),
                subtotal=Decimal("1000.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("1000.00"),
            ),
        ]

        result = BillingService.calculate_invoice_totals(
            items=items,
            clinic_state="MH",
            patient_state="MH",
            discount_amount=Decimal("200.00"),
        )

        assert result["subtotal"] == Decimal("1000.00")
        assert result["discount_amount"] == Decimal("200.00")
        assert result["taxable_amount"] == Decimal("800.00")
        assert result["tax_amount"] == Decimal("144.00")  # 18% of 800
        assert result["total_amount"] == Decimal("944.00")

    def test_invoice_totals_inter_state(self):
        """Test invoice calculation for inter-state."""
        items = [
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="Surgery",
                quantity=1,
                unit_price=Decimal("50000.00"),
                tax_rate=Decimal("18.00"),
                subtotal=Decimal("50000.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("50000.00"),
            ),
        ]

        result = BillingService.calculate_invoice_totals(
            items=items,
            clinic_state="MH",
            patient_state="KA",
        )

        assert result["gst_type"] == GSTType.INTER_STATE.value
        assert result["cgst_amount"] == Decimal("0.00")
        assert result["sgst_amount"] == Decimal("0.00")
        assert result["igst_amount"] == Decimal("9000.00")  # 18% of 50000

    def test_invoice_totals_multiple_line_items(self):
        """Test invoice with multiple line items at different tax rates."""
        items = [
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="Consultation (Exempt)",
                quantity=1,
                unit_price=Decimal("1000.00"),
                tax_rate=Decimal("0.00"),  # Exempt
                subtotal=Decimal("1000.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("1000.00"),
            ),
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="Medicine",
                quantity=2,
                unit_price=Decimal("500.00"),
                tax_rate=Decimal("12.00"),  # 12% GST
                subtotal=Decimal("1000.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("1000.00"),
            ),
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="Equipment Rental",
                quantity=1,
                unit_price=Decimal("2000.00"),
                tax_rate=Decimal("18.00"),  # 18% GST
                subtotal=Decimal("2000.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("2000.00"),
            ),
        ]

        result = BillingService.calculate_invoice_totals(
            items=items,
            clinic_state="MH",
            patient_state="MH",
        )

        assert result["subtotal"] == Decimal("4000.00")
        # Tax calculation: 0% on 1000 + 12% on 1000 + 18% on 2000
        # = 0 + 108 + 324 = 432 (split into CGST+SGST)
        assert result["tax_amount"] == Decimal("432.00")

    def test_invoice_discount_exceeds_subtotal(self):
        """Test invoice where discount exceeds subtotal."""
        items = [
            InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description="Consultation",
                quantity=1,
                unit_price=Decimal("500.00"),
                tax_rate=Decimal("18.00"),
                subtotal=Decimal("500.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("500.00"),
            ),
        ]

        result = BillingService.calculate_invoice_totals(
            items=items,
            clinic_state="MH",
            patient_state="MH",
            discount_amount=Decimal("1000.00"),  # More than subtotal
        )

        # Taxable amount should be 0, not negative
        assert result["taxable_amount"] == Decimal("0.00")
        assert result["tax_amount"] == Decimal("0.00")
        assert result["total_amount"] == Decimal("0.00")


class TestInsuranceSplit:
    """Test insurance vs patient portion calculations."""

    def test_no_copay_no_deductible(self):
        """Test split with no copay or deductible."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
        )

        assert result["patient_portion"] == Decimal("0.00")
        assert result["insurance_portion"] == Decimal("10000.00")
        assert result["patient_deductible"] == Decimal("0.00")
        assert result["patient_copay"] == Decimal("0.00")

    def test_with_copay(self):
        """Test split with 10% copay."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
            copay_percentage=Decimal("10.00"),
        )

        assert result["patient_portion"] == Decimal("1000.00")  # 10%
        assert result["insurance_portion"] == Decimal("9000.00")  # 90%
        assert result["patient_deductible"] == Decimal("0.00")
        assert result["patient_copay"] == Decimal("1000.00")

    def test_with_deductible(self):
        """Test split with deductible."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
            deductible=Decimal("2000.00"),
        )

        assert result["patient_deductible"] == Decimal("2000.00")
        assert result["patient_copay"] == Decimal("0.00")
        assert result["insurance_portion"] == Decimal("8000.00")
        assert result["patient_portion"] == Decimal("2000.00")

    def test_with_copay_and_deductible(self):
        """Test split with both copay and deductible."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
            copay_percentage=Decimal("10.00"),
            deductible=Decimal("1000.00"),
        )

        # Deductible: 1000
        # Remaining: 9000
        # Copay (10% of 9000): 900
        # Insurance: 8100
        # Patient total: 1000 + 900 = 1900

        assert result["patient_deductible"] == Decimal("1000.00")
        assert result["patient_copay"] == Decimal("900.00")
        assert result["insurance_portion"] == Decimal("8100.00")
        assert result["patient_portion"] == Decimal("1900.00")

    def test_with_partial_insurance_approval(self):
        """Test when insurance approves less than claimed."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
            copay_percentage=Decimal("10.00"),
            approved_amount=Decimal("7000.00"),  # Only approved 7k
        )

        # Copay (10%): 1000
        # Insurance can cover: 9000
        # But only approved: 7000
        # Patient additional: 2000
        # Patient total: 1000 + 2000 = 3000

        assert result["patient_copay"] == Decimal("1000.00")
        assert result["patient_additional"] == Decimal("2000.00")
        assert result["insurance_portion"] == Decimal("7000.00")
        assert result["patient_portion"] == Decimal("3000.00")

    def test_deductible_exceeds_total(self):
        """Test when deductible exceeds total amount."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("5000.00"),
            deductible=Decimal("10000.00"),  # Deductible higher than total
        )

        # Patient pays entire amount (limited to total)
        assert result["patient_deductible"] == Decimal("5000.00")
        assert result["patient_copay"] == Decimal("0.00")
        assert result["insurance_portion"] == Decimal("0.00")
        assert result["patient_portion"] == Decimal("5000.00")

    def test_high_copay_percentage(self):
        """Test with high copay percentage (50%)."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("100000.00"),
            copay_percentage=Decimal("50.00"),  # 50% copay
        )

        assert result["patient_copay"] == Decimal("50000.00")
        assert result["insurance_portion"] == Decimal("50000.00")
        assert result["patient_portion"] == Decimal("50000.00")


class TestHSNCodes:
    """Test HSN code retrieval."""

    def test_consultation_hsn(self):
        """Test HSN code for consultation."""
        code = BillingService.get_hsn_code("consultation")
        assert code == "9993"

    def test_diagnostic_hsn(self):
        """Test HSN code for diagnostic."""
        code = BillingService.get_hsn_code("diagnostic")
        assert code == "9993"

    def test_ambulance_hsn(self):
        """Test HSN code for ambulance."""
        code = BillingService.get_hsn_code("ambulance")
        assert code == "9994"

    def test_unknown_service_default_hsn(self):
        """Test default HSN code for unknown service."""
        code = BillingService.get_hsn_code("unknown_service")
        assert code == "9993"

    def test_case_insensitive_hsn_lookup(self):
        """Test HSN code lookup is case-insensitive."""
        assert BillingService.get_hsn_code("CONSULTATION") == "9993"
        assert BillingService.get_hsn_code("Ambulance") == "9994"


class TestGSTINValidation:
    """Test GSTIN validation."""

    def test_valid_gstin(self):
        """Test valid GSTIN format."""
        assert BillingService.validate_gstin("27AABCT1234F1Z5") is True
        assert BillingService.validate_gstin("29AABCT1234F1Z5") is True

    def test_invalid_gstin_length(self):
        """Test GSTIN with wrong length."""
        assert BillingService.validate_gstin("27AABCT1234F1Z") is False  # Too short
        assert BillingService.validate_gstin("27AABCT1234F1Z55") is False  # Too long

    def test_invalid_gstin_format(self):
        """Test GSTIN with invalid format."""
        assert BillingService.validate_gstin("XXAABCT1234F1Z5") is False  # Should start with digits
        assert BillingService.validate_gstin("27AABCT1234F1X5") is False  # Should have Z at position 13

    def test_none_gstin(self):
        """Test None GSTIN."""
        assert BillingService.validate_gstin(None) is False

    def test_empty_gstin(self):
        """Test empty GSTIN."""
        assert BillingService.validate_gstin("") is False

    def test_lowercase_gstin(self):
        """Test lowercase GSTIN (should be validated after uppercase conversion)."""
        assert BillingService.validate_gstin("27aabct1234f1z5") is True


class TestServiceExemptions:
    """Test GST exemption checks."""

    def test_hospital_room_below_threshold(self):
        """Test hospital room charges below Rs 5000 are exempt."""
        assert BillingService.is_service_exempt("hospital_room_charges", Decimal("4000.00")) is True

    def test_hospital_room_above_threshold(self):
        """Test hospital room charges above Rs 5000 are not exempt."""
        assert BillingService.is_service_exempt("hospital_room_charges", Decimal("6000.00")) is False

    def test_hospital_room_exactly_at_threshold(self):
        """Test hospital room charges exactly at Rs 5000."""
        assert BillingService.is_service_exempt("hospital_room_charges", Decimal("5000.00")) is False

    def test_diagnostic_tests_exempt(self):
        """Test diagnostic tests are exempt."""
        assert BillingService.is_service_exempt("diagnostic_tests_prescribed") is True

    def test_ambulance_exempt(self):
        """Test ambulance services are exempt."""
        assert BillingService.is_service_exempt("transportation_patient") is True

    def test_non_exempt_service(self):
        """Test non-exempt service."""
        assert BillingService.is_service_exempt("consultation") is False


class TestInvoiceFormatting:
    """Test invoice data formatting for PDF generation."""

    def test_format_gst_invoice_data(self):
        """Test formatting invoice data for GST-compliant PDF."""
        # Create mock objects
        invoice = MagicMock(spec=Invoice)
        invoice.invoice_number = "INV-2026-001"
        invoice.invoice_date = date(2026, 1, 5)
        invoice.due_date = date(2026, 2, 5)
        invoice.subtotal = Decimal("10000.00")
        invoice.discount_amount = Decimal("500.00")
        invoice.discount_reason = "Senior citizen discount"
        invoice.cgst_amount = Decimal("855.00")
        invoice.sgst_amount = Decimal("855.00")
        invoice.igst_amount = Decimal("0.00")
        invoice.tax_amount = Decimal("1710.00")
        invoice.total_amount = Decimal("11210.00")
        invoice.paid_amount = Decimal("0.00")
        invoice.balance_due = Decimal("11210.00")
        invoice.status = "pending"
        invoice.notes = "Test invoice"
        invoice.gstin = "27AABCT1234F1Z5"

        # Mock invoice items
        item = MagicMock(spec=InvoiceItem)
        item.description = "Consultation"
        item.hsn_code = "9993"
        item.quantity = 1
        item.unit_price = Decimal("10000.00")
        item.subtotal = Decimal("10000.00")
        item.tax_rate = Decimal("18.00")
        item.tax_amount = Decimal("1710.00")
        item.total = Decimal("11710.00")
        invoice.items = [item]

        clinic = MagicMock(spec=Clinic)
        clinic.name = "Test Clinic"
        clinic.address = "123 Test St"
        clinic.city = "Mumbai"
        clinic.state = "MH"
        clinic.pincode = "400001"
        clinic.gst_number = "27AABCT1234F1Z5"
        clinic.phone = "+919876543210"

        patient = MagicMock(spec=Patient)
        patient.full_name = "Test Patient"
        patient.address = "456 Patient Rd"
        patient.city = "Mumbai"
        patient.state = "MH"
        patient.pincode = "400002"
        patient.phone = "+919876543212"

        result = BillingService.format_gst_invoice_data(invoice, clinic, patient)

        assert result["invoice_number"] == "INV-2026-001"
        assert result["clinic_name"] == "Test Clinic"
        assert result["patient_name"] == "Test Patient"
        assert result["is_intra_state"] is True
        assert len(result["items"]) == 1
        assert result["items"][0]["description"] == "Consultation"


# ============================================================================
# INSURANCE CLAIMS SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
class TestInsuranceClaimsService:
    """Test insurance claims service."""

    async def test_generate_claim_number(self, async_session: AsyncSession):
        """Test claim number generation."""
        # Create test insurance company
        company = InsuranceCompany(
            id=uuid4(),
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

    async def test_generate_multiple_claim_numbers_same_day(self, async_session: AsyncSession):
        """Test generating multiple claim numbers on the same day increments correctly."""
        company = InsuranceCompany(
            id=uuid4(),
            name="Test Insurance",
            code="TEST",
            is_active=True,
        )
        async_session.add(company)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)

        # Generate first claim number
        claim_number1 = await service.generate_claim_number(company.id)
        assert claim_number1.endswith("-0001")

        # Create a claim to increment the count
        patient = Patient(
            id=uuid4(),
            clinic_id=uuid4(),
            name="Test Patient",
            phone="+911234567890",
            gender="male",
        )
        async_session.add(patient)

        invoice = Invoice(
            id=uuid4(),
            invoice_number="INV-001",
            clinic_id=uuid4(),
            patient_id=patient.id,
            invoice_date=date.today(),
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )
        async_session.add(invoice)

        patient_insurance = PatientInsurance(
            id=uuid4(),
            patient_id=patient.id,
            insurance_company_id=company.id,
            policy_number="POL123",
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=365),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        claim = InsuranceClaim(
            id=uuid4(),
            patient_id=patient.id,
            invoice_id=invoice.id,
            patient_insurance_id=patient_insurance.id,
            insurance_company_id=company.id,
            internal_claim_number=claim_number1,
            claimed_amount=Decimal("1000.00"),
            status=ClaimStatus.DRAFT.value,
        )
        async_session.add(claim)
        await async_session.commit()

        # Generate second claim number
        claim_number2 = await service.generate_claim_number(company.id)
        assert claim_number2.endswith("-0002")

    async def test_create_claim_success(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test creating a valid insurance claim."""
        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
            notes="Test claim for surgery",
        )

        assert claim is not None
        assert claim.patient_id == test_patient.id
        assert claim.claimed_amount == Decimal("10000.00")
        assert claim.status == ClaimStatus.DRAFT.value
        assert claim.internal_claim_number is not None
        assert "CLM-" in claim.internal_claim_number

    async def test_create_claim_invalid_insurance(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
    ):
        """Test creating claim with invalid insurance ID."""
        service = InsuranceClaimsService(async_session)

        with pytest.raises(ValueError, match="Patient insurance not found"):
            await service.create_claim(
                patient_id=test_patient.id,
                invoice_id=test_invoice.id,
                patient_insurance_id=uuid4(),  # Non-existent
                claimed_amount=Decimal("10000.00"),
            )

    async def test_create_claim_expired_insurance(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_insurance_company: InsuranceCompany,
    ):
        """Test creating claim with expired insurance."""
        # Create expired insurance
        expired_insurance = PatientInsurance(
            id=uuid4(),
            patient_id=test_patient.id,
            insurance_company_id=test_insurance_company.id,
            policy_number="POL-EXPIRED",
            valid_from=date(2020, 1, 1),
            valid_to=date(2021, 12, 31),  # Expired
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            is_active=True,
        )
        async_session.add(expired_insurance)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)

        with pytest.raises(ValueError, match="not valid"):
            await service.create_claim(
                patient_id=test_patient.id,
                invoice_id=test_invoice.id,
                patient_insurance_id=expired_insurance.id,
                claimed_amount=Decimal("10000.00"),
            )

    async def test_submit_claim(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test submitting a claim."""
        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        # Submit claim
        submitted_claim = await service.submit_claim(
            claim_id=claim.id,
            submitted_by="Dr. Test",
            documents=["doc1.pdf", "doc2.pdf"],
        )

        assert submitted_claim.status == ClaimStatus.SUBMITTED.value
        assert submitted_claim.submitted_at is not None
        assert submitted_claim.submitted_by == "Dr. Test"
        assert len(submitted_claim.documents_submitted) == 2

    async def test_update_claim_status_to_approved(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test updating claim status to approved."""
        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        # Update to approved
        updated_claim = await service.update_claim_status(
            claim_id=claim.id,
            status=ClaimStatus.APPROVED,
            approved_amount=Decimal("9000.00"),
            claim_number="INS-12345",
            tpa_reference="TPA-REF-001",
        )

        assert updated_claim.status == ClaimStatus.APPROVED.value
        assert updated_claim.approved_amount == Decimal("9000.00")
        assert updated_claim.claim_number == "INS-12345"
        assert updated_claim.approved_at is not None
        assert updated_claim.patient_liability == Decimal("1000.00")  # 10000 - 9000
        assert updated_claim.tpa_reference_number == "TPA-REF-001"

    async def test_update_claim_status_to_rejected(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test updating claim status to rejected."""
        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        # Update to rejected
        updated_claim = await service.update_claim_status(
            claim_id=claim.id,
            status=ClaimStatus.REJECTED,
            rejection_reason="Insufficient documentation",
            rejection_code="E404",
        )

        assert updated_claim.status == ClaimStatus.REJECTED.value
        assert updated_claim.rejection_reason == "Insufficient documentation"
        assert updated_claim.rejection_code == "E404"

    async def test_appeal_rejected_claim(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test appealing a rejected claim."""
        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
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

    async def test_appeal_non_rejected_claim_fails(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test that appealing non-rejected claim fails."""
        service = InsuranceClaimsService(async_session)
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        with pytest.raises(ValueError, match="only appeal rejected claims"):
            await service.appeal_claim(
                claim_id=claim.id,
                appeal_notes="Should fail",
            )

    async def test_generate_preauth_number(self, async_session: AsyncSession):
        """Test pre-auth number generation."""
        company = InsuranceCompany(
            id=uuid4(),
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

    async def test_create_preauthorization(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_patient_insurance: PatientInsurance,
    ):
        """Test creating pre-authorization."""
        service = InsuranceClaimsService(async_session)
        preauth = await service.create_preauthorization(
            patient_id=test_patient.id,
            patient_insurance_id=test_patient_insurance.id,
            procedure_name="Angioplasty",
            requested_amount=Decimal("100000.00"),
            requested_date=date.today(),
            diagnosis="Coronary artery disease",
            procedure_code="CPT-12345",
            requested_by="Dr. Cardiologist",
        )

        assert preauth is not None
        assert preauth.procedure_name == "Angioplasty"
        assert preauth.requested_amount == Decimal("100000.00")
        assert preauth.status == PreAuthStatus.PENDING.value
        assert preauth.internal_ref_number is not None
        assert "PA-" in preauth.internal_ref_number

    async def test_preauth_below_threshold_fails(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_patient_insurance: PatientInsurance,
    ):
        """Test pre-auth below threshold is rejected."""
        service = InsuranceClaimsService(async_session)

        with pytest.raises(ValueError, match="not required"):
            await service.create_preauthorization(
                patient_id=test_patient.id,
                patient_insurance_id=test_patient_insurance.id,
                procedure_name="Minor Surgery",
                requested_amount=Decimal("30000.00"),  # Below 50000 threshold
                requested_date=date.today(),
            )

    async def test_submit_preauthorization(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_patient_insurance: PatientInsurance,
    ):
        """Test submitting pre-authorization."""
        service = InsuranceClaimsService(async_session)
        preauth = await service.create_preauthorization(
            patient_id=test_patient.id,
            patient_insurance_id=test_patient_insurance.id,
            procedure_name="Bypass Surgery",
            requested_amount=Decimal("200000.00"),
            requested_date=date.today(),
        )

        # Submit
        submitted_preauth = await service.submit_preauthorization(
            preauth_id=preauth.id,
            documents=["medical_report.pdf", "doctor_note.pdf"],
        )

        assert submitted_preauth.status == PreAuthStatus.REQUESTED.value
        assert submitted_preauth.submitted_at is not None
        assert len(submitted_preauth.documents_submitted) == 2

    async def test_update_preauth_status_to_approved(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_patient_insurance: PatientInsurance,
    ):
        """Test updating pre-auth status to approved."""
        service = InsuranceClaimsService(async_session)
        preauth = await service.create_preauthorization(
            patient_id=test_patient.id,
            patient_insurance_id=test_patient_insurance.id,
            procedure_name="Bypass Surgery",
            requested_amount=Decimal("200000.00"),
            requested_date=date.today(),
        )

        # Submit first
        await service.submit_preauthorization(preauth_id=preauth.id)

        # Approve
        approved_preauth = await service.update_preauth_status(
            preauth_id=preauth.id,
            status=PreAuthStatus.APPROVED,
            auth_number="AUTH-2026-12345",
            approved_amount=Decimal("180000.00"),
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=30),
        )

        assert approved_preauth.status == PreAuthStatus.APPROVED.value
        assert approved_preauth.auth_number == "AUTH-2026-12345"
        assert approved_preauth.approved_amount == Decimal("180000.00")
        assert approved_preauth.approved_at is not None
        assert approved_preauth.is_valid is True

    async def test_check_preauth_validity_valid(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_patient_insurance: PatientInsurance,
    ):
        """Test checking valid pre-auth."""
        # Create and approve pre-auth
        preauth = PreAuthorization(
            id=uuid4(),
            patient_id=test_patient.id,
            patient_insurance_id=test_patient_insurance.id,
            insurance_company_id=test_patient_insurance.insurance_company_id,
            internal_ref_number="PA-TEST-001",
            procedure_name="Test Procedure",
            requested_amount=Decimal("100000.00"),
            approved_amount=Decimal("90000.00"),
            requested_date=date.today(),
            status=PreAuthStatus.APPROVED.value,
            auth_number="AUTH-12345",
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=30),
        )
        async_session.add(preauth)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        validity = await service.check_preauth_validity(preauth.id)

        assert validity["is_valid"] is True
        assert validity["auth_number"] == "AUTH-12345"
        assert validity["approved_amount"] == 90000.0

    async def test_check_preauth_validity_expired(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_patient_insurance: PatientInsurance,
    ):
        """Test checking expired pre-auth."""
        # Create expired pre-auth
        preauth = PreAuthorization(
            id=uuid4(),
            patient_id=test_patient.id,
            patient_insurance_id=test_patient_insurance.id,
            insurance_company_id=test_patient_insurance.insurance_company_id,
            internal_ref_number="PA-TEST-002",
            procedure_name="Test Procedure",
            requested_amount=Decimal("100000.00"),
            approved_amount=Decimal("90000.00"),
            requested_date=date.today() - timedelta(days=60),
            status=PreAuthStatus.APPROVED.value,
            auth_number="AUTH-EXPIRED",
            valid_from=date.today() - timedelta(days=60),
            valid_to=date.today() - timedelta(days=1),  # Expired yesterday
        )
        async_session.add(preauth)
        await async_session.commit()

        service = InsuranceClaimsService(async_session)
        validity = await service.check_preauth_validity(preauth.id)

        assert validity["is_valid"] is False
        assert "Expired" in str(validity["reasons"])

    async def test_get_claim_summary(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test getting claim summary."""
        service = InsuranceClaimsService(async_session)

        # Create multiple claims
        claim1 = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )
        await service.update_claim_status(
            claim_id=claim1.id,
            status=ClaimStatus.APPROVED,
            approved_amount=Decimal("9000.00"),
            settled_amount=Decimal("9000.00"),
        )

        # Create second invoice for second claim
        invoice2 = Invoice(
            id=uuid4(),
            invoice_number="INV-2026-002",
            clinic_id=test_invoice.clinic_id,
            patient_id=test_patient.id,
            doctor_id=test_invoice.doctor_id,
            invoice_date=date.today(),
            subtotal=Decimal("5000.00"),
            total_amount=Decimal("5000.00"),
        )
        async_session.add(invoice2)
        await async_session.commit()

        claim2 = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=invoice2.id,
            patient_insurance_id=test_patient_insurance.id,
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
        assert summary["total_settled"] == 9000.0
        assert summary["approved_count"] == 1
        assert summary["rejected_count"] == 1


# ============================================================================
# EDGE CASES AND INTEGRATION TESTS
# ============================================================================


@pytest.mark.asyncio
class TestFinancialEdgeCases:
    """Test edge cases and complex scenarios."""

    async def test_claim_with_zero_amount(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test creating claim with zero amount."""
        service = InsuranceClaimsService(async_session)

        # Should allow creating claim with zero amount
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("0.00"),
        )

        assert claim.claimed_amount == Decimal("0.00")

    async def test_claim_with_large_amount_crore_range(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test creating claim with large amount (crore range)."""
        service = InsuranceClaimsService(async_session)

        # 2 crore claim
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("20000000.00"),  # 2 crore
        )

        assert claim.claimed_amount == Decimal("20000000.00")

        # Approve partial amount
        updated = await service.update_claim_status(
            claim_id=claim.id,
            status=ClaimStatus.PARTIALLY_APPROVED,
            approved_amount=Decimal("15000000.00"),  # 1.5 crore approved
        )

        assert updated.patient_liability == Decimal("5000000.00")  # 50 lakh patient pays

    async def test_multiple_insurance_policies_same_patient(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_insurance_company: InsuranceCompany,
    ):
        """Test patient with multiple insurance policies."""
        # Create second insurance company
        company2 = InsuranceCompany(
            id=uuid4(),
            name="HDFC Ergo",
            code="HDFC",
            is_active=True,
        )
        async_session.add(company2)
        await async_session.commit()

        # Create primary insurance
        primary_insurance = PatientInsurance(
            id=uuid4(),
            patient_id=test_patient.id,
            insurance_company_id=test_insurance_company.id,
            policy_number="PRIMARY-001",
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=365),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("300000.00"),
            is_primary=True,
            priority_order=1,
            is_active=True,
        )

        # Create secondary insurance
        secondary_insurance = PatientInsurance(
            id=uuid4(),
            patient_id=test_patient.id,
            insurance_company_id=company2.id,
            policy_number="SECONDARY-001",
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=365),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("200000.00"),
            is_primary=False,
            priority_order=2,
            is_active=True,
        )

        async_session.add(primary_insurance)
        async_session.add(secondary_insurance)
        await async_session.commit()

        # Verify both policies exist
        result = await async_session.execute(
            select(PatientInsurance).where(PatientInsurance.patient_id == test_patient.id)
        )
        policies = result.scalars().all()

        assert len(policies) == 2
        assert any(p.is_primary for p in policies)
        assert any(not p.is_primary for p in policies)

    async def test_partial_insurance_coverage_workflow(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test complete workflow with partial coverage."""
        service = InsuranceClaimsService(async_session)

        # Create claim for Rs 50,000
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("50000.00"),
        )

        # Submit claim
        await service.submit_claim(claim_id=claim.id, submitted_by="Front Desk")

        # Insurance partially approves (only 80%)
        await service.update_claim_status(
            claim_id=claim.id,
            status=ClaimStatus.PARTIALLY_APPROVED,
            approved_amount=Decimal("40000.00"),
            claim_number="CLM-PARTIAL-001",
        )

        # Calculate patient vs insurance split with copay
        split = BillingService.calculate_insurance_split(
            total_amount=Decimal("50000.00"),
            copay_percentage=test_patient_insurance.copay_percentage,  # 10%
            deductible=test_patient_insurance.deductible_amount,  # 5000
            approved_amount=Decimal("40000.00"),
        )

        # Patient pays: deductible (5000) + copay on remaining 45k (4500) + unapproved (5000)
        # = 5000 + 4500 + 5000 = 14500
        # Insurance pays: 40000 (approved) - copay portion already paid
        # But approved_amount in split is what insurance actually pays

        assert split["patient_deductible"] == Decimal("5000.00")
        assert split["patient_portion"] > Decimal("10000.00")  # Patient pays significant amount
        assert split["insurance_portion"] == Decimal("40000.00")

    async def test_decimal_precision_in_claims(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test decimal precision handling in claims (paisa level)."""
        service = InsuranceClaimsService(async_session)

        # Create claim with odd decimal amount
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("12345.67"),
        )

        # Approve with precise amount
        await service.update_claim_status(
            claim_id=claim.id,
            status=ClaimStatus.APPROVED,
            approved_amount=Decimal("11111.11"),
        )

        # Patient liability should be precise
        await async_session.refresh(claim)
        assert claim.patient_liability == Decimal("1234.56")  # 12345.67 - 11111.11

    async def test_claim_with_preauthorization_link(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test claim linked to pre-authorization."""
        service = InsuranceClaimsService(async_session)

        # Create pre-authorization
        preauth = await service.create_preauthorization(
            patient_id=test_patient.id,
            patient_insurance_id=test_patient_insurance.id,
            procedure_name="Angioplasty",
            requested_amount=Decimal("150000.00"),
            requested_date=date.today(),
        )

        # Approve pre-auth
        await service.update_preauth_status(
            preauth_id=preauth.id,
            status=PreAuthStatus.APPROVED,
            auth_number="AUTH-001",
            approved_amount=Decimal("140000.00"),
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=30),
        )

        # Create claim linked to pre-auth
        claim = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("140000.00"),
            preauthorization_id=preauth.id,
            notes=f"Claim against pre-auth {preauth.auth_number}",
        )

        assert claim.preauthorization_id == preauth.id
        assert str(preauth.auth_number) in claim.notes

    async def test_claim_summary_by_date_range(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_invoice: Invoice,
        test_patient_insurance: PatientInsurance,
    ):
        """Test claim summary with date filtering."""
        service = InsuranceClaimsService(async_session)

        # Create claims on different dates (simulated)
        claim1 = await service.create_claim(
            patient_id=test_patient.id,
            invoice_id=test_invoice.id,
            patient_insurance_id=test_patient_insurance.id,
            claimed_amount=Decimal("10000.00"),
        )

        # Get summary for today
        summary = await service.get_claim_summary(
            patient_id=test_patient.id,
            date_from=date.today(),
            date_to=date.today(),
        )

        assert summary["total_claims"] >= 1
        assert summary["total_claimed"] >= 10000.0


# ============================================================================
# PERFORMANCE AND STRESS TESTS
# ============================================================================


@pytest.mark.asyncio
class TestFinancialServicePerformance:
    """Test performance with large datasets."""

    async def test_bulk_claim_generation(
        self,
        async_session: AsyncSession,
        test_patient: Patient,
        test_insurance_company: InsuranceCompany,
    ):
        """Test generating multiple claims efficiently."""
        # Create patient insurance
        patient_insurance = PatientInsurance(
            id=uuid4(),
            patient_id=test_patient.id,
            insurance_company_id=test_insurance_company.id,
            policy_number="BULK-TEST",
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=365),
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("1000000.00"),
            is_active=True,
        )
        async_session.add(patient_insurance)
        await async_session.commit()

        # Create invoices and claims
        service = InsuranceClaimsService(async_session)
        claims = []

        for i in range(10):  # Create 10 claims
            invoice = Invoice(
                id=uuid4(),
                invoice_number=f"INV-BULK-{i:03d}",
                clinic_id=uuid4(),
                patient_id=test_patient.id,
                invoice_date=date.today(),
                subtotal=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
            )
            async_session.add(invoice)
            await async_session.commit()

            claim = await service.create_claim(
                patient_id=test_patient.id,
                invoice_id=invoice.id,
                patient_insurance_id=patient_insurance.id,
                claimed_amount=Decimal("1000.00"),
            )
            claims.append(claim)

        assert len(claims) == 10
        # All claims should have unique claim numbers
        claim_numbers = [c.internal_claim_number for c in claims]
        assert len(set(claim_numbers)) == 10

    def test_complex_multi_line_invoice_calculation(self):
        """Test invoice calculation with many line items."""
        # Create 20 line items with varying prices and tax rates
        items = []
        for i in range(20):
            item = InvoiceItem(
                id=uuid4(),
                invoice_id=uuid4(),
                description=f"Item {i+1}",
                quantity=1 + (i % 3),  # 1, 2, or 3
                unit_price=Decimal(str(100 + i * 50)),
                tax_rate=Decimal(str(i % 3 * 6)),  # 0%, 6%, or 12%
                subtotal=Decimal(str((100 + i * 50) * (1 + i % 3))),
                tax_amount=Decimal("0.00"),
                total=Decimal(str((100 + i * 50) * (1 + i % 3))),
            )
            items.append(item)

        result = BillingService.calculate_invoice_totals(
            items=items,
            clinic_state="MH",
            patient_state="MH",
            discount_amount=Decimal("500.00"),
        )

        # Should complete without errors
        assert result["subtotal"] > Decimal("0.00")
        assert result["total_amount"] >= result["taxable_amount"]
