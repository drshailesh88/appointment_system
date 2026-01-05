"""
Tests for SMS integration service.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.integrations.sms import (
    SMSService,
    MessageType,
    MessageChannel,
    MessageResult,
    SMS_TEMPLATES,
    WHATSAPP_TEMPLATES,
)


class TestSMSTemplates:
    """Tests for SMS message templates."""

    def test_appointment_confirmation_template(self):
        """Test appointment confirmation template exists."""
        assert MessageType.APPOINTMENT_CONFIRMATION in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.APPOINTMENT_CONFIRMATION]
        assert "{patient_name}" in template["template"]
        assert "{doctor_name}" in template["template"]
        assert "{date}" in template["template"]
        assert "{time}" in template["template"]

    def test_reminder_template(self):
        """Test reminder template exists."""
        assert MessageType.APPOINTMENT_REMINDER in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.APPOINTMENT_REMINDER]
        assert "{patient_name}" in template["template"]
        assert "{doctor_name}" in template["template"]

    def test_cancellation_template(self):
        """Test cancellation template exists."""
        assert MessageType.APPOINTMENT_CANCELLATION in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.APPOINTMENT_CANCELLATION]
        assert "{patient_name}" in template["template"]

    def test_otp_template(self):
        """Test OTP template exists."""
        assert MessageType.OTP in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.OTP]
        assert "{otp}" in template["template"]


class TestWhatsAppTemplates:
    """Tests for WhatsApp message templates."""

    def test_whatsapp_templates_exist(self):
        """Test WhatsApp templates exist."""
        assert MessageType.APPOINTMENT_CONFIRMATION in WHATSAPP_TEMPLATES
        assert MessageType.APPOINTMENT_REMINDER in WHATSAPP_TEMPLATES


class TestSMSService:
    """Tests for SMSService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = SMSService(api_key="test_key", sender_id="TEST")
        assert service is not None
        assert service.api_key == "test_key"
        assert service.sender_id == "TEST"

    def test_phone_formatting(self):
        """Test phone number formatting."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        assert service._format_phone("+919876543210") == "919876543210"
        assert service._format_phone("9876543210") == "919876543210"
        assert service._format_phone("09876543210") == "09876543210"

    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test sending SMS successfully."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "success",
            "request_id": "req_123"
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.send_sms(
                phone="+919876543210",
                message_type=MessageType.OTP,
                variables={"otp": "123456", "validity": "10"}
            )

            assert result.success is True
            assert result.channel == MessageChannel.SMS
            assert result.message_id == "req_123"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_sms_failure(self):
        """Test SMS sending failure."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.send_sms(
                phone="+919876543210",
                message_type=MessageType.OTP,
                variables={"otp": "123456", "validity": "10"}
            )

            assert result.success is False
            assert result.channel == MessageChannel.SMS
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_send_sms_not_configured(self):
        """Test SMS when not configured."""
        service = SMSService(api_key=None, sender_id="TEST")

        result = await service.send_sms(
            phone="+919876543210",
            message_type=MessageType.OTP,
            variables={"otp": "123456", "validity": "10"}
        )

        assert result.success is False
        assert "not configured" in result.error

    @pytest.mark.asyncio
    async def test_send_whatsapp_success(self):
        """Test sending WhatsApp message successfully."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "success",
            "request_id": "wa_req_123"
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.send_whatsapp(
                phone="+919876543210",
                message_type=MessageType.APPOINTMENT_CONFIRMATION,
                variables={
                    "patient_name": "John Doe",
                    "doctor_name": "Dr. Smith",
                    "date": "2024-01-15",
                    "time": "10:00 AM",
                    "token": "5",
                    "clinic_address": "123 Main St"
                }
            )

            assert result.success is True
            assert result.channel == MessageChannel.WHATSAPP
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_appointment_confirmation(self):
        """Test sending appointment confirmation."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"request_id": "req_123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.send_appointment_confirmation(
                phone="+919876543210",
                patient_name="John Doe",
                doctor_name="Dr. Smith",
                date="2024-01-15",
                time="10:00 AM",
                token="5",
                prefer_whatsapp=True
            )

            assert result.success is True
            mock_client.post.assert_called()

    @pytest.mark.asyncio
    async def test_send_appointment_reminder(self):
        """Test sending appointment reminder."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"request_id": "req_123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.send_appointment_reminder(
                phone="+919876543210",
                patient_name="John Doe",
                doctor_name="Dr. Smith",
                date="2024-01-15",
                time="10:00 AM",
                prefer_whatsapp=False
            )

            assert result.success is True
            assert result.channel == MessageChannel.SMS
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_otp(self):
        """Test sending OTP."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"request_id": "req_123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.send_otp(
                phone="+919876543210",
                otp="123456",
                validity_minutes=10
            )

            assert result.success is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_payment_receipt(self):
        """Test sending payment receipt."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"request_id": "req_123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(service, '_get_client', return_value=mock_client):
            result = await service.send_payment_receipt(
                phone="+919876543210",
                amount="500.00",
                invoice_number="INV-123",
                clinic_name="Test Clinic"
            )

            assert result.success is True
            mock_client.post.assert_called_once()


class TestPhoneValidation:
    """Tests for phone number validation."""

    def test_valid_indian_phone(self):
        """Test valid Indian phone numbers."""
        valid_phones = [
            "+919876543210",
            "+91 9876543210",
            "9876543210",
            "09876543210",
        ]
        # These should all be processable by the service

    def test_invalid_phone(self):
        """Test invalid phone numbers."""
        invalid_phones = [
            "123",
            "abcdefghij",
            "",
        ]
        # These should be rejected
