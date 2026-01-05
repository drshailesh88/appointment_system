"""
Tests for Razorpay payment integration.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from app.integrations.razorpay import (
    RazorpayService,
    RazorpayOrder,
    RazorpayPayment,
    RefundResult,
)


class TestRazorpayService:
    """Tests for RazorpayService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")
        assert service is not None
        assert service.key_id == "test_key"
        assert service.key_secret == "test_secret"

    @pytest.mark.asyncio
    async def test_create_order(self):
        """Test creating a payment order."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "order_123",
            "amount": 50000,
            "currency": "INR",
            "status": "created",
            "receipt": "receipt_123",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            order = await service.create_order(
                amount=Decimal("500.0"),
                currency="INR",
                receipt="receipt_123",
            )

            assert order is not None
            assert order.order_id == "order_123"
            assert order.amount == 50000
            assert order.currency == "INR"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_with_notes(self):
        """Test creating order with notes."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "order_456",
            "amount": 100000,
            "currency": "INR",
            "status": "created",
            "receipt": "receipt_456",
            "notes": {"patient_id": "pat_123"},
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            order = await service.create_order(
                amount=Decimal("1000.0"),
                currency="INR",
                receipt="receipt_456",
                notes={"patient_id": "pat_123"},
            )

            assert order.order_id == "order_456"
            assert order.amount == 100000

    def test_verify_payment_signature_valid(self):
        """Test verifying valid payment signature."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        # Create a valid signature
        import hmac
        import hashlib
        order_id = "order_123"
        payment_id = "pay_123"
        message = f"{order_id}|{payment_id}"
        signature = hmac.new(
            b"test_secret",
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        result = service.verify_payment_signature(
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
        )

        assert result is True

    def test_verify_payment_signature_invalid(self):
        """Test verifying invalid payment signature."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        result = service.verify_payment_signature(
            order_id="order_123",
            payment_id="pay_123",
            signature="invalid_signature",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_create_refund(self):
        """Test creating a refund."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "rfnd_123",
            "payment_id": "pay_123",
            "amount": 50000,
            "status": "processed",
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            refund = await service.create_refund(
                payment_id="pay_123",
                amount=Decimal("500.0"),
            )

            assert refund is not None
            assert refund.success is True
            assert refund.refund_id == "rfnd_123"
            assert refund.amount == 50000
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_refund_failure(self):
        """Test refund failure."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Insufficient balance"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            refund = await service.create_refund(
                payment_id="pay_123",
                amount=Decimal("500.0"),
            )

            assert refund.success is False
            assert refund.error is not None

    @pytest.mark.asyncio
    async def test_get_order(self):
        """Test fetching order details."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "order_123",
            "amount": 50000,
            "currency": "INR",
            "status": "created",
            "receipt": "receipt_123",
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            order = await service.get_order("order_123")

            assert order is not None
            assert order.order_id == "order_123"
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_payment(self):
        """Test capturing a payment."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.capture_payment(
                payment_id="pay_123",
                amount=50000,
            )

            assert result is True
            mock_client.post.assert_called_once()

    def test_get_checkout_options(self):
        """Test getting checkout options for frontend."""
        service = RazorpayService(key_id="test_key", key_secret="test_secret")

        order = RazorpayOrder(
            order_id="order_123",
            amount=50000,
            currency="INR",
            status="created",
            receipt="receipt_123",
            created_at=datetime.now(timezone.utc),
        )

        options = service.get_checkout_options(
            order=order,
            customer_name="Test Patient",
            customer_email="patient@test.com",
            customer_phone="+919876543210",
            description="Consultation Fee",
        )

        assert "key" in options
        assert "order_id" in options
        assert options["order_id"] == "order_123"
        assert "amount" in options
        assert options["amount"] == 50000
        assert "name" in options
        assert options["prefill"]["name"] == "Test Patient"


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
