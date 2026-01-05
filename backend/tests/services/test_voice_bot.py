"""
Tests for voice bot service.

Phase 18: Voice Bot / Phone Automation
"""

import pytest
from uuid import uuid4

from app.services.voice_bot import AppointmentBookingBot, ConversationState


class TestConversationState:
    """Test conversation state management."""

    def test_conversation_state_initialization(self):
        """Test conversation state initialization."""
        call_id = uuid4()
        clinic_id = uuid4()

        state = ConversationState(call_id=call_id, clinic_id=clinic_id)

        assert state.call_id == call_id
        assert state.clinic_id == clinic_id
        assert state.language == "hi"  # Default Hindi
        assert state.patient_name is None
        assert state.intent is None
        assert state.awaiting_confirmation is False
        assert len(state.conversation_history) == 0

    def test_conversation_state_updates(self):
        """Test updating conversation state."""
        state = ConversationState(call_id=uuid4(), clinic_id=uuid4())

        # Update fields
        state.patient_name = "Rajesh Kumar"
        state.language = "en"
        state.intent = "book_appointment"
        state.extracted_date = "tomorrow"
        state.extracted_time = "3pm"

        assert state.patient_name == "Rajesh Kumar"
        assert state.language == "en"
        assert state.intent == "book_appointment"
        assert state.extracted_date == "tomorrow"
        assert state.extracted_time == "3pm"


class TestAppointmentBookingBot:
    """Test appointment booking bot."""

    @pytest.fixture
    def bot(self, db_session):
        """Create bot instance for testing."""
        clinic_id = uuid4()
        return AppointmentBookingBot(db_session, clinic_id)

    def test_detect_intent_hindi(self, bot):
        """Test intent detection in Hindi."""
        # Book appointment
        assert bot._detect_intent("मुझे अपॉइंटमेंट बुक करनी है") == "book_appointment"
        assert bot._detect_intent("डॉक्टर से मिलना है") == "book_appointment"

        # Check availability
        assert bot._detect_intent("क्या कल का समय खाली है?") == "check_availability"

        # Cancel
        assert bot._detect_intent("मुझे अपॉइंटमेंट रद्द करनी है") == "cancel_appointment"

        # Confirm
        assert bot._detect_intent("हाँ") == "confirm"
        assert bot._detect_intent("जी हां") == "confirm"

        # Deny
        assert bot._detect_intent("नहीं") == "deny"

        # Goodbye
        assert bot._detect_intent("धन्यवाद") == "goodbye"

    def test_detect_intent_english(self, bot):
        """Test intent detection in English."""
        # Book appointment
        assert bot._detect_intent("I want to book an appointment") == "book_appointment"
        assert bot._detect_intent("Need an appointment with doctor") == "book_appointment"

        # Check availability
        assert bot._detect_intent("Is there a slot available tomorrow?") == "check_availability"

        # Cancel
        assert bot._detect_intent("I want to cancel my appointment") == "cancel_appointment"

        # Confirm
        assert bot._detect_intent("yes") == "confirm"
        assert bot._detect_intent("okay, confirm it") == "confirm"

        # Deny
        assert bot._detect_intent("no") == "deny"

        # Goodbye
        assert bot._detect_intent("thank you") == "goodbye"

    def test_detect_language_hindi(self, bot):
        """Test language detection for Hindi."""
        assert bot._detect_language("नमस्ते, मैं अपॉइंटमेंट बुक करना चाहता हूं") == "hi"
        assert bot._detect_language("कल का समय बताइए") == "hi"

    def test_detect_language_tamil(self, bot):
        """Test language detection for Tamil."""
        assert bot._detect_language("வணக்கம், நான் சந்திப்பை முன்பதிவு செய்ய விரும்புகிறேன்") == "ta"

    def test_detect_language_telugu(self, bot):
        """Test language detection for Telugu."""
        assert bot._detect_language("నమస్కారం, నేను అపాయింట్‌మెంట్ బుక్ చేయాలనుకుంటున్నాను") == "te"

    def test_detect_language_english(self, bot):
        """Test language detection for English."""
        assert bot._detect_language("Hello, I want to book an appointment") == "en"
        assert bot._detect_language("What time is available tomorrow?") == "en"

    def test_get_prompt_hindi(self, bot):
        """Test getting prompts in Hindi."""
        bot.state.language = "hi"

        assert "नाम" in bot._get_prompt("ask_name")
        assert "दिन" in bot._get_prompt("ask_date") or "किस" in bot._get_prompt("ask_date")
        assert "समय" in bot._get_prompt("ask_time")
        assert "धन्यवाद" in bot._get_prompt("goodbye")

    def test_get_prompt_english(self, bot):
        """Test getting prompts in English."""
        bot.state.language = "en"

        assert "name" in bot._get_prompt("ask_name").lower()
        assert "date" in bot._get_prompt("ask_date").lower() or "day" in bot._get_prompt("ask_date").lower()
        assert "time" in bot._get_prompt("ask_time").lower()
        assert "thank" in bot._get_prompt("goodbye").lower()

    def test_conversation_history(self, bot):
        """Test conversation history tracking."""
        bot.state.conversation_history = [
            {"speaker": "bot", "text": "Hello", "timestamp": "2026-01-05T10:00:00"},
            {"speaker": "caller", "text": "Hi", "timestamp": "2026-01-05T10:00:05"},
            {"speaker": "bot", "text": "How can I help?", "timestamp": "2026-01-05T10:00:10"},
        ]

        transcript = bot.get_full_transcript()

        assert "BOT: Hello" in transcript
        assert "CALLER: Hi" in transcript
        assert "BOT: How can I help?" in transcript

    def test_greeting_new_caller(self, bot):
        """Test greeting for new caller (no patient record)."""
        # This is an async test, would need async test setup
        # For now, just test the greeting logic
        assert bot.GREETINGS["hi"] is not None
        assert bot.GREETINGS["en"] is not None
        assert "DocAssist" in bot.GREETINGS["hi"]
        assert "DocAssist" in bot.GREETINGS["en"]

    def test_personalized_greeting(self, bot):
        """Test personalized greeting for known patient."""
        bot.state.patient_name = "Rajesh Kumar"

        template_hi = bot.PERSONALIZED_GREETINGS["hi"]
        greeting_hi = template_hi.format(name="Rajesh")

        assert "Rajesh" in greeting_hi
        assert "DocAssist" in greeting_hi

        template_en = bot.PERSONALIZED_GREETINGS["en"]
        greeting_en = template_en.format(name="Rajesh")

        assert "Rajesh" in greeting_en
        assert "DocAssist" in greeting_en


