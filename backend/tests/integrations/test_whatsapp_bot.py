"""
Tests for WhatsApp Bot Integration.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from app.integrations.whatsapp_bot import (
    WhatsAppBot,
    ConversationState,
    MessageType,
    WhatsAppMessage,
    ConversationContext,
    get_whatsapp_bot,
)


class TestWhatsAppBot:
    """Tests for WhatsAppBot."""

    def test_initialization(self):
        """Test bot initialization."""
        bot = WhatsAppBot(
            api_url="https://test.api.com",
            api_token="test_token",
            phone_number_id="12345",
        )
        assert bot.api_url == "https://test.api.com"
        assert bot.api_token == "test_token"
        assert bot.phone_number_id == "12345"
        assert bot._conversations == {}

    @pytest.mark.asyncio
    async def test_parse_webhook_msg91(self, bot):
        """Test parsing MSG91 webhook payload."""
        payload = {
            "user": {"mobiles": "919876543210"},
            "message": "Hello, I want to book an appointment",
            "timestamp": "2026-01-04T10:00:00Z",
        }

        result = bot.parse_webhook(payload, provider="msg91")

        assert result["phone"] == "+919876543210"
        assert result["message"] == "Hello, I want to book an appointment"

    @pytest.mark.asyncio
    async def test_parse_webhook_twilio(self, bot):
        """Test parsing Twilio webhook payload."""
        payload = {
            "From": "whatsapp:+919876543210",
            "Body": "Book appointment",
        }

        result = bot.parse_webhook(payload, provider="twilio")

        assert result["phone"] == "+919876543210"
        assert result["message"] == "Book appointment"

    @pytest.mark.asyncio
    async def test_detect_intent_book(self, bot, mock_nlu_engine):
        """Test detecting booking intent."""
        mock_nlu_engine.parse.return_value = {
            "intent": {"name": "book_appointment", "confidence": 0.9},
            "entities": [],
        }

        intent = await bot.detect_intent("I want to book an appointment")

        assert intent == MessageIntent.BOOK_APPOINTMENT

    @pytest.mark.asyncio
    async def test_detect_intent_cancel(self, bot, mock_nlu_engine):
        """Test detecting cancel intent."""
        mock_nlu_engine.parse.return_value = {
            "intent": {"name": "cancel_appointment", "confidence": 0.9},
            "entities": [],
        }

        intent = await bot.detect_intent("Cancel my appointment")

        assert intent == MessageIntent.CANCEL_APPOINTMENT

    @pytest.mark.asyncio
    async def test_detect_intent_status(self, bot, mock_nlu_engine):
        """Test detecting status check intent."""
        mock_nlu_engine.parse.return_value = {
            "intent": {"name": "check_status", "confidence": 0.85},
            "entities": [],
        }

        intent = await bot.detect_intent("What is my appointment status?")

        assert intent == MessageIntent.CHECK_STATUS

    @pytest.mark.asyncio
    async def test_detect_intent_unknown(self, bot, mock_nlu_engine):
        """Test detecting unknown intent."""
        mock_nlu_engine.parse.return_value = {
            "intent": {"name": "other", "confidence": 0.3},
            "entities": [],
        }

        intent = await bot.detect_intent("Random message")

        assert intent == MessageIntent.UNKNOWN

    @pytest.mark.asyncio
    async def test_handle_message_new_conversation(self, bot, mock_db, mock_nlu_engine):
        """Test handling message for new conversation."""
        phone = "+919876543210"
        message = "Hi, I want to book an appointment"

        mock_nlu_engine.parse.return_value = {
            "intent": {"name": "book_appointment", "confidence": 0.9},
            "entities": [],
        }

        # Mock patient lookup
        mock_patient = MagicMock()
        mock_patient.id = str(uuid4())
        mock_patient.name = "Test Patient"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_patient
        mock_db.execute.return_value = mock_result

        response = await bot.handle_message(phone, message)

        assert phone in bot.conversations
        assert response is not None

    @pytest.mark.asyncio
    async def test_handle_message_existing_conversation(self, bot, mock_db, mock_nlu_engine):
        """Test handling message in existing conversation."""
        phone = "+919876543210"

        # Set up existing conversation
        bot.conversations[phone] = ConversationState(
            phone=phone,
            patient_id=str(uuid4()),
            state="awaiting_doctor_selection",
            context={"clinic_id": str(uuid4())},
        )

        # Mock doctor selection
        mock_doctors = [
            MagicMock(id=str(uuid4()), name="Dr. Sharma"),
            MagicMock(id=str(uuid4()), name="Dr. Patel"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_doctors
        mock_db.execute.return_value = mock_result

        response = await bot.handle_message(phone, "1")  # Select first doctor

        assert response is not None
        assert bot.conversations[phone].state != "awaiting_doctor_selection"

    @pytest.mark.asyncio
    async def test_handle_cancel_confirmation(self, bot, mock_db):
        """Test handling appointment cancellation."""
        phone = "+919876543210"
        appointment_id = str(uuid4())

        bot.conversations[phone] = ConversationState(
            phone=phone,
            patient_id=str(uuid4()),
            state="awaiting_cancel_confirmation",
            context={"appointment_id": appointment_id},
        )

        # Mock appointment
        mock_appointment = MagicMock()
        mock_appointment.id = appointment_id
        mock_appointment.status = "scheduled"
        mock_db.get.return_value = mock_appointment

        response = await bot.handle_message(phone, "YES")

        assert mock_appointment.status == "cancelled"
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_send_reminder(self, bot, mock_sms_service):
        """Test sending appointment reminder."""
        appointment = MagicMock(
            id=str(uuid4()),
            patient=MagicMock(name="Test Patient", phone="+919876543210"),
            doctor=MagicMock(name="Dr. Sharma"),
            start_time=datetime.now() + timedelta(days=1),
        )

        await bot.send_reminder(appointment)

        mock_sms_service.send_whatsapp.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_confirmation(self, bot, mock_sms_service):
        """Test sending booking confirmation."""
        appointment = MagicMock(
            id=str(uuid4()),
            patient=MagicMock(name="Test Patient", phone="+919876543210"),
            doctor=MagicMock(name="Dr. Sharma"),
            start_time=datetime.now() + timedelta(days=1),
            token_number=5,
            clinic=MagicMock(address="123 Clinic St"),
        )

        await bot.send_confirmation(appointment)

        mock_sms_service.send_whatsapp.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_timeout(self, bot):
        """Test conversation session timeout."""
        phone = "+919876543210"

        # Create old conversation
        bot.conversations[phone] = ConversationState(
            phone=phone,
            patient_id=str(uuid4()),
            state="awaiting_input",
            context={},
            last_activity=datetime.now() - timedelta(hours=2),
        )

        is_expired = bot.is_session_expired(phone)
        assert is_expired

    @pytest.mark.asyncio
    async def test_session_not_expired(self, bot):
        """Test conversation session not expired."""
        phone = "+919876543210"

        # Create recent conversation
        bot.conversations[phone] = ConversationState(
            phone=phone,
            patient_id=str(uuid4()),
            state="awaiting_input",
            context={},
            last_activity=datetime.now() - timedelta(minutes=5),
        )

        is_expired = bot.is_session_expired(phone)
        assert not is_expired


class TestConversationState:
    """Tests for ConversationState."""

    def test_create_state(self):
        """Test creating conversation state."""
        state = ConversationState(
            phone="+919876543210",
            patient_id=str(uuid4()),
            state="initial",
            context={"clinic_id": str(uuid4())},
        )

        assert state.phone == "+919876543210"
        assert state.state == "initial"
        assert state.context is not None

    def test_state_with_default_values(self):
        """Test conversation state with default values."""
        state = ConversationState(
            phone="+919876543210",
        )

        assert state.patient_id is None
        assert state.state == "initial"
        assert state.context == {}
        assert state.last_activity is not None


class TestMessageIntent:
    """Tests for MessageIntent enum."""

    def test_intent_values(self):
        """Test intent enum values."""
        assert MessageIntent.BOOK_APPOINTMENT.value == "book_appointment"
        assert MessageIntent.CANCEL_APPOINTMENT.value == "cancel_appointment"
        assert MessageIntent.RESCHEDULE.value == "reschedule"
        assert MessageIntent.CHECK_STATUS.value == "check_status"
        assert MessageIntent.GREETING.value == "greeting"
        assert MessageIntent.HELP.value == "help"
        assert MessageIntent.UNKNOWN.value == "unknown"


class TestGetWhatsAppBot:
    """Tests for factory function."""

    def test_creates_bot(self):
        """Test that factory creates bot."""
        mock_db = AsyncMock()
        bot = get_whatsapp_bot(mock_db)
        assert isinstance(bot, WhatsAppBot)
        assert bot.db == mock_db

    def test_singleton_pattern(self):
        """Test that factory returns same instance."""
        mock_db = AsyncMock()

        # Reset singleton
        import app.integrations.whatsapp_bot as whatsapp_module
        whatsapp_module._whatsapp_bot = None

        bot1 = get_whatsapp_bot(mock_db)
        bot2 = get_whatsapp_bot(mock_db)

        assert bot1 is bot2


class TestWebhookHandling:
    """Tests for webhook handling scenarios."""

    @pytest.fixture
    def bot(self):
        """Create bot for webhook tests."""
        mock_db = AsyncMock()
        return WhatsAppBot(mock_db)

    def test_parse_invalid_webhook(self, bot):
        """Test parsing invalid webhook payload."""
        result = bot.parse_webhook({}, provider="msg91")
        assert result is None or result.get("phone") is None

    def test_parse_webhook_extracts_phone_formats(self, bot):
        """Test phone number format extraction."""
        test_cases = [
            ({"user": {"mobiles": "9876543210"}}, "+919876543210"),
            ({"user": {"mobiles": "+919876543210"}}, "+919876543210"),
            ({"user": {"mobiles": "919876543210"}}, "+919876543210"),
        ]

        for payload, expected_phone in test_cases:
            result = bot.parse_webhook(payload, provider="msg91")
            if result:
                assert result["phone"] == expected_phone
