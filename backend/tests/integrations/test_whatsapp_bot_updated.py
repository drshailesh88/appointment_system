"""
Comprehensive tests for WhatsApp Bot Integration.

Tests webhook parsing, conversation handling, message sending, and state management.
"""
import pytest
from datetime import datetime, timezone
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


class TestWebhookVerification:
    """Test webhook verification."""

    def test_verify_webhook_success(self):
        """Test successful webhook verification."""
        bot = WhatsAppBot(verify_token="test_verify_token")

        challenge = bot.verify_webhook(
            mode="subscribe",
            token="test_verify_token",
            challenge="challenge_string_123",
        )

        assert challenge == "challenge_string_123"

    def test_verify_webhook_wrong_token(self):
        """Test webhook verification with wrong token."""
        bot = WhatsAppBot(verify_token="test_verify_token")

        challenge = bot.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="challenge_string",
        )

        assert challenge is None

    def test_verify_webhook_wrong_mode(self):
        """Test webhook verification with wrong mode."""
        bot = WhatsAppBot(verify_token="test_verify_token")

        challenge = bot.verify_webhook(
            mode="unsubscribe",
            token="test_verify_token",
            challenge="challenge_string",
        )

        assert challenge is None


class TestWebhookParsing:
    """Test webhook payload parsing."""

    def test_parse_text_message(self):
        """Test parsing text message."""
        bot = WhatsAppBot()

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "919876543210",
                            "text": {"body": "Hello, I want to book an appointment"},
                            "timestamp": "1234567890",
                        }],
                        "contacts": [{
                            "profile": {"name": "Test User"},
                        }],
                    },
                }],
            }],
        }

        message = bot.parse_webhook(payload)

        assert message is not None
        assert message.message_id == "msg_123"
        assert message.from_phone == "919876543210"
        assert message.from_name == "Test User"
        assert message.message_type == MessageType.TEXT
        assert message.text == "Hello, I want to book an appointment"

    def test_parse_button_reply(self):
        """Test parsing button reply."""
        bot = WhatsAppBot()

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_456",
                            "from": "919876543210",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "book_appointment",
                                    "title": "Book Appointment",
                                },
                            },
                        }],
                        "contacts": [{"profile": {"name": "Patient"}}],
                    },
                }],
            }],
        }

        message = bot.parse_webhook(payload)

        assert message is not None
        assert message.message_type == MessageType.BUTTON
        assert message.button_id == "book_appointment"
        assert message.button_text == "Book Appointment"

    def test_parse_list_reply(self):
        """Test parsing list reply."""
        bot = WhatsAppBot()

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_789",
                            "from": "919876543210",
                            "interactive": {
                                "type": "list_reply",
                                "list_reply": {
                                    "id": "doctor_1",
                                    "title": "Dr. Sharma",
                                },
                            },
                        }],
                        "contacts": [{"profile": {"name": "Patient"}}],
                    },
                }],
            }],
        }

        message = bot.parse_webhook(payload)

        assert message is not None
        assert message.message_type == MessageType.LIST_REPLY
        assert message.list_id == "doctor_1"
        assert message.list_title == "Dr. Sharma"

    def test_parse_invalid_webhook(self):
        """Test parsing invalid webhook."""
        bot = WhatsAppBot()

        payload = {"invalid": "data"}

        message = bot.parse_webhook(payload)

        assert message is None


class TestConversationManagement:
    """Test conversation context management."""

    def test_get_context_new(self):
        """Test getting context for new conversation."""
        bot = WhatsAppBot()
        clinic_id = uuid4()

        context = bot._get_context("+919876543210", clinic_id)

        assert context.phone == "+919876543210"
        assert context.clinic_id == clinic_id
        assert context.state == ConversationState.IDLE

    def test_get_context_existing(self):
        """Test getting existing conversation context."""
        bot = WhatsAppBot()
        clinic_id = uuid4()
        phone = "+919876543210"

        # Create existing context
        existing = bot._get_context(phone, clinic_id)
        existing.patient_name = "Test Patient"

        # Get same context
        context = bot._get_context(phone, clinic_id)

        assert context == existing
        assert context.patient_name == "Test Patient"

    def test_cleanup_stale_conversations(self):
        """Test cleanup of stale conversations."""
        bot = WhatsAppBot()

        # Create old conversation
        old_context = ConversationContext(
            phone="+919876543210",
            last_activity=datetime.now(timezone.utc) - timezone.timedelta(hours=2),
        )
        bot._conversations["+919876543210"] = old_context

        # Create recent conversation
        new_context = ConversationContext(
            phone="+919876543211",
            last_activity=datetime.now(timezone.utc),
        )
        bot._conversations["+919876543211"] = new_context

        # Cleanup with 60 minute threshold
        bot.cleanup_stale_conversations(max_age_minutes=60)

        # Old conversation should be removed
        assert "+919876543210" not in bot._conversations
        # New conversation should remain
        assert "+919876543211" in bot._conversations


