"""
Tests for WhatsApp Bot Integration.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4, UUID

from app.integrations.whatsapp_bot import (
    WhatsAppBot,
    WhatsAppMessage,
    ConversationState,
    ConversationContext,
    MessageType,
    MessageIntent,
    get_whatsapp_bot,
)
from app.voice.nlu import Intent


class TestWhatsAppBot:
    """Tests for WhatsAppBot."""

    @pytest.fixture
    def bot(self):
        """Create WhatsApp bot with test config."""
        return WhatsAppBot(
            api_token="test_token",
            phone_number_id="123456789",
            verify_token="test_verify"
        )

    def test_initialization(self):
        """Test bot initialization."""
        bot = WhatsAppBot(
            api_token="test_token",
            phone_number_id="123456789"
        )
        assert bot.api_token == "test_token"
        assert bot.phone_number_id == "123456789"
        assert bot._conversations == {}

    def test_parse_webhook_whatsapp(self, bot):
        """Test parsing WhatsApp Business API webhook payload."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "919876543210",
                            "text": {
                                "body": "Hello, I want to book an appointment"
                            }
                        }],
                        "contacts": [{
                            "profile": {
                                "name": "Test Patient"
                            }
                        }]
                    }
                }]
            }]
        }

        result = bot.parse_webhook(payload)

        assert result is not None
        assert result.from_phone == "919876543210"
        assert result.text == "Hello, I want to book an appointment"
        assert result.from_name == "Test Patient"
        assert result.message_type == MessageType.TEXT

    def test_parse_webhook_with_button(self, bot):
        """Test parsing webhook with button reply."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "919876543210",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "book_appointment",
                                    "title": "Book Appointment"
                                }
                            }
                        }],
                        "contacts": [{
                            "profile": {"name": "Test Patient"}
                        }]
                    }
                }]
            }]
        }

        result = bot.parse_webhook(payload)

        assert result is not None
        assert result.message_type == MessageType.BUTTON
        assert result.button_id == "book_appointment"
        assert result.button_text == "Book Appointment"

    def test_verify_webhook(self, bot):
        """Test webhook verification."""
        result = bot.verify_webhook(
            mode="subscribe",
            token="test_verify",
            challenge="challenge_123"
        )

        assert result == "challenge_123"

    def test_verify_webhook_invalid(self, bot):
        """Test webhook verification with invalid token."""
        result = bot.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="challenge_123"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_handle_message_greeting(self, bot):
        """Test handling greeting message."""
        message = WhatsAppMessage(
            message_id="msg_123",
            from_phone="919876543210",
            from_name="Test Patient",
            message_type=MessageType.TEXT,
            text="Hi"
        )

        mock_db = AsyncMock()
        clinic_id = uuid4()

        response = await bot.handle_message(message, mock_db, clinic_id)

        assert response is not None
        assert "Welcome to DocAssist" in response

    @pytest.mark.asyncio
    async def test_handle_message_book_appointment(self, bot):
        """Test handling book appointment request."""
        message = WhatsAppMessage(
            message_id="msg_123",
            from_phone="919876543210",
            from_name="Test Patient",
            message_type=MessageType.TEXT,
            text="book"
        )

        mock_db = AsyncMock()
        clinic_id = uuid4()

        # Mock doctors query
        mock_doctor = MagicMock()
        mock_doctor.id = uuid4()
        mock_doctor.name = "Sharma"
        mock_doctor.specialization = "Cardiologist"

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_doctor]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await bot.handle_message(message, mock_db, clinic_id)

        assert response is not None
        assert "select a doctor" in response.lower()

    @pytest.mark.asyncio
    async def test_send_message(self, bot):
        """Test sending a message."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(bot, '_get_client', return_value=mock_client):
            result = await bot.send_message(
                to_phone="919876543210",
                text="Test message"
            )

            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        """Test sending message when not configured."""
        bot = WhatsAppBot(api_token=None)

        result = await bot.send_message(
            to_phone="919876543210",
            text="Test message"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_interactive_buttons(self, bot):
        """Test sending message with interactive buttons."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(bot, '_get_client', return_value=mock_client):
            result = await bot.send_interactive_buttons(
                to_phone="919876543210",
                body="Choose an option",
                buttons=[
                    {"id": "opt1", "title": "Option 1"},
                    {"id": "opt2", "title": "Option 2"}
                ]
            )

            assert result is True
            mock_client.post.assert_called_once()

    def test_cleanup_stale_conversations(self, bot):
        """Test cleaning up old conversations."""
        phone1 = "919876543210"
        phone2 = "919876543211"

        # Create old conversation
        old_context = ConversationContext(phone=phone1)
        old_context.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        bot._conversations[phone1] = old_context

        # Create recent conversation
        recent_context = ConversationContext(phone=phone2)
        recent_context.last_activity = datetime.now(timezone.utc)
        bot._conversations[phone2] = recent_context

        # Cleanup with 60 min max age
        bot.cleanup_stale_conversations(max_age_minutes=60)

        assert phone1 not in bot._conversations
        assert phone2 in bot._conversations


class TestConversationContext:
    """Tests for ConversationContext."""

    def test_create_context(self):
        """Test creating conversation context."""
        context = ConversationContext(
            phone="+919876543210",
            clinic_id=uuid4(),
            patient_id=uuid4(),
        )

        assert context.phone == "+919876543210"
        assert context.state == ConversationState.IDLE
        assert context.clinic_id is not None
        assert context.patient_id is not None

    def test_context_with_defaults(self):
        """Test conversation context with default values."""
        context = ConversationContext(phone="+919876543210")

        assert context.patient_id is None
        assert context.state == ConversationState.IDLE
        assert context.message_history == []
        assert context.last_activity is not None


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
        # Reset singleton first
        import app.integrations.whatsapp_bot as whatsapp_module
        whatsapp_module._whatsapp_bot = None

        bot = get_whatsapp_bot()
        assert isinstance(bot, WhatsAppBot)

    def test_singleton_pattern(self):
        """Test that factory returns same instance."""
        # Reset singleton
        import app.integrations.whatsapp_bot as whatsapp_module
        whatsapp_module._whatsapp_bot = None

        bot1 = get_whatsapp_bot()
        bot2 = get_whatsapp_bot()

        assert bot1 is bot2


class TestWebhookHandling:
    """Tests for webhook handling scenarios."""

    @pytest.fixture
    def bot(self):
        """Create bot for webhook tests."""
        return WhatsAppBot(api_token="test_token")

    def test_parse_invalid_webhook(self, bot):
        """Test parsing invalid webhook payload."""
        result = bot.parse_webhook({})
        assert result is None

    def test_parse_webhook_missing_messages(self, bot):
        """Test parsing webhook with missing messages."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": []
                    }
                }]
            }]
        }

        result = bot.parse_webhook(payload)
        assert result is None

    def test_parse_webhook_with_image(self, bot):
        """Test parsing webhook with image message."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "919876543210",
                            "image": {
                                "id": "image_123"
                            }
                        }],
                        "contacts": [{
                            "profile": {"name": "Test Patient"}
                        }]
                    }
                }]
            }]
        }

        result = bot.parse_webhook(payload)

        assert result is not None
        assert result.message_type == MessageType.IMAGE

    def test_parse_webhook_with_document(self, bot):
        """Test parsing webhook with document message."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "919876543210",
                            "document": {
                                "id": "doc_123"
                            }
                        }],
                        "contacts": [{
                            "profile": {"name": "Test Patient"}
                        }]
                    }
                }]
            }]
        }

        result = bot.parse_webhook(payload)

        assert result is not None
        assert result.message_type == MessageType.DOCUMENT


class TestWhatsAppMessage:
    """Tests for WhatsAppMessage dataclass."""

    def test_create_message(self):
        """Test creating WhatsApp message."""
        msg = WhatsAppMessage(
            message_id="msg_123",
            from_phone="919876543210",
            from_name="Test Patient",
            message_type=MessageType.TEXT,
            text="Hello"
        )

        assert msg.message_id == "msg_123"
        assert msg.from_phone == "919876543210"
        assert msg.text == "Hello"
        assert msg.message_type == MessageType.TEXT

    def test_message_with_button(self):
        """Test creating message with button."""
        msg = WhatsAppMessage(
            message_id="msg_123",
            from_phone="919876543210",
            from_name="Test Patient",
            message_type=MessageType.BUTTON,
            button_id="btn_1",
            button_text="Book Now",
            text="Book Now"
        )

        assert msg.message_type == MessageType.BUTTON
        assert msg.button_id == "btn_1"
        assert msg.button_text == "Book Now"
