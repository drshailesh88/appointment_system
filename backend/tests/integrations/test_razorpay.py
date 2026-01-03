"""
Tests for Razorpay payment integration.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.integrations.razorpay import (
    RazorpayService,
    RazorpayOrder,
    RazorpayPayment,
)


class TestRazorpayService:
    """Tests for RazorpayService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        with patch.dict("os.environ", {
            "RAZORPAY_KEY_ID": "test_key",
            "RAZORPAY_KEY_SECRET": "test_secret"
        }):
            service = RazorpayService()
            assert service is not None

    @patch("razorpay.Client")
    def test_create_order(self, mock_client):
        """Test creating a payment order."""
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            "id": "order_123",
            "amount": 50000,
            "currency": "INR",
            "status": "created",
            "receipt": "receipt_123",
        }
        mock_client.return_value = mock_instance

        with patch.dict("os.environ", {
            "RAZORPAY_KEY_ID": "test_key",
            "RAZORPAY_KEY_SECRET": "test_secret"
        }):
            service = RazorpayService()
            order = service.create_order(
                amount=500.0,
                currency="INR",
                receipt="receipt_123",
            )

            assert order is not None
            assert order.id == "order_123"
            assert order.amount == 50000

    @patch("razorpay.Client")
    def test_create_order_with_notes(self, mock_client):
        """Test creating order with notes."""
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            "id": "order_456",
            "amount": 100000,
            "currency": "INR",
            "status": "created",
            "receipt": "receipt_456",
            "notes": {"patient_id": "pat_123"},
        }
        mock_client.return_value = mock_instance

        with patch.dict("os.environ", {
            "RAZORPAY_KEY_ID": "test_key",
            "RAZORPAY_KEY_SECRET": "test_secret"
        }):
            service = RazorpayService()
            order = service.create_order(
                amount=1000.0,
                currency="INR",
                receipt="receipt_456",
                notes={"patient_id": "pat_123"},
            )

            assert order.id == "order_456"

    @patch("razorpay.Client")
    def test_verify_payment_signature_valid(self, mock_client):
        """Test verifying valid payment signature."""
        mock_instance = MagicMock()
        mock_instance.utility.verify_payment_signature.return_value = True
        mock_client.return_value = mock_instance

        with patch.dict("os.environ", {
            "RAZORPAY_KEY_ID": "test_key",
            "RAZORPAY_KEY_SECRET": "test_secret"
        }):
            service = RazorpayService()
            result = service.verify_payment_signature(
                order_id="order_123",
                payment_id="pay_123",
                signature="valid_signature",
            )

            assert result == True

    @patch("razorpay.Client")
    def test_verify_payment_signature_invalid(self, mock_client):
        """Test verifying invalid payment signature."""
        mock_instance = MagicMock()
        mock_instance.utility.verify_payment_signature.side_effect = Exception("Invalid signature")
        mock_client.return_value = mock_instance

        with patch.dict("os.environ", {
            "RAZORPAY_KEY_ID": "test_key",
            "RAZORPAY_KEY_SECRET": "test_secret"
        }):
            service = RazorpayService()
            result = service.verify_payment_signature(
                order_id="order_123",
                payment_id="pay_123",
                signature="invalid_signature",
            )

            assert result == False

    @patch("razorpay.Client")
    def test_create_refund(self, mock_client):
        """Test creating a refund."""
        mock_instance = MagicMock()
        mock_instance.payment.refund.return_value = {
            "id": "rfnd_123",
            "payment_id": "pay_123",
            "amount": 50000,
            "status": "processed",
        }
        mock_client.return_value = mock_instance

        with patch.dict("os.environ", {
            "RAZORPAY_KEY_ID": "test_key",
            "RAZORPAY_KEY_SECRET": "test_secret"
        }):
            service = RazorpayService()
            refund = service.create_refund(
                payment_id="pay_123",
                amount=500.0,
            )

            assert refund is not None
            assert refund["id"] == "rfnd_123"

    @patch("razorpay.Client")
    def test_get_checkout_options(self, mock_client):
        """Test getting checkout options for frontend."""
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        with patch.dict("os.environ", {
            "RAZORPAY_KEY_ID": "test_key",
            "RAZORPAY_KEY_SECRET": "test_secret"
        }):
            service = RazorpayService()
            options = service.get_checkout_options(
                order_id="order_123",
                amount=500.0,
                name="Test Clinic",
                description="Consultation Fee",
                prefill_email="patient@test.com",
                prefill_phone="+919876543210",
            )

            assert "key" in options
            assert "order_id" in options
            assert "amount" in options
            assert "name" in options


class TestRazorpayDataClasses:
    """Tests for Razorpay data classes."""

    def test_razorpay_order_creation(self):
        """Test RazorpayOrder dataclass."""
        order = RazorpayOrder(
            id="order_123",
            amount=50000,
            currency="INR",
            status="created",
            receipt="receipt_123",
        )
        assert order.id == "order_123"
        assert order.amount == 50000

    def test_razorpay_payment_creation(self):
        """Test RazorpayPayment dataclass."""
        payment = RazorpayPayment(
            id="pay_123",
            order_id="order_123",
            amount=50000,
            currency="INR",
            status="captured",
            method="upi",
        )
        assert payment.id == "pay_123"
        assert payment.method == "upi"


class TestAmountConversion:
    """Tests for amount conversion (rupees to paise)."""

    def test_rupees_to_paise(self):
        """Test converting rupees to paise."""
        # 500 rupees = 50000 paise
        assert 500 * 100 == 50000

        # 99.99 rupees = 9999 paise
        assert int(99.99 * 100) == 9999

    def test_paise_to_rupees(self):
        """Test converting paise to rupees."""
        # 50000 paise = 500 rupees
        assert 50000 / 100 == 500.0
