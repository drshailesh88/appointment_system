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
        assert "template" in template
        assert "{patient_name}" in template["template"]
        assert "{doctor_name}" in template["template"]
        assert "{date}" in template["template"]
        assert "{time}" in template["template"]

    def test_appointment_reminder_template(self):
        """Test appointment reminder template exists."""
        assert MessageType.APPOINTMENT_REMINDER in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.APPOINTMENT_REMINDER]
        assert "{doctor_name}" in template["template"]

    def test_cancellation_template(self):
        """Test cancellation template exists."""
        assert MessageType.APPOINTMENT_CANCELLATION in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.APPOINTMENT_CANCELLATION]
        assert "{doctor_name}" in template["template"]

    def test_otp_template(self):
        """Test OTP template exists."""
        assert MessageType.OTP in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.OTP]
        assert "{otp}" in template["template"]

    def test_payment_receipt_template(self):
        """Test payment receipt template exists."""
        assert MessageType.PAYMENT_RECEIPT in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.PAYMENT_RECEIPT]
        assert "{amount}" in template["template"]


class TestWhatsAppTemplates:
    """Tests for WhatsApp message templates."""

    def test_whatsapp_templates_exist(self):
        """Test WhatsApp templates exist."""
        assert MessageType.APPOINTMENT_CONFIRMATION in WHATSAPP_TEMPLATES
        assert MessageType.APPOINTMENT_REMINDER in WHATSAPP_TEMPLATES

    def test_whatsapp_template_structure(self):
        """Test WhatsApp template structure."""
        for msg_type, template in WHATSAPP_TEMPLATES.items():
            assert "template_name" in template
            assert "template" in template


