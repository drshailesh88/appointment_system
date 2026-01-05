"""
Integration tests for Financial API endpoints (Payments, Invoices, Insurance).
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insurance import (
    InsuranceCompany,
    PatientInsurance,
    InsuranceClaim,
    PreAuthorization,
    ClaimStatus,
    PreAuthStatus,
    CoverageType,
)
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.service import Service


# ============= Fixtures =============

@pytest.fixture
@pytest.mark.asyncio
async def test_invoice(
    db: AsyncSession,
    test_clinic,
    test_doctor,
    test_patient,
) -> Invoice:
    """Create a test invoice."""
    today = date.today()
    invoice = Invoice(
        id=str(uuid4()),
        invoice_number=f"INV-{today.strftime('%Y%m%d')}-0001",
        clinic_id=test_clinic.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        invoice_date=today,
        due_date=today + timedelta(days=7),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        cgst_amount=Decimal("90.00"),
        sgst_amount=Decimal("90.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("1180.00"),
        paid_amount=Decimal("0.00"),
        status=InvoiceStatus.PENDING.value,
    )
    db.add(invoice)

    # Add invoice items
    item = InvoiceItem(
        id=str(uuid4()),
        invoice_id=invoice.id,
        description="Consultation Fee",
        quantity=1,
        unit_price=Decimal("1000.00"),
        tax_rate=Decimal("18.00"),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        total=Decimal("1180.00"),
    )
    db.add(item)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@pytest.fixture
@pytest.mark.asyncio
async def test_paid_invoice(
    db: AsyncSession,
    test_clinic,
    test_doctor,
    test_patient,
) -> Invoice:
    """Create a fully paid invoice."""
    today = date.today()
    invoice = Invoice(
        id=str(uuid4()),
        invoice_number=f"INV-{today.strftime('%Y%m%d')}-0002",
        clinic_id=test_clinic.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        invoice_date=today,
        due_date=today + timedelta(days=7),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("90.00"),
        total_amount=Decimal("590.00"),
        paid_amount=Decimal("590.00"),
        status=InvoiceStatus.PAID.value,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@pytest.fixture
@pytest.mark.asyncio
async def test_payment(
    db: AsyncSession,
    test_invoice,
) -> Payment:
    """Create a test payment."""
    payment = Payment(
        id=str(uuid4()),
        invoice_id=test_invoice.id,
        amount=Decimal("500.00"),
        payment_method=PaymentMethod.CASH.value,
        status=PaymentStatus.COMPLETED.value,
        payment_date=datetime.now(),
        receipt_number="REC-001",
        collected_by="Test Cashier",
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@pytest.fixture
@pytest.mark.asyncio
async def test_insurance_company(db: AsyncSession) -> InsuranceCompany:
    """Create a test insurance company."""
    company = InsuranceCompany(
        id=str(uuid4()),
        name="Star Health Insurance",
        code="STAR",
        contact_email="claims@starhealth.in",
        contact_phone="+911234567890",
        tpa_name="Medi Assist",
        cashless_available=True,
        preauth_required=True,
        preauth_threshold=Decimal("10000.00"),
        is_active=True,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@pytest.fixture
@pytest.mark.asyncio
async def test_patient_insurance(
    db: AsyncSession,
    test_patient,
    test_insurance_company,
) -> PatientInsurance:
    """Create a test patient insurance policy."""
    today = date.today()
    insurance = PatientInsurance(
        id=str(uuid4()),
        patient_id=test_patient.id,
        insurance_company_id=test_insurance_company.id,
        policy_number="POL123456",
        coverage_type=CoverageType.INDIVIDUAL.value,
        sum_insured=Decimal("500000.00"),
        valid_from=today - timedelta(days=30),
        valid_to=today + timedelta(days=335),
        policy_holder_name=test_patient.full_name,
        is_active=True,
    )
    db.add(insurance)
    await db.commit()
    await db.refresh(insurance)
    return insurance


@pytest.fixture
@pytest.mark.asyncio
async def test_insurance_claim(
    db: AsyncSession,
    test_patient,
    test_invoice,
    test_insurance_company,
    test_patient_insurance,
) -> InsuranceClaim:
    """Create a test insurance claim."""
    claim = InsuranceClaim(
        id=str(uuid4()),
        internal_claim_number=f"CLM-{date.today().strftime('%Y%m%d')}-0001",
        patient_id=test_patient.id,
        invoice_id=test_invoice.id,
        insurance_company_id=test_insurance_company.id,
        patient_insurance_id=test_patient_insurance.id,
        claimed_amount=Decimal("1180.00"),
        approved_amount=Decimal("0.00"),
        settled_amount=Decimal("0.00"),
        status=ClaimStatus.DRAFT.value,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


@pytest.fixture
@pytest.mark.asyncio
async def test_preauthorization(
    db: AsyncSession,
    test_patient,
    test_insurance_company,
    test_patient_insurance,
) -> PreAuthorization:
    """Create a test pre-authorization."""
    preauth = PreAuthorization(
        id=str(uuid4()),
        internal_ref_number=f"PA-{date.today().strftime('%Y%m%d')}-0001",
        patient_id=test_patient.id,
        insurance_company_id=test_insurance_company.id,
        patient_insurance_id=test_patient_insurance.id,
        procedure_name="Cardiac Catheterization",
        procedure_code="CATH001",
        requested_amount=Decimal("50000.00"),
        requested_date=date.today(),
        planned_procedure_date=date.today() + timedelta(days=7),
        diagnosis="Coronary Artery Disease",
        status=PreAuthStatus.PENDING.value,
        requested_by="Dr. Test",
    )
    db.add(preauth)
    await db.commit()
    await db.refresh(preauth)
    return preauth


# ============= Payment API Tests =============

class TestPaymentsAPI:
    """Tests for Payment endpoints."""

    @pytest.mark.asyncio

    async def test_create_cash_payment(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test recording a cash payment."""
        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(test_invoice.id),
                "amount": 500.00,
                "payment_method": "cash",
                "payment_date": datetime.now().isoformat(),
                "receipt_number": "REC-TEST-001",
                "collected_by": "Test Cashier",
                "notes": "Partial payment",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "500.00"
        assert data["payment_method"] == "cash"
        assert data["status"] == "completed"
        assert data["receipt_number"] == "REC-TEST-001"

    @pytest.mark.asyncio

    async def test_create_upi_payment(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test recording a UPI payment."""
        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(test_invoice.id),
                "amount": 1180.00,
                "payment_method": "upi",
                "payment_date": datetime.now().isoformat(),
                "upi_transaction_id": "UPI123456789",
                "upi_vpa": "patient@paytm",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "1180.00"
        assert data["payment_method"] == "upi"
        assert data["upi_transaction_id"] == "UPI123456789"

    @pytest.mark.asyncio

    async def test_create_payment_invalid_invoice(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test creating payment with non-existent invoice."""
        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(uuid4()),
                "amount": 500.00,
                "payment_method": "cash",
                "payment_date": datetime.now().isoformat(),
            },
        )
        assert response.status_code == 404
        assert "Invoice not found" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_create_payment_exceeds_balance(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test payment amount exceeding invoice balance."""
        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(test_invoice.id),
                "amount": 2000.00,  # More than invoice total
                "payment_method": "cash",
                "payment_date": datetime.now().isoformat(),
            },
        )
        assert response.status_code == 400
        assert "exceeds balance due" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_create_payment_cancelled_invoice(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
        db: AsyncSession,
    ):
        """Test payment on a cancelled invoice."""
        # Cancel the invoice first
        test_invoice.status = InvoiceStatus.CANCELLED.value
        await db.commit()

        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(test_invoice.id),
                "amount": 500.00,
                "payment_method": "cash",
                "payment_date": datetime.now().isoformat(),
            },
        )
        assert response.status_code == 400
        assert "Cannot pay a cancelled invoice" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_list_payments(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
    ):
        """Test listing payments."""
        response = await client.get(
            "/api/v1/payments/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_list_payments_with_filters(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
        test_invoice,
    ):
        """Test listing payments with filters."""
        response = await client.get(
            f"/api/v1/payments/?invoice_id={str(test_invoice.id)}&payment_method=cash",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert data[0]["payment_method"] == "cash"

    @pytest.mark.asyncio

    async def test_list_payments_date_range(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
    ):
        """Test listing payments by date range."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        response = await client.get(
            f"/api/v1/payments/?date_from={yesterday.isoformat()}&date_to={tomorrow.isoformat()}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_get_payment_by_id(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
    ):
        """Test getting a specific payment."""
        response = await client.get(
            f"/api/v1/payments/{test_payment.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_payment.id
        assert data["amount"] == "500.00"

    @pytest.mark.asyncio

    async def test_get_payment_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test getting non-existent payment."""
        response = await client.get(
            f"/api/v1/payments/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_refund_payment(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
    ):
        """Test processing a payment refund."""
        response = await client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={
                "amount": 200.00,
                "reason": "Service not rendered",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["refund_amount"] == "200.00"
        assert data["status"] == "partially_refunded"

    @pytest.mark.asyncio

    async def test_refund_full_payment(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
    ):
        """Test processing a full refund."""
        response = await client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={
                "amount": 500.00,
                "reason": "Cancelled appointment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["refund_amount"] == "500.00"
        assert data["status"] == "refunded"

    @pytest.mark.asyncio

    async def test_refund_exceeds_payment(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
    ):
        """Test refund amount exceeding payment amount."""
        response = await client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={
                "amount": 1000.00,  # More than payment
                "reason": "Test",
            },
        )
        assert response.status_code == 400
        assert "exceeds available" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_refund_non_existent_payment(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test refunding non-existent payment."""
        response = await client.post(
            f"/api/v1/payments/{uuid4()}/refund",
            headers=auth_headers,
            json={
                "amount": 100.00,
                "reason": "Test",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_get_payment_summary(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
        test_payment,
    ):
        """Test getting payment summary for a clinic."""
        response = await client.get(
            f"/api/v1/payments/summary/clinic/{test_clinic.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_collected" in data
        assert "cash_collected" in data
        assert "upi_collected" in data
        assert "pending_amount" in data
        assert "transaction_count" in data

    @pytest.mark.asyncio

    async def test_payment_summary_unauthorized_clinic(
        self,
        client: AsyncClient,
        doctor_auth_headers,
    ):
        """Test accessing payment summary for unauthorized clinic."""
        response = await client.get(
            f"/api/v1/payments/summary/clinic/{uuid4()}",
            headers=doctor_auth_headers,
        )
        assert response.status_code == 403


# ============= Invoice API Tests =============

class TestInvoicesAPI:
    """Tests for Invoice endpoints."""

    @pytest.mark.asyncio

    async def test_create_invoice(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test creating an invoice."""
        today = date.today()
        response = await client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "invoice_date": today.isoformat(),
                "due_date": (today + timedelta(days=7)).isoformat(),
                "items": [
                    {
                        "description": "Consultation",
                        "quantity": 1,
                        "unit_price": 1000.00,
                        "tax_rate": 18.00,
                    }
                ],
                "discount_amount": 0.00,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "invoice_number" in data
        assert data["patient_id"] == test_patient.id
        assert data["status"] == "pending"
        assert "subtotal" in data
        assert "total_amount" in data

    @pytest.mark.asyncio

    async def test_create_invoice_with_discount(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test creating invoice with discount."""
        today = date.today()
        response = await client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "invoice_date": today.isoformat(),
                "due_date": (today + timedelta(days=7)).isoformat(),
                "items": [
                    {
                        "description": "Consultation",
                        "quantity": 1,
                        "unit_price": 1000.00,
                        "tax_rate": 18.00,
                    }
                ],
                "discount_amount": 100.00,
                "discount_reason": "Senior citizen discount",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["discount_amount"] == "100.00"
        assert data["discount_reason"] == "Senior citizen discount"

    @pytest.mark.asyncio

    async def test_create_invoice_multiple_items(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test creating invoice with multiple items."""
        today = date.today()
        response = await client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "invoice_date": today.isoformat(),
                "due_date": (today + timedelta(days=7)).isoformat(),
                "items": [
                    {
                        "description": "Consultation",
                        "quantity": 1,
                        "unit_price": 1000.00,
                        "tax_rate": 18.00,
                    },
                    {
                        "description": "ECG",
                        "quantity": 1,
                        "unit_price": 500.00,
                        "tax_rate": 18.00,
                        "hsn_code": "9018",
                    }
                ],
                "discount_amount": 0.00,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["items"]) == 2

    @pytest.mark.asyncio

    async def test_create_invoice_invalid_patient(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
        test_doctor,
    ):
        """Test creating invoice with invalid patient."""
        today = date.today()
        response = await client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "patient_id": str(uuid4()),  # Non-existent patient
                "doctor_id": str(test_doctor.id),
                "invoice_date": today.isoformat(),
                "due_date": (today + timedelta(days=7)).isoformat(),
                "items": [
                    {
                        "description": "Consultation",
                        "quantity": 1,
                        "unit_price": 1000.00,
                        "tax_rate": 18.00,
                    }
                ],
                "discount_amount": 0.00,
            },
        )
        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_list_invoices(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test listing invoices."""
        response = await client.get(
            "/api/v1/invoices/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_list_invoices_by_patient(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
        test_patient,
    ):
        """Test listing invoices for a specific patient."""
        response = await client.get(
            f"/api/v1/invoices/?patient_id={str(test_patient.id)}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert data[0]["patient_id"] == test_patient.id

    @pytest.mark.asyncio

    async def test_list_invoices_by_status(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test filtering invoices by status."""
        response = await client.get(
            "/api/v1/invoices/?status_filter=pending",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert data[0]["status"] == "pending"

    @pytest.mark.asyncio

    async def test_list_invoices_by_date_range(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test filtering invoices by date range."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        response = await client.get(
            f"/api/v1/invoices/?date_from={yesterday.isoformat()}&date_to={tomorrow.isoformat()}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_get_invoice_by_id(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test getting a specific invoice."""
        response = await client.get(
            f"/api/v1/invoices/{test_invoice.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_invoice.id
        assert "items" in data
        assert "patient" in data

    @pytest.mark.asyncio

    async def test_get_invoice_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test getting non-existent invoice."""
        response = await client.get(
            f"/api/v1/invoices/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_update_invoice(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test updating an invoice."""
        response = await client.patch(
            f"/api/v1/invoices/{test_invoice.id}",
            headers=auth_headers,
            json={
                "discount_amount": 100.00,
                "discount_reason": "Loyalty discount",
                "notes": "Updated notes",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["discount_amount"] == "100.00"
        assert data["discount_reason"] == "Loyalty discount"

    @pytest.mark.asyncio

    async def test_update_paid_invoice(
        self,
        client: AsyncClient,
        auth_headers,
        test_paid_invoice,
    ):
        """Test updating a paid invoice (should fail)."""
        response = await client.patch(
            f"/api/v1/invoices/{test_paid_invoice.id}",
            headers=auth_headers,
            json={
                "discount_amount": 50.00,
            },
        )
        assert response.status_code == 400
        assert "Cannot update invoice" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_cancel_invoice(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test cancelling an invoice."""
        response = await client.post(
            f"/api/v1/invoices/{test_invoice.id}/cancel",
            headers=auth_headers,
            params={"reason": "Duplicate invoice"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["is_cancelled"] is True

    @pytest.mark.asyncio

    async def test_cancel_paid_invoice(
        self,
        client: AsyncClient,
        auth_headers,
        test_paid_invoice,
    ):
        """Test cancelling a paid invoice (should fail)."""
        response = await client.post(
            f"/api/v1/invoices/{test_paid_invoice.id}/cancel",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Cannot cancel a paid invoice" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_get_invoice_summary(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
        test_invoice,
    ):
        """Test getting invoice summary for a clinic."""
        response = await client.get(
            f"/api/v1/invoices/summary/clinic/{test_clinic.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_invoices" in data
        assert "total_amount" in data
        assert "paid_amount" in data
        assert "pending_amount" in data
        assert "overdue_count" in data


# ============= Insurance API Tests =============

class TestInsuranceAPI:
    """Tests for Insurance endpoints."""

    # Insurance Company Tests

    @pytest.mark.asyncio

    async def test_create_insurance_company(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test creating an insurance company."""
        response = await client.post(
            "/api/v1/insurance/companies",
            headers=auth_headers,
            json={
                "name": "HDFC Ergo Health Insurance",
                "code": "HDFC",
                "contact_email": "claims@hdfcergo.com",
                "contact_phone": "+919876543210",
                "tpa_name": "Paramount TPA",
                "cashless_available": True,
                "preauth_required": True,
                "preauth_threshold": 15000.00,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "HDFC Ergo Health Insurance"
        assert data["code"] == "HDFC"
        assert data["cashless_available"] is True

    @pytest.mark.asyncio

    async def test_create_duplicate_insurance_company(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_company,
    ):
        """Test creating insurance company with duplicate code."""
        response = await client.post(
            "/api/v1/insurance/companies",
            headers=auth_headers,
            json={
                "name": "Another Star Health",
                "code": "STAR",  # Duplicate code
                "contact_email": "test@test.com",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_list_insurance_companies(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_company,
    ):
        """Test listing insurance companies."""
        response = await client.get(
            "/api/v1/insurance/companies",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_get_insurance_company(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_company,
    ):
        """Test getting insurance company details."""
        response = await client.get(
            f"/api/v1/insurance/companies/{test_insurance_company.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_insurance_company.id
        assert data["name"] == "Star Health Insurance"

    @pytest.mark.asyncio

    async def test_update_insurance_company(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_company,
    ):
        """Test updating insurance company."""
        response = await client.patch(
            f"/api/v1/insurance/companies/{test_insurance_company.id}",
            headers=auth_headers,
            json={
                "contact_email": "newclaims@starhealth.in",
                "preauth_threshold": 20000.00,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["contact_email"] == "newclaims@starhealth.in"

    # Patient Insurance Tests

    @pytest.mark.asyncio

    async def test_create_patient_insurance(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
        test_insurance_company,
    ):
        """Test creating patient insurance policy."""
        today = date.today()
        response = await client.post(
            "/api/v1/insurance/patient-insurance",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "insurance_company_id": str(test_insurance_company.id),
                "policy_number": "POL987654",
                "coverage_type": "individual",
                "sum_insured": 300000.00,
                "valid_from": today.isoformat(),
                "valid_to": (today + timedelta(days=365)).isoformat(),
                "policy_holder_name": test_patient.full_name,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["policy_number"] == "POL987654"
        assert data["sum_insured"] == "300000.00"

    @pytest.mark.asyncio

    async def test_create_patient_insurance_invalid_patient(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_company,
    ):
        """Test creating insurance with invalid patient."""
        today = date.today()
        response = await client.post(
            "/api/v1/insurance/patient-insurance",
            headers=auth_headers,
            json={
                "patient_id": str(uuid4()),
                "insurance_company_id": str(test_insurance_company.id),
                "policy_number": "POL999999",
                "coverage_type": "individual",
                "sum_insured": 300000.00,
                "valid_from": today.isoformat(),
                "valid_to": (today + timedelta(days=365)).isoformat(),
                "policy_holder_name": "Test Patient",
            },
        )
        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_list_patient_insurance(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient_insurance,
        test_patient,
    ):
        """Test listing patient insurance policies."""
        response = await client.get(
            f"/api/v1/insurance/patient-insurance?patient_id={str(test_patient.id)}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_list_valid_patient_insurance(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient_insurance,
    ):
        """Test listing only valid (non-expired) insurance policies."""
        response = await client.get(
            "/api/v1/insurance/patient-insurance?valid_only=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_get_patient_insurance(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient_insurance,
    ):
        """Test getting patient insurance details."""
        response = await client.get(
            f"/api/v1/insurance/patient-insurance/{test_patient_insurance.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_patient_insurance.id
        assert data["policy_number"] == "POL123456"
        assert "is_valid" in data

    @pytest.mark.asyncio

    async def test_update_patient_insurance(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient_insurance,
    ):
        """Test updating patient insurance."""
        response = await client.patch(
            f"/api/v1/insurance/patient-insurance/{test_patient_insurance.id}",
            headers=auth_headers,
            json={
                "sum_insured": 600000.00,
                "notes": "Updated sum insured",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sum_insured"] == "600000.00"

    # Insurance Claims Tests

    @pytest.mark.asyncio

    async def test_create_insurance_claim(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
        test_invoice,
        test_patient_insurance,
    ):
        """Test creating an insurance claim."""
        response = await client.post(
            "/api/v1/insurance/claims",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "invoice_id": str(test_invoice.id),
                "patient_insurance_id": str(test_patient_insurance.id),
                "claimed_amount": 1180.00,
                "documents_submitted": ["prescription.pdf", "lab_report.pdf"],
                "notes": "Initial claim submission",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["claimed_amount"] == "1180.00"
        assert data["status"] == "draft"
        assert "internal_claim_number" in data

    @pytest.mark.asyncio

    async def test_submit_insurance_claim(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_claim,
    ):
        """Test submitting a claim to insurance."""
        response = await client.post(
            f"/api/v1/insurance/claims/{test_insurance_claim.id}/submit",
            headers=auth_headers,
            json={
                "documents_submitted": ["claim_form.pdf", "invoice.pdf"],
                "submitted_by": "Billing Clerk",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None

    @pytest.mark.asyncio

    async def test_update_claim_status_to_approved(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_claim,
    ):
        """Test updating claim status to approved."""
        response = await client.patch(
            f"/api/v1/insurance/claims/{test_insurance_claim.id}",
            headers=auth_headers,
            json={
                "status": "approved",
                "claim_number": "CLM-STAR-123456",
                "approved_amount": 1000.00,
                "processing_notes": "Claim approved with partial amount",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_amount"] == "1000.00"

    @pytest.mark.asyncio

    async def test_update_claim_status_to_rejected(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_claim,
    ):
        """Test rejecting a claim."""
        response = await client.patch(
            f"/api/v1/insurance/claims/{test_insurance_claim.id}",
            headers=auth_headers,
            json={
                "status": "rejected",
                "rejection_reason": "Pre-existing condition",
                "rejection_code": "PEC01",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Pre-existing condition"

    @pytest.mark.asyncio

    async def test_list_insurance_claims(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_claim,
    ):
        """Test listing insurance claims."""
        response = await client.get(
            "/api/v1/insurance/claims",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_list_claims_by_patient(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_claim,
        test_patient,
    ):
        """Test listing claims for a specific patient."""
        response = await client.get(
            f"/api/v1/insurance/claims?patient_id={str(test_patient.id)}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_list_claims_by_status(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_claim,
    ):
        """Test filtering claims by status."""
        response = await client.get(
            "/api/v1/insurance/claims?status_filter=draft",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_get_claims_summary(
        self,
        client: AsyncClient,
        auth_headers,
        test_insurance_claim,
    ):
        """Test getting claims summary/statistics."""
        response = await client.get(
            "/api/v1/insurance/claims/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_claims" in data
        assert "total_claimed_amount" in data
        assert "total_approved_amount" in data

    # Pre-Authorization Tests

    @pytest.mark.asyncio

    async def test_create_preauthorization(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
        test_patient_insurance,
    ):
        """Test creating a pre-authorization request."""
        today = date.today()
        response = await client.post(
            "/api/v1/insurance/preauthorizations",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "patient_insurance_id": str(test_patient_insurance.id),
                "procedure_name": "Angioplasty",
                "procedure_code": "ANGIO001",
                "requested_amount": 75000.00,
                "requested_date": today.isoformat(),
                "planned_procedure_date": (today + timedelta(days=10)).isoformat(),
                "diagnosis": "Acute MI",
                "notes": "Emergency procedure required",
                "requested_by": "Dr. Cardiologist",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["procedure_name"] == "Angioplasty"
        assert data["requested_amount"] == "75000.00"
        assert data["status"] == "pending"

    @pytest.mark.asyncio

    async def test_submit_preauthorization(
        self,
        client: AsyncClient,
        auth_headers,
        test_preauthorization,
    ):
        """Test submitting pre-authorization to insurance."""
        response = await client.post(
            f"/api/v1/insurance/preauthorizations/{test_preauthorization.id}/submit",
            headers=auth_headers,
            json={
                "documents_submitted": ["doctor_note.pdf", "ecg.pdf"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "requested"
        assert data["submitted_at"] is not None

    @pytest.mark.asyncio

    async def test_approve_preauthorization(
        self,
        client: AsyncClient,
        auth_headers,
        test_preauthorization,
    ):
        """Test approving a pre-authorization."""
        today = date.today()
        response = await client.patch(
            f"/api/v1/insurance/preauthorizations/{test_preauthorization.id}",
            headers=auth_headers,
            json={
                "status": "approved",
                "auth_number": "AUTH-STAR-789012",
                "approved_amount": 45000.00,
                "valid_from": today.isoformat(),
                "valid_to": (today + timedelta(days=30)).isoformat(),
                "tpa_notes": "Pre-auth approved with conditions",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_amount"] == "45000.00"
        assert data["auth_number"] == "AUTH-STAR-789012"

    @pytest.mark.asyncio

    async def test_reject_preauthorization(
        self,
        client: AsyncClient,
        auth_headers,
        test_preauthorization,
    ):
        """Test rejecting a pre-authorization."""
        response = await client.patch(
            f"/api/v1/insurance/preauthorizations/{test_preauthorization.id}",
            headers=auth_headers,
            json={
                "status": "rejected",
                "rejection_reason": "Insufficient coverage",
                "rejection_code": "COV02",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Insufficient coverage"

    @pytest.mark.asyncio

    async def test_list_preauthorizations(
        self,
        client: AsyncClient,
        auth_headers,
        test_preauthorization,
    ):
        """Test listing pre-authorizations."""
        response = await client.get(
            "/api/v1/insurance/preauthorizations",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_list_valid_preauthorizations(
        self,
        client: AsyncClient,
        auth_headers,
        test_preauthorization,
        db: AsyncSession,
    ):
        """Test listing only valid (approved & non-expired) pre-authorizations."""
        # First approve it
        today = date.today()
        test_preauthorization.status = PreAuthStatus.APPROVED.value
        test_preauthorization.valid_from = today
        test_preauthorization.valid_to = today + timedelta(days=30)
        await db.commit()

        response = await client.get(
            "/api/v1/insurance/preauthorizations?valid_only=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_check_preauth_validity(
        self,
        client: AsyncClient,
        auth_headers,
        test_preauthorization,
        db: AsyncSession,
    ):
        """Test checking pre-authorization validity."""
        # Approve the pre-auth first
        today = date.today()
        test_preauthorization.status = PreAuthStatus.APPROVED.value
        test_preauthorization.valid_from = today
        test_preauthorization.valid_to = today + timedelta(days=30)
        await db.commit()

        response = await client.get(
            f"/api/v1/insurance/preauthorizations/{test_preauthorization.id}/validity",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data

    @pytest.mark.asyncio

    async def test_check_expired_preauth_validity(
        self,
        client: AsyncClient,
        auth_headers,
        test_preauthorization,
        db: AsyncSession,
    ):
        """Test validity check for expired pre-authorization."""
        # Set expired dates
        today = date.today()
        test_preauthorization.status = PreAuthStatus.APPROVED.value
        test_preauthorization.valid_from = today - timedelta(days=60)
        test_preauthorization.valid_to = today - timedelta(days=30)
        await db.commit()

        response = await client.get(
            f"/api/v1/insurance/preauthorizations/{test_preauthorization.id}/validity",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False


# ============= Authorization Tests =============

class TestFinancialAPIsAuthorization:
    """Test authorization and access control."""

    @pytest.mark.asyncio

    async def test_payment_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Test creating payment without authentication."""
        response = await client.post(
            "/api/v1/payments/",
            json={
                "invoice_id": str(uuid4()),
                "amount": 500.00,
                "payment_method": "cash",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio

    async def test_invoice_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Test creating invoice without authentication."""
        response = await client.post(
            "/api/v1/invoices/",
            json={
                "clinic_id": str(uuid4()),
                "patient_id": str(uuid4()),
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio

    async def test_insurance_company_non_admin(
        self,
        client: AsyncClient,
        doctor_auth_headers,
    ):
        """Test creating insurance company as non-admin (should fail)."""
        response = await client.post(
            "/api/v1/insurance/companies",
            headers=doctor_auth_headers,
            json={
                "name": "Test Insurance",
                "code": "TEST",
            },
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    @pytest.mark.asyncio

    async def test_update_insurance_company_non_admin(
        self,
        client: AsyncClient,
        doctor_auth_headers,
        test_insurance_company,
    ):
        """Test updating insurance company as non-admin (should fail)."""
        response = await client.patch(
            f"/api/v1/insurance/companies/{test_insurance_company.id}",
            headers=doctor_auth_headers,
            json={
                "contact_email": "newemail@test.com",
            },
        )
        assert response.status_code == 403


# ============= Edge Cases =============

class TestFinancialAPIsEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio

    async def test_payment_with_zero_amount(
        self,
        client: AsyncClient,
        auth_headers,
        test_invoice,
    ):
        """Test creating payment with zero amount (should fail validation)."""
        response = await client.post(
            "/api/v1/payments/",
            headers=auth_headers,
            json={
                "invoice_id": str(test_invoice.id),
                "amount": 0.00,
                "payment_method": "cash",
                "payment_date": datetime.now().isoformat(),
            },
        )
        # This might fail validation at schema level or be accepted
        # Depends on schema validation rules
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio

    async def test_invoice_with_no_items(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
        test_patient,
    ):
        """Test creating invoice with no items (should fail)."""
        today = date.today()
        response = await client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "patient_id": str(test_patient.id),
                "invoice_date": today.isoformat(),
                "due_date": (today + timedelta(days=7)).isoformat(),
                "items": [],  # No items
                "discount_amount": 0.00,
            },
        )
        # Should fail validation
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio

    async def test_claim_with_expired_insurance(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
        test_invoice,
        test_insurance_company,
        db: AsyncSession,
    ):
        """Test creating claim with expired insurance policy."""
        # Create expired insurance
        today = date.today()
        expired_insurance = PatientInsurance(
            id=str(uuid4()),
            patient_id=test_patient.id,
            insurance_company_id=test_insurance_company.id,
            policy_number="EXP123",
            coverage_type=CoverageType.INDIVIDUAL.value,
            sum_insured=Decimal("500000.00"),
            valid_from=today - timedelta(days=400),
            valid_to=today - timedelta(days=35),  # Expired
            policy_holder_name=test_patient.full_name,
            is_active=True,
        )
        db.add(expired_insurance)
        await db.commit()

        response = await client.post(
            "/api/v1/insurance/claims",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "invoice_id": str(test_invoice.id),
                "patient_insurance_id": str(expired_insurance.id),
                "claimed_amount": 1180.00,
            },
        )
        # Service should reject expired insurance
        assert response.status_code == 400

    @pytest.mark.asyncio

    async def test_double_refund_same_payment(
        self,
        client: AsyncClient,
        auth_headers,
        test_payment,
    ):
        """Test attempting to refund same payment twice."""
        # First refund
        response1 = await client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={
                "amount": 300.00,
                "reason": "First refund",
            },
        )
        assert response1.status_code == 200

        # Second refund
        response2 = await client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={
                "amount": 300.00,  # Would exceed total
                "reason": "Second refund",
            },
        )
        assert response2.status_code == 400
        assert "exceeds available" in response2.json()["detail"]

    @pytest.mark.asyncio

    async def test_preauth_without_insurance(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
    ):
        """Test creating pre-auth for patient without insurance."""
        today = date.today()
        response = await client.post(
            "/api/v1/insurance/preauthorizations",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "patient_insurance_id": str(uuid4()),  # Non-existent
                "procedure_name": "Surgery",
                "requested_amount": 50000.00,
                "requested_date": today.isoformat(),
                "planned_procedure_date": (today + timedelta(days=7)).isoformat(),
            },
        )
        # Should fail - insurance not found
        assert response.status_code == 400

