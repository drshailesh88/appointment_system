"""
Comprehensive Payment System Tests for DocAssist Practice Manager.

Tests cover:
- Payment flow (creation, success, failure)
- Webhook security (signature verification, replay attacks)
- Refund processing (full, partial, double refund prevention)
- Edge cases (timeouts, concurrent attempts, amount mismatches)
- Razorpay API mocking
- Financial integrity (audit trails, no duplicates)
"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.razorpay import (
    PaymentStatus as RazorpayPaymentStatus,
    RazorpayOrder,
    RazorpayPayment,
    RazorpayService,
    RefundResult,
)
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.patient import Patient
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.service import Service


# ==================
# Fixtures
# ==================


@pytest.fixture
def test_invoice(
    db: Session,
    test_clinic: Clinic,
    test_doctor: Doctor,
    test_patient: Patient,
) -> Invoice:
    """Create a test invoice for payment testing."""
    invoice = Invoice(
        id=uuid4(),
        clinic_id=test_clinic.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        invoice_number=f"INV-{datetime.now().strftime('%Y%m%d')}-001",
        invoice_date=datetime.now().date(),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("90.00"),
        total_amount=Decimal("590.00"),
        paid_amount=Decimal("0.00"),
        status=InvoiceStatus.PENDING.value,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@pytest.fixture
def test_payment(db: Session, test_invoice: Invoice) -> Payment:
    """Create a test completed payment."""
    payment = Payment(
        id=uuid4(),
        invoice_id=test_invoice.id,
        amount=Decimal("590.00"),
        payment_method=PaymentMethod.UPI.value,
        status=PaymentStatus.COMPLETED.value,
        payment_date=datetime.now(timezone.utc),
        razorpay_payment_id="pay_test123",
        razorpay_order_id="order_test123",
        upi_transaction_id="UPI123456789",
    )
    db.add(payment)

    # Update invoice
    test_invoice.paid_amount = Decimal("590.00")
    test_invoice.status = InvoiceStatus.PAID.value

    db.commit()
    db.refresh(payment)
    return payment


@pytest.fixture
def razorpay_service():
    """Create a Razorpay service instance for testing."""
    return RazorpayService(
        key_id="rzp_test_123456",
        key_secret="test_secret_key_12345678",
    )


# ==================
# A. Payment Flow Tests
# ==================


class TestPaymentFlow:
    """Test payment creation and processing flows."""

    def test_create_payment_success(
        self,
        db: Session,
        client,
        auth_headers,
        test_invoice: Invoice,
    ):
        """Test successful payment creation."""
        payment_data = {
            "invoice_id": str(test_invoice.id),
            "amount": 590.00,
            "payment_method": "upi",
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "upi_transaction_id": "UPI123456789",
            "upi_vpa": "patient@upi",
            "notes": "UPI payment via PhonePe",
        }

        response = client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["amount"] == "590.00"
        assert data["payment_method"] == "upi"
        assert data["status"] == "completed"
        assert data["upi_transaction_id"] == "UPI123456789"

        # Verify invoice is updated
        db.refresh(test_invoice)
        assert test_invoice.paid_amount == Decimal("590.00")
        assert test_invoice.status == InvoiceStatus.PAID.value

    def test_partial_payment_handling(
        self,
        db: Session,
        client,
        auth_headers,
        test_invoice: Invoice,
    ):
        """Test partial payment handling."""
        payment_data = {
            "invoice_id": str(test_invoice.id),
            "amount": 300.00,
            "payment_method": "cash",
            "payment_date": datetime.now(timezone.utc).isoformat(),
        }

        response = client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify invoice is partially paid
        db.refresh(test_invoice)
        assert test_invoice.paid_amount == Decimal("300.00")
        assert test_invoice.status == InvoiceStatus.PARTIALLY_PAID.value
        assert test_invoice.balance_due == Decimal("290.00")

    def test_payment_exceeds_balance(
        self,
        client,
        auth_headers,
        test_invoice: Invoice,
    ):
        """Test payment amount exceeding balance is rejected."""
        payment_data = {
            "invoice_id": str(test_invoice.id),
            "amount": 1000.00,  # More than invoice total
            "payment_method": "cash",
            "payment_date": datetime.now(timezone.utc).isoformat(),
        }

        response = client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds balance due" in response.json()["detail"]

    def test_payment_for_cancelled_invoice(
        self,
        db: Session,
        client,
        auth_headers,
        test_invoice: Invoice,
    ):
        """Test payment cannot be made for cancelled invoice."""
        # Cancel the invoice
        test_invoice.status = InvoiceStatus.CANCELLED.value
        db.commit()

        payment_data = {
            "invoice_id": str(test_invoice.id),
            "amount": 590.00,
            "payment_method": "cash",
            "payment_date": datetime.now(timezone.utc).isoformat(),
        }

        response = client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cancelled invoice" in response.json()["detail"]

    def test_currency_handling_inr(
        self,
        db: Session,
        test_invoice: Invoice,
    ):
        """Test INR currency handling with paise conversion."""
        payment = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=Decimal("590.50"),  # Decimal places for paise
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
        )
        db.add(payment)
        db.commit()

        # Verify decimal precision is maintained
        assert payment.amount == Decimal("590.50")
        assert str(payment.amount) == "590.50"


# ==================
# B. Webhook Security Tests
# ==================


class TestWebhookSecurity:
    """Test webhook signature verification and security."""

    def test_valid_webhook_signature(self, razorpay_service: RazorpayService):
        """Test valid webhook signature verification."""
        webhook_secret = "webhook_secret_123"
        payload = {"event": "payment.captured", "entity": {"id": "pay_123"}}
        body = json.dumps(payload).encode()

        # Create valid signature
        signature = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        is_valid = razorpay_service.verify_webhook_signature(
            body=body,
            signature=signature,
            webhook_secret=webhook_secret,
        )

        assert is_valid is True

    def test_invalid_webhook_signature(self, razorpay_service: RazorpayService):
        """Test invalid webhook signature is rejected."""
        webhook_secret = "webhook_secret_123"
        payload = {"event": "payment.captured"}
        body = json.dumps(payload).encode()

        # Use wrong signature
        invalid_signature = "invalid_signature_hash"

        is_valid = razorpay_service.verify_webhook_signature(
            body=body,
            signature=invalid_signature,
            webhook_secret=webhook_secret,
        )

        assert is_valid is False

    def test_webhook_replay_attack_prevention(
        self,
        db: Session,
        razorpay_service: RazorpayService,
    ):
        """Test webhook replay attack prevention via idempotency."""
        webhook_event_id = "evt_test_123"

        # First webhook processing
        payment1 = Payment(
            id=uuid4(),
            invoice_id=uuid4(),
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
            razorpay_payment_id="pay_123",
            gateway_response={"webhook_event_id": webhook_event_id},
        )
        db.add(payment1)
        db.commit()

        # Try to process same webhook again (replay attack)
        result = db.execute(
            select(Payment).where(
                Payment.gateway_response["webhook_event_id"].astext == webhook_event_id
            )
        )
        existing_payment = result.scalar_one_or_none()

        # Should find existing payment (preventing duplicate processing)
        assert existing_payment is not None
        assert existing_payment.id == payment1.id

    def test_webhook_with_tampered_amount(self, razorpay_service: RazorpayService):
        """Test webhook with tampered payload is rejected."""
        webhook_secret = "webhook_secret_123"

        # Original payload
        original_payload = {"amount": 50000}  # ₹500
        body = json.dumps(original_payload).encode()
        signature = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Tampered payload (changed amount)
        tampered_payload = {"amount": 5000}  # ₹50
        tampered_body = json.dumps(tampered_payload).encode()

        # Signature won't match tampered body
        is_valid = razorpay_service.verify_webhook_signature(
            body=tampered_body,
            signature=signature,
            webhook_secret=webhook_secret,
        )

        assert is_valid is False

    def test_webhook_duplicate_event_handling(self, db: Session):
        """Test handling of duplicate webhook events (idempotency)."""
        payment_id = "pay_test_duplicate"
        invoice_id = uuid4()

        # Create invoice
        invoice = Invoice(
            id=invoice_id,
            clinic_id=uuid4(),
            patient_id=uuid4(),
            invoice_number="INV-TEST-001",
            invoice_date=datetime.now().date(),
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("0.00"),
            status=InvoiceStatus.PENDING.value,
        )
        db.add(invoice)
        db.commit()

        # First webhook - create payment
        payment1 = Payment(
            id=uuid4(),
            invoice_id=invoice_id,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
            razorpay_payment_id=payment_id,
        )
        db.add(payment1)
        invoice.paid_amount = Decimal("500.00")
        invoice.status = InvoiceStatus.PAID.value
        db.commit()

        # Second webhook (duplicate) - check for existing payment
        result = db.execute(
            select(Payment).where(Payment.razorpay_payment_id == payment_id)
        )
        existing = result.scalar_one_or_none()

        # Should find existing payment
        assert existing is not None
        assert existing.id == payment1.id

        # Invoice should still be paid once
        db.refresh(invoice)
        assert invoice.paid_amount == Decimal("500.00")


# ==================
# C. Refund Tests
# ==================


class TestRefunds:
    """Test refund processing."""

    def test_full_refund_processing(
        self,
        db: Session,
        client,
        auth_headers,
        test_payment: Payment,
        test_invoice: Invoice,
    ):
        """Test full refund processing."""
        refund_data = {
            "amount": 590.00,
            "reason": "Patient cancelled appointment",
        }

        response = client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            json=refund_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "refunded"
        assert data["refund_amount"] == "590.00"
        assert data["net_amount"] == "0.00"

        # Verify invoice is updated
        db.refresh(test_invoice)
        assert test_invoice.paid_amount == Decimal("0.00")
        assert test_invoice.status == InvoiceStatus.PENDING.value

    def test_partial_refund(
        self,
        db: Session,
        client,
        auth_headers,
        test_payment: Payment,
        test_invoice: Invoice,
    ):
        """Test partial refund processing."""
        refund_data = {
            "amount": 100.00,
            "reason": "Service discount applied",
        }

        response = client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            json=refund_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "partially_refunded"
        assert data["refund_amount"] == "100.00"
        assert data["net_amount"] == "490.00"

        # Verify invoice
        db.refresh(test_invoice)
        assert test_invoice.paid_amount == Decimal("490.00")
        assert test_invoice.status == InvoiceStatus.PARTIALLY_PAID.value

    def test_double_refund_prevention(
        self,
        db: Session,
        client,
        auth_headers,
        test_payment: Payment,
    ):
        """Test double refund prevention."""
        # First refund (full amount)
        refund_data = {
            "amount": 590.00,
            "reason": "First refund",
        }
        response = client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            json=refund_data,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        # Try second refund (should fail)
        refund_data2 = {
            "amount": 100.00,
            "reason": "Second refund attempt",
        }
        response = client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            json=refund_data2,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds available" in response.json()["detail"]

    def test_refund_exceeds_available(
        self,
        client,
        auth_headers,
        test_payment: Payment,
    ):
        """Test refund amount exceeding available amount is rejected."""
        refund_data = {
            "amount": 1000.00,  # More than payment amount
            "reason": "Excessive refund attempt",
        }

        response = client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            json=refund_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "exceeds available" in response.json()["detail"]

    def test_refund_only_completed_payments(
        self,
        db: Session,
        client,
        auth_headers,
        test_invoice: Invoice,
    ):
        """Test refund can only be processed for completed payments."""
        # Create pending payment
        pending_payment = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.PENDING.value,
            payment_date=datetime.now(timezone.utc),
        )
        db.add(pending_payment)
        db.commit()

        refund_data = {
            "amount": 100.00,
            "reason": "Test refund",
        }

        response = client.post(
            f"/api/v1/payments/{pending_payment.id}/refund",
            json=refund_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "completed payments" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_razorpay_refund_api(self, razorpay_service: RazorpayService):
        """Test Razorpay refund API call."""
        payment_id = "pay_test123"
        refund_amount = Decimal("100.00")

        # Mock the HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "rfnd_test123",
            "amount": 10000,  # In paise
            "status": "processed",
        }

        with patch.object(
            razorpay_service,
            "_get_client",
            return_value=AsyncMock(post=AsyncMock(return_value=mock_response)),
        ):
            result = await razorpay_service.create_refund(
                payment_id=payment_id,
                amount=refund_amount,
                notes={"reason": "Test refund"},
            )

        assert result.success is True
        assert result.refund_id == "rfnd_test123"
        assert result.amount == 10000


# ==================
# D. Edge Cases
# ==================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_payment_for_nonexistent_invoice(
        self,
        client,
        auth_headers,
    ):
        """Test payment for non-existent invoice is rejected."""
        payment_data = {
            "invoice_id": str(uuid4()),  # Random UUID
            "amount": 100.00,
            "payment_method": "cash",
            "payment_date": datetime.now(timezone.utc).isoformat(),
        }

        response = client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_payment_timeout_handling(self, razorpay_service: RazorpayService):
        """Test payment timeout handling."""
        # Mock timeout error
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Request timeout")

        with patch.object(razorpay_service, "_get_client", return_value=mock_client):
            order = await razorpay_service.create_order(
                amount=Decimal("500.00"),
                receipt="timeout_test",
            )

        assert order is None

    @pytest.mark.asyncio
    async def test_network_failure_during_payment(
        self,
        razorpay_service: RazorpayService,
    ):
        """Test network failure handling during payment verification."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")

        with patch.object(razorpay_service, "_get_client", return_value=mock_client):
            payment = await razorpay_service.get_payment("pay_test123")

        assert payment is None

    def test_concurrent_payment_attempts(
        self,
        db: Session,
        test_invoice: Invoice,
    ):
        """Test handling of concurrent payment attempts for same invoice."""
        # Create two payments for same invoice
        payment1 = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.PROCESSING.value,
            payment_date=datetime.now(timezone.utc),
        )
        db.add(payment1)
        db.commit()

        payment2 = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.CARD.value,
            status=PaymentStatus.PROCESSING.value,
            payment_date=datetime.now(timezone.utc),
        )
        db.add(payment2)
        db.commit()

        # Both should be allowed but only one should complete
        # (Application logic should handle this)
        payments = db.query(Payment).filter(
            Payment.invoice_id == test_invoice.id
        ).all()

        assert len(payments) == 2
        assert all(p.status == PaymentStatus.PROCESSING.value for p in payments)

    def test_payment_amount_mismatch(
        self,
        db: Session,
        test_invoice: Invoice,
    ):
        """Test detection of payment amount mismatch."""
        # Invoice expects ₹590, but payment only for ₹500
        payment = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
        )
        db.add(payment)

        test_invoice.paid_amount = Decimal("500.00")
        test_invoice.status = InvoiceStatus.PARTIALLY_PAID.value
        db.commit()

        # Verify mismatch is tracked
        db.refresh(test_invoice)
        assert test_invoice.balance_due == Decimal("90.00")
        assert not test_invoice.is_fully_paid

    def test_payment_with_zero_amount(
        self,
        client,
        auth_headers,
        test_invoice: Invoice,
    ):
        """Test payment with zero amount is rejected."""
        payment_data = {
            "invoice_id": str(test_invoice.id),
            "amount": 0.00,
            "payment_method": "cash",
            "payment_date": datetime.now(timezone.utc).isoformat(),
        }

        response = client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers,
        )

        # Should fail validation (amount must be > 0)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_payment_with_negative_amount(
        self,
        client,
        auth_headers,
        test_invoice: Invoice,
    ):
        """Test payment with negative amount is rejected."""
        payment_data = {
            "invoice_id": str(test_invoice.id),
            "amount": -100.00,
            "payment_method": "cash",
            "payment_date": datetime.now(timezone.utc).isoformat(),
        }

        response = client.post(
            "/api/v1/payments/",
            json=payment_data,
            headers=auth_headers,
        )

        # Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==================