class TestSMSService:
    """Tests for SMSService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = SMSService(api_key="test_key", sender_id="TEST")
        assert service.api_key == "test_key"
        assert service.sender_id == "TEST"

    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test sending SMS successfully."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"request_id": "REQ123"}
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                phone="+919876543210",
                message_type=MessageType.APPOINTMENT_CONFIRMATION,
                variables={
                    "patient_name": "John Doe",
                    "doctor_name": "Dr. Smith",
                    "date": "2024-01-15",
                    "time": "10:00 AM",
                    "token": "A123",
                },
            )

            assert result.success is True
            assert result.message_id == "REQ123"
            assert result.channel == MessageChannel.SMS

    @pytest.mark.asyncio
    async def test_send_sms_failure(self):
        """Test SMS sending failure."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Server Error"
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                phone="+919876543210",
                message_type=MessageType.OTP,
                variables={"otp": "123456", "validity": "10"},
            )

            assert result.success is False
            assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_send_sms_no_api_key(self):
        """Test SMS sending without API key."""
        service = SMSService(api_key=None, sender_id="TEST")

        result = await service.send_sms(
            phone="+919876543210",
            message_type=MessageType.OTP,
            variables={"otp": "123456", "validity": "10"},
        )

        assert result.success is False
        assert "not configured" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_whatsapp_success(self):
        """Test sending WhatsApp message successfully."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"request_id": "WA_REQ123"}
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_whatsapp(
                phone="+919876543210",
                message_type=MessageType.APPOINTMENT_CONFIRMATION,
                variables={
                    "patient_name": "John Doe",
                    "doctor_name": "Dr. Smith",
                    "date": "2024-01-15",
                    "time": "10:00 AM",
                    "token": "A123",
                    "clinic_address": "123 Main St",
                },
            )

            assert result.success is True
            assert result.channel == MessageChannel.WHATSAPP

    @pytest.mark.asyncio
    async def test_send_appointment_confirmation(self):
        """Test sending appointment confirmation."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        with patch.object(service, "send_whatsapp") as mock_whatsapp:
            mock_whatsapp.return_value = MessageResult(
                success=True,
                message_id="WA123",
                channel=MessageChannel.WHATSAPP,
            )

            result = await service.send_appointment_confirmation(
                phone="+919876543210",
                patient_name="John Doe",
                doctor_name="Dr. Smith",
                date="2024-01-15",
                time="10:00 AM",
                token="A123",
                prefer_whatsapp=True,
            )

            assert result.success is True
            mock_whatsapp.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_appointment_confirmation_fallback_to_sms(self):
        """Test fallback to SMS when WhatsApp fails."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        with patch.object(service, "send_whatsapp") as mock_whatsapp:
            with patch.object(service, "send_sms") as mock_sms:
                # WhatsApp fails
                mock_whatsapp.return_value = MessageResult(
                    success=False,
                    error="WhatsApp failed",
                    channel=MessageChannel.WHATSAPP,
                )
                # SMS succeeds
                mock_sms.return_value = MessageResult(
                    success=True,
                    message_id="SMS123",
                    channel=MessageChannel.SMS,
                )

                result = await service.send_appointment_confirmation(
                    phone="+919876543210",
                    patient_name="John Doe",
                    doctor_name="Dr. Smith",
                    date="2024-01-15",
                    time="10:00 AM",
                    prefer_whatsapp=True,
                )

                assert result.success is True
                assert result.channel == MessageChannel.SMS
                mock_whatsapp.assert_called_once()
                mock_sms.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_otp(self):
        """Test sending OTP."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        with patch.object(service, "send_sms") as mock_sms:
            mock_sms.return_value = MessageResult(
                success=True,
                message_id="OTP123",
                channel=MessageChannel.SMS,
            )

            result = await service.send_otp(
                phone="+919876543210",
                otp="123456",
                validity_minutes=10,
            )

            assert result.success is True
            mock_sms.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_payment_receipt(self):
        """Test sending payment receipt."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        with patch.object(service, "send_sms") as mock_sms:
            mock_sms.return_value = MessageResult(
                success=True,
                message_id="PAY123",
                channel=MessageChannel.SMS,
            )

            result = await service.send_payment_receipt(
                phone="+919876543210",
                amount="1500",
                invoice_number="INV001",
                clinic_name="Test Clinic",
            )

            assert result.success is True


class TestPhoneFormatting:
    """Tests for phone number formatting."""

    def test_format_indian_phone(self):
        """Test formatting Indian phone numbers."""
        service = SMSService(api_key="test_key", sender_id="TEST")

        # Test various formats
        assert service._format_phone("+919876543210") == "919876543210"
        assert service._format_phone("9876543210") == "919876543210"
        assert service._format_phone("09876543210") == "919876543210"
        assert service._format_phone("+91 9876543210") == "919876543210"
        assert service._format_phone("91-9876543210") == "919876543210"


class TestMessageResult:
    """Tests for MessageResult dataclass."""

    def test_message_result_success(self):
        """Test successful message result."""
        result = MessageResult(
            success=True,
            message_id="MSG123",
            channel=MessageChannel.SMS,
        )

        assert result.success is True
        assert result.message_id == "MSG123"
        assert result.channel == MessageChannel.SMS
        assert result.timestamp is not None

    def test_message_result_failure(self):
        """Test failed message result."""
        result = MessageResult(
            success=False,
            error="API error",
            channel=MessageChannel.WHATSAPP,
        )

        assert result.success is False
        assert result.error == "API error"
        assert result.message_id is None


class TestDNDHandling:
    """Tests for DND (Do Not Disturb) number handling."""

    @pytest.mark.asyncio
    async def test_dnd_number_handling(self):
        """Test handling DND registered numbers."""
        # DND numbers in India can't receive promotional SMS
        # Only transactional messages allowed
        service = SMSService(api_key="test_key", sender_id="TEST")

        # All messages in this app are transactional (appointments, OTP, etc.)
        # So DND shouldn't block them
        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"request_id": "DND_OK"}
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send_sms(
                phone="+919876543210",  # Assume DND registered
                message_type=MessageType.APPOINTMENT_CONFIRMATION,  # Transactional
                variables={
                    "patient_name": "Test",
                    "doctor_name": "Dr. Test",
                    "date": "2024-01-15",
                    "time": "10:00 AM",
                    "token": "A1",
                },
            )

            # Should succeed for transactional messages
            assert result.success is True
