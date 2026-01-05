"""
Tests for billing service and GST calculations.
"""

from decimal import Decimal

import pytest

from app.models.invoice import Invoice, InvoiceItem
from app.services.billing import BillingService, GSTType


class TestGSTCalculation:
    """Test GST calculation logic."""

    @pytest.mark.asyncio


    async def test_intra_state_gst(self):
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

    @pytest.mark.asyncio


    async def test_inter_state_gst(self):
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

    @pytest.mark.asyncio


    async def test_exempt_service(self):
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

    @pytest.mark.asyncio


    async def test_custom_gst_rate(self):
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

    @pytest.mark.asyncio


    async def test_case_insensitive_state_codes(self):
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


class TestInvoiceTotalsCalculation:
    """Test invoice totals calculation."""

    @pytest.mark.asyncio


    async def test_invoice_totals_without_discount(self):
        """Test invoice calculation without discount."""
        items = [
            InvoiceItem(
                description="Consultation",
                quantity=1,
                unit_price=Decimal("1000.00"),
                tax_rate=Decimal("18.00"),
                subtotal=Decimal("1000.00"),
                tax_amount=Decimal("0.00"),
                total=Decimal("1000.00"),
            ),
            InvoiceItem(
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

    @pytest.mark.asyncio


    async def test_invoice_totals_with_discount(self):
        """Test invoice calculation with discount."""
        items = [
            InvoiceItem(
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

    @pytest.mark.asyncio


    async def test_invoice_totals_inter_state(self):
        """Test invoice calculation for inter-state."""
        items = [
            InvoiceItem(
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


class TestInsuranceSplit:
    """Test insurance vs patient portion calculations."""

    @pytest.mark.asyncio


    async def test_no_copay_no_deductible(self):
        """Test split with no copay or deductible."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
        )

        assert result["patient_portion"] == Decimal("0.00")
        assert result["insurance_portion"] == Decimal("10000.00")
        assert result["patient_deductible"] == Decimal("0.00")
        assert result["patient_copay"] == Decimal("0.00")

    @pytest.mark.asyncio


    async def test_with_copay(self):
        """Test split with 10% copay."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
            copay_percentage=Decimal("10.00"),
        )

        assert result["patient_portion"] == Decimal("1000.00")  # 10%
        assert result["insurance_portion"] == Decimal("9000.00")  # 90%
        assert result["patient_deductible"] == Decimal("0.00")
        assert result["patient_copay"] == Decimal("1000.00")

    @pytest.mark.asyncio


    async def test_with_deductible(self):
        """Test split with deductible."""
        result = BillingService.calculate_insurance_split(
            total_amount=Decimal("10000.00"),
            deductible=Decimal("2000.00"),
        )

        assert result["patient_deductible"] == Decimal("2000.00")
        assert result["patient_copay"] == Decimal("0.00")
        assert result["insurance_portion"] == Decimal("8000.00")
        assert result["patient_portion"] == Decimal("2000.00")

    @pytest.mark.asyncio


    async def test_with_copay_and_deductible(self):
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

    @pytest.mark.asyncio


    async def test_with_partial_insurance_approval(self):
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


class TestHSNCodes:
    """Test HSN code retrieval."""

    @pytest.mark.asyncio


    async def test_consultation_hsn(self):
        """Test HSN code for consultation."""
        code = BillingService.get_hsn_code("consultation")
        assert code == "9993"

    @pytest.mark.asyncio


    async def test_diagnostic_hsn(self):
        """Test HSN code for diagnostic."""
        code = BillingService.get_hsn_code("diagnostic")
        assert code == "9993"

    @pytest.mark.asyncio


    async def test_ambulance_hsn(self):
        """Test HSN code for ambulance."""
        code = BillingService.get_hsn_code("ambulance")
        assert code == "9994"

    @pytest.mark.asyncio


    async def test_unknown_service_default_hsn(self):
        """Test default HSN code for unknown service."""
        code = BillingService.get_hsn_code("unknown_service")
        assert code == "9993"


class TestGSTINValidation:
    """Test GSTIN validation."""

    @pytest.mark.asyncio


    async def test_valid_gstin(self):
        """Test valid GSTIN format."""
        assert BillingService.validate_gstin("27AABCT1234F1Z5") is True
        assert BillingService.validate_gstin("29AABCT1234F1Z5") is True

    @pytest.mark.asyncio


    async def test_invalid_gstin_length(self):
        """Test GSTIN with wrong length."""
        assert BillingService.validate_gstin("27AABCT1234F1Z") is False  # Too short
        assert BillingService.validate_gstin("27AABCT1234F1Z55") is False  # Too long

    @pytest.mark.asyncio


    async def test_invalid_gstin_format(self):
        """Test GSTIN with invalid format."""
        assert BillingService.validate_gstin("XXAABCT1234F1Z5") is False  # Should start with digits
        assert BillingService.validate_gstin("27AABCT1234F1X5") is False  # Should have Z at position 13

    @pytest.mark.asyncio


    async def test_none_gstin(self):
        """Test None GSTIN."""
        assert BillingService.validate_gstin(None) is False

    @pytest.mark.asyncio


    async def test_empty_gstin(self):
        """Test empty GSTIN."""
        assert BillingService.validate_gstin("") is False


class TestServiceExemptions:
    """Test GST exemption checks."""

    @pytest.mark.asyncio


    async def test_hospital_room_below_threshold(self):
        """Test hospital room charges below Rs 5000 are exempt."""
        assert BillingService.is_service_exempt("hospital_room_charges", Decimal("4000.00")) is True

    @pytest.mark.asyncio


    async def test_hospital_room_above_threshold(self):
        """Test hospital room charges above Rs 5000 are not exempt."""
        assert BillingService.is_service_exempt("hospital_room_charges", Decimal("6000.00")) is False

    @pytest.mark.asyncio


    async def test_diagnostic_tests_exempt(self):
        """Test diagnostic tests are exempt."""
        assert BillingService.is_service_exempt("diagnostic_tests_prescribed") is True

    @pytest.mark.asyncio


    async def test_ambulance_exempt(self):
        """Test ambulance services are exempt."""
        assert BillingService.is_service_exempt("transportation_patient") is True

    @pytest.mark.asyncio


    async def test_non_exempt_service(self):
        """Test non-exempt service."""
        assert BillingService.is_service_exempt("consultation") is False