class TestMessageSending:
    """Test sending WhatsApp messages."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successfully sending message."""
        bot = WhatsAppBot(
            api_token="test_token",
            phone_number_id="12345",
        )

        with patch.object(bot, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await bot.send_message(
                to_phone="+919876543210",
                text="Test message",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_send_message_no_token(self):
        """Test sending message without API token."""
        bot = WhatsAppBot(api_token=None)

        result = await bot.send_message(
            to_phone="+919876543210",
            text="Test message",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_interactive_buttons(self):
        """Test sending interactive buttons."""
        bot = WhatsAppBot(
            api_token="test_token",
            phone_number_id="12345",
        )

        with patch.object(bot, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await bot.send_interactive_buttons(
                to_phone="+919876543210",
                body="Choose an option:",
                buttons=[
                    {"id": "option1", "title": "Option 1"},
                    {"id": "option2", "title": "Option 2"},
                ],
            )

            assert result is True


class TestConversationFlows:
    """Test conversation flows."""

    @pytest.mark.asyncio
    async def test_greeting_flow(self):
        """Test greeting conversation flow."""
        bot = WhatsAppBot()
        clinic_id = uuid4()

        message = WhatsAppMessage(
            message_id="msg_123",
            from_phone="+919876543210",
            from_name="Test Patient",
            message_type=MessageType.TEXT,
            text="Hi",
        )

        async_db = AsyncMock()

        response = await bot.handle_message(message, async_db, clinic_id)

        assert response is not None
        assert "welcome" in response.lower() or "hi" in response.lower()

    @pytest.mark.asyncio
    async def test_menu_display(self):
        """Test main menu display."""
        bot = WhatsAppBot()

        context = ConversationContext(phone="+919876543210")

        response = await bot._show_main_menu(context)

        assert "book" in response.lower() or "appointment" in response.lower()
        assert "cancel" in response.lower()
        assert "status" in response.lower() or "my appointments" in response.lower()


class TestConversationContext:
    """Tests for ConversationContext dataclass."""

    def test_create_context(self):
        """Test creating conversation context."""
        phone = "+919876543210"
        clinic_id = uuid4()

        context = ConversationContext(
            phone=phone,
            clinic_id=clinic_id,
        )

        assert context.phone == phone
        assert context.clinic_id == clinic_id
        assert context.state == ConversationState.IDLE
        assert context.last_activity is not None

    def test_context_with_patient_info(self):
        """Test context with patient information."""
        patient_id = uuid4()
        doctor_id = uuid4()

        context = ConversationContext(
            phone="+919876543210",
            patient_id=patient_id,
            patient_name="John Doe",
            doctor_id=doctor_id,
            doctor_name="Dr. Smith",
        )

        assert context.patient_id == patient_id
        assert context.patient_name == "John Doe"
        assert context.doctor_id == doctor_id
        assert context.doctor_name == "Dr. Smith"


class TestMessageTypes:
    """Test MessageType enum."""

    def test_message_types_exist(self):
        """Test all message types exist."""
        assert MessageType.TEXT
        assert MessageType.BUTTON
        assert MessageType.LIST_REPLY
        assert MessageType.IMAGE
        assert MessageType.DOCUMENT


class TestConversationStates:
    """Test ConversationState enum."""

    def test_conversation_states_exist(self):
        """Test all conversation states exist."""
        assert ConversationState.IDLE
        assert ConversationState.MENU
        assert ConversationState.BOOKING_DOCTOR
        assert ConversationState.BOOKING_DATE
        assert ConversationState.BOOKING_TIME
        assert ConversationState.BOOKING_CONFIRM


class TestGetWhatsAppBot:
    """Test factory function."""

    def test_creates_bot(self):
        """Test that factory creates bot."""
        bot = get_whatsapp_bot()
        assert isinstance(bot, WhatsAppBot)

    def test_singleton_pattern(self):
        """Test singleton pattern."""
        # Reset singleton
        import app.integrations.whatsapp_bot as whatsapp_module
        whatsapp_module._whatsapp_bot = None

        bot1 = get_whatsapp_bot()
        bot2 = get_whatsapp_bot()

        assert bot1 is bot2