class TestTelephonyService:
    """Test telephony service."""

    def test_twiml_generation(self):
        """Test TwiML generation."""
        from app.services.voice_bot.telephony import TelephonyService

        service = TelephonyService(
            account_sid="test_sid",
            auth_token="test_token",
            phone_number="+919876543210",
            webhook_url="https://example.com",
        )

        # Test TwiML connect generation
        twiml = service.generate_twiml_connect("test_call_sid")

        assert "<?xml" in twiml
        assert "Stream" in twiml
        assert "test_call_sid" in twiml
        assert service.webhook_url in twiml

    def test_twiml_say_generation(self):
        """Test TwiML say generation."""
        from app.services.voice_bot.telephony import TelephonyService

        service = TelephonyService(
            account_sid="test_sid",
            auth_token="test_token",
            phone_number="+919876543210",
            webhook_url="https://example.com",
        )

        # Test TwiML say for Hindi
        twiml_hi = service.generate_twiml_say("नमस्ते", language="hi")
        assert "<?xml" in twiml_hi
        assert "Say" in twiml_hi

        # Test TwiML say for English
        twiml_en = service.generate_twiml_say("Hello", language="en")
        assert "<?xml" in twiml_en
        assert "Say" in twiml_en


# Integration tests would require:
# - Mock Twilio client
# - Mock database
# - Mock STT/TTS services
# - WebSocket testing
# These should be added for production use

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
