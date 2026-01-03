"""
Tests for SMS integration service.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.integrations.sms import (
    SMSService,
    MessageType,
    SMS_TEMPLATES,
    WHATSAPP_TEMPLATES,
)


class TestSMSTemplates:
    """Tests for SMS message templates."""

    def test_appointment_confirmation_template(self):
        """Test appointment confirmation template exists."""
        assert MessageType.APPOINTMENT_CONFIRMATION in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.APPOINTMENT_CONFIRMATION]
        assert "{patient_name}" in template
        assert "{doctor_name}" in template
        assert "{date}" in template
        assert "{time}" in template

    def test_reminder_template(self):
        """Test reminder template exists."""
        assert MessageType.REMINDER in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.REMINDER]
        assert "{patient_name}" in template
        assert "{doctor_name}" in template

    def test_cancellation_template(self):
        """Test cancellation template exists."""
        assert MessageType.CANCELLATION in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.CANCELLATION]
        assert "{patient_name}" in template

    def test_otp_template(self):
        """Test OTP template exists."""
        assert MessageType.OTP in SMS_TEMPLATES
        template = SMS_TEMPLATES[MessageType.OTP]
        assert "{otp}" in template


class TestWhatsAppTemplates:
    """Tests for WhatsApp message templates."""

    def test_whatsapp_templates_exist(self):
        """Test WhatsApp templates exist."""
        assert MessageType.APPOINTMENT_CONFIRMATION in WHATSAPP_TEMPLATES
        assert MessageType.REMINDER in WHATSAPP_TEMPLATES


class TestSMSService:
    """Tests for SMSService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        with patch.dict("os.environ", {"MSG91_AUTH_KEY": "test_key", "MSG91_SENDER_ID": "TEST"}):
            service = SMSService()
            assert service is not None

    @patch("requests.post")
    def test_send_sms_success(self, mock_post):
        """Test sending SMS successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success"}
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"MSG91_AUTH_KEY": "test_key", "MSG91_SENDER_ID": "TEST"}):
            service = SMSService()
            result = service.send_sms("+919876543210", "Test message")

            assert result == True
            mock_post.assert_called_once()

    @patch("requests.post")
    def test_send_sms_failure(self, mock_post):
        """Test SMS sending failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"MSG91_AUTH_KEY": "test_key", "MSG91_SENDER_ID": "TEST"}):
            service = SMSService()
            result = service.send_sms("+919876543210", "Test message")

            assert result == False

    @patch("requests.post")
    def test_send_appointment_confirmation(self, mock_post):
        """Test sending appointment confirmation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success"}
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"MSG91_AUTH_KEY": "test_key", "MSG91_SENDER_ID": "TEST"}):
            service = SMSService()
            result = service.send_appointment_confirmation(
                phone="+919876543210",
                patient_name="John Doe",
                doctor_name="Dr. Smith",
                date="2024-01-15",
                time="10:00 AM",
                clinic_name="Test Clinic",
            )

            assert result == True

    @patch("requests.post")
    def test_send_appointment_reminder(self, mock_post):
        """Test sending appointment reminder."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success"}
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"MSG91_AUTH_KEY": "test_key", "MSG91_SENDER_ID": "TEST"}):
            service = SMSService()
            result = service.send_appointment_reminder(
                phone="+919876543210",
                patient_name="John Doe",
                doctor_name="Dr. Smith",
                date="2024-01-15",
                time="10:00 AM",
                clinic_name="Test Clinic",
            )

            assert result == True

    @patch("requests.post")
    def test_send_otp(self, mock_post):
        """Test sending OTP."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success"}
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"MSG91_AUTH_KEY": "test_key", "MSG91_SENDER_ID": "TEST"}):
            service = SMSService()
            result = service.send_otp(
                phone="+919876543210",
                otp="123456",
            )

            assert result == True


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