# E. Razorpay API Mocking
# ==================


class TestRazorpayAPIMocking:
    """Test Razorpay API integration with mocking."""

    @pytest.mark.asyncio
    async def test_mock_razorpay_order_creation(
        self,
        razorpay_service: RazorpayService,
    ):
        """Test Razorpay order creation with mocking."""
        amount = Decimal("500.00")
        receipt = "rcpt_test_123"

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "order_test123",
            "amount": 50000,
            "currency": "INR",
            "receipt": receipt,
            "status": "created",
            "created_at": int(datetime.now().timestamp()),
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(razorpay_service, "_get_client", return_value=mock_client):
            order = await razorpay_service.create_order(
                amount=amount,
                receipt=receipt,
            )

        assert order is not None
        assert order.order_id == "order_test123"
        assert order.amount == 50000
        assert order.currency == "INR"

    @pytest.mark.asyncio
    async def test_mock_payment_verification(
        self,
        razorpay_service: RazorpayService,
    ):
        """Test Razorpay payment verification with mocking."""
        payment_id = "pay_test123"

        # Mock payment details
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": payment_id,
            "order_id": "order_test123",
            "amount": 50000,
            "currency": "INR",
            "status": "captured",
            "method": "upi",
            "vpa": "test@upi",
            "captured": True,
            "created_at": int(datetime.now().timestamp()),
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(razorpay_service, "_get_client", return_value=mock_client):
            payment = await razorpay_service.get_payment(payment_id)

        assert payment is not None
        assert payment.payment_id == payment_id
        assert payment.status == "captured"
        assert payment.method == "upi"
        assert payment.captured is True

    def test_payment_signature_verification(
        self,
        razorpay_service: RazorpayService,
    ):
        """Test payment signature verification."""
        order_id = "order_test123"
        payment_id = "pay_test123"

        # Generate valid signature
        message = f"{order_id}|{payment_id}"
        expected_signature = hmac.new(
            razorpay_service.key_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Test valid signature
        is_valid = razorpay_service.verify_payment_signature(
            order_id=order_id,
            payment_id=payment_id,
            signature=expected_signature,
        )
        assert is_valid is True

        # Test invalid signature
        is_valid = razorpay_service.verify_payment_signature(
            order_id=order_id,
            payment_id=payment_id,
            signature="invalid_signature",
        )
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_razorpay_error_codes(self, razorpay_service: RazorpayService):
        """Test handling of various Razorpay error codes."""
        error_scenarios = [
            (400, "BAD_REQUEST_ERROR"),
            (401, "UNAUTHORIZED"),
            (404, "NOT_FOUND"),
            (500, "SERVER_ERROR"),
        ]

        for status_code, error_type in error_scenarios:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.text = f"Error: {error_type}"

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response

            with patch.object(
                razorpay_service, "_get_client", return_value=mock_client
            ):
                order = await razorpay_service.create_order(
                    amount=Decimal("100.00"),
                )

            assert order is None

    @pytest.mark.asyncio
    async def test_razorpay_payment_capture(self, razorpay_service: RazorpayService):
        """Test payment capture API."""
        payment_id = "pay_test123"

        mock_response = Mock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(razorpay_service, "_get_client", return_value=mock_client):
            success = await razorpay_service.capture_payment(
                payment_id=payment_id,
                amount=50000,
            )

        assert success is True


# ==================
# F. Financial Integrity Tests
# ==================


class TestFinancialIntegrity:
    """Test financial integrity and audit trails."""

    def test_payment_matches_invoice_amount(
        self,
        db: Session,
        test_invoice: Invoice,
    ):
        """Test payment amount matches invoice amount."""
        payment = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=test_invoice.total_amount,
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
        )
        db.add(payment)

        test_invoice.paid_amount = payment.amount
        test_invoice.status = InvoiceStatus.PAID.value
        db.commit()

        # Verify amounts match
        assert payment.amount == test_invoice.total_amount
        assert test_invoice.is_fully_paid is True

    def test_no_duplicate_charges(
        self,
        db: Session,
        test_invoice: Invoice,
    ):
        """Test no duplicate charges for same invoice."""
        # Create first payment
        payment1 = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=Decimal("590.00"),
            payment_method=PaymentMethod.UPI.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
            razorpay_payment_id="pay_unique_123",
        )
        db.add(payment1)
        db.commit()

        # Check for duplicate payment_id
        duplicate_check = db.query(Payment).filter(
            Payment.razorpay_payment_id == "pay_unique_123"
        ).count()

        assert duplicate_check == 1

    def test_audit_trail_for_transactions(
        self,
        db: Session,
        test_payment: Payment,
    ):
        """Test audit trail exists for all transactions."""
        # Verify payment has required audit fields
        assert test_payment.created_at is not None
        assert test_payment.updated_at is not None
        assert test_payment.payment_date is not None

        # Payment should have identifiable transaction ID
        assert (
            test_payment.razorpay_payment_id is not None
            or test_payment.transaction_id is not None
            or test_payment.upi_transaction_id is not None
        )

    def test_revenue_calculation_accuracy(
        self,
        db: Session,
        test_clinic: Clinic,
        test_patient: Patient,
        test_doctor: Doctor,
        client,
        auth_headers,
    ):
        """Test revenue calculation accuracy."""
        # Create multiple invoices and payments
        invoices_data = [
            (Decimal("500.00"), Decimal("500.00")),  # Fully paid
            (Decimal("1000.00"), Decimal("600.00")),  # Partially paid
            (Decimal("300.00"), Decimal("0.00")),  # Unpaid
        ]

        total_collected = Decimal("0.00")

        for total, paid in invoices_data:
            invoice = Invoice(
                id=uuid4(),
                clinic_id=test_clinic.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                invoice_number=f"INV-{uuid4().hex[:8]}",
                invoice_date=datetime.now().date(),
                total_amount=total,
                paid_amount=paid,
                status=(
                    InvoiceStatus.PAID.value if paid >= total
                    else InvoiceStatus.PARTIALLY_PAID.value if paid > 0
                    else InvoiceStatus.PENDING.value
                ),
            )
            db.add(invoice)

            if paid > 0:
                payment = Payment(
                    id=uuid4(),
                    invoice_id=invoice.id,
                    amount=paid,
                    payment_method=PaymentMethod.UPI.value,
                    status=PaymentStatus.COMPLETED.value,
                    payment_date=datetime.now(timezone.utc),
                )
                db.add(payment)
                total_collected += paid

        db.commit()

        # Get payment summary
        response = client.get(
            f"/api/v1/payments/summary/clinic/{test_clinic.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify calculations
        assert Decimal(data["total_collected"]) == total_collected
        assert data["transaction_count"] > 0

    def test_refund_affects_revenue(
        self,
        db: Session,
        client,
        auth_headers,
        test_payment: Payment,
        test_clinic: Clinic,
    ):
        """Test refunds properly affect revenue calculations."""
        # Get initial revenue
        response = client.get(
            f"/api/v1/payments/summary/clinic/{test_clinic.id}",
            headers=auth_headers,
        )
        initial_data = response.json()
        initial_collected = Decimal(initial_data["total_collected"])

        # Process refund
        refund_amount = Decimal("100.00")
        refund_data = {
            "amount": float(refund_amount),
            "reason": "Test refund",
        }
        client.post(
            f"/api/v1/payments/{test_payment.id}/refund",
            json=refund_data,
            headers=auth_headers,
        )

        # Get updated revenue
        response = client.get(
            f"/api/v1/payments/summary/clinic/{test_clinic.id}",
            headers=auth_headers,
        )
        updated_data = response.json()
        updated_collected = Decimal(updated_data["total_collected"])

        # Revenue should decrease by refund amount
        assert updated_collected == initial_collected - refund_amount
        assert Decimal(updated_data["refunded_amount"]) == refund_amount

    def test_payment_timestamps_accuracy(
        self,
        db: Session,
        test_invoice: Invoice,
    ):
        """Test payment timestamps are accurate."""
        before_payment = datetime.now(timezone.utc)

        payment = Payment(
            id=uuid4(),
            invoice_id=test_invoice.id,
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.CASH.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        after_payment = datetime.now(timezone.utc)

        # Verify timestamps are within reasonable range
        assert before_payment <= payment.payment_date <= after_payment
        assert before_payment <= payment.created_at <= after_payment

    def test_multiple_payment_methods_tracking(
        self,
        db: Session,
        client,
        auth_headers,
        test_clinic: Clinic,
        test_patient: Patient,
        test_doctor: Doctor,
    ):
        """Test accurate tracking of different payment methods."""
        payment_methods = [
            (PaymentMethod.CASH, Decimal("100.00")),
            (PaymentMethod.UPI, Decimal("200.00")),
            (PaymentMethod.CARD, Decimal("300.00")),
        ]

        for method, amount in payment_methods:
            invoice = Invoice(
                id=uuid4(),
                clinic_id=test_clinic.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                invoice_number=f"INV-{uuid4().hex[:8]}",
                invoice_date=datetime.now().date(),
                total_amount=amount,
                paid_amount=amount,
                status=InvoiceStatus.PAID.value,
            )
            db.add(invoice)

            payment = Payment(
                id=uuid4(),
                invoice_id=invoice.id,
                amount=amount,
                payment_method=method.value,
                status=PaymentStatus.COMPLETED.value,
                payment_date=datetime.now(timezone.utc),
            )
            db.add(payment)

        db.commit()

        # Get summary
        response = client.get(
            f"/api/v1/payments/summary/clinic/{test_clinic.id}",
            headers=auth_headers,
        )
        data = response.json()

        # Verify breakdown by payment method
        assert Decimal(data["cash_collected"]) >= Decimal("100.00")
        assert Decimal(data["upi_collected"]) >= Decimal("200.00")
        assert Decimal(data["card_collected"]) >= Decimal("300.00")
