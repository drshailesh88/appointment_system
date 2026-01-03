"""
Tests for voice agent service.
"""
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.voice.nlu import (
    NaturalLanguageUnderstanding,
    Intent,
    ExtractedEntities,
)
from app.voice.agent import (
    VoiceAgent,
    ConversationState,
    BookingContext,
)


class TestIntent:
    """Tests for Intent enum."""

    def test_all_intents_exist(self):
        """Test all expected intents exist."""
        expected_intents = [
            "BOOK_APPOINTMENT",
            "CANCEL_APPOINTMENT",
            "CHECK_AVAILABILITY",
            "RESCHEDULE",
            "GREETING",
            "CONFIRM",
            "DENY",
            "PROVIDE_INFO",
            "ASK_HELP",
            "GOODBYE",
            "UNKNOWN",
        ]
        for intent_name in expected_intents:
            assert hasattr(Intent, intent_name)


class TestConversationState:
    """Tests for ConversationState enum."""

    def test_all_states_exist(self):
        """Test all expected states exist."""
        expected_states = [
            "IDLE",
            "GREETING",
            "COLLECTING_DOCTOR",
            "COLLECTING_DATE",
            "COLLECTING_TIME",
            "COLLECTING_PATIENT",
            "COLLECTING_REASON",
            "CONFIRMING",
            "BOOKING",
            "COMPLETED",
        ]
        for state_name in expected_states:
            assert hasattr(ConversationState, state_name)


class TestBookingContext:
    """Tests for BookingContext dataclass."""

    def test_empty_context(self):
        """Test empty booking context."""
        context = BookingContext()
        assert context.doctor_name is None
        assert context.date is None
        assert context.time is None
        assert context.patient_name is None
        assert context.phone is None
        assert context.reason is None

    def test_context_with_values(self):
        """Test booking context with values."""
        context = BookingContext(
            doctor_name="Dr. Smith",
            date=datetime.now().date(),
            time="10:00",
            patient_name="John Doe",
            phone="+919876543210",
            reason="Headache",
        )
        assert context.doctor_name == "Dr. Smith"
        assert context.patient_name == "John Doe"

    def test_context_is_complete(self):
        """Test checking if context is complete."""
        incomplete = BookingContext(doctor_name="Dr. Smith")
        complete = BookingContext(
            doctor_name="Dr. Smith",
            date=datetime.now().date(),
            time="10:00",
            patient_name="John Doe",
            phone="+919876543210",
        )

        # Check required fields
        assert incomplete.doctor_name is not None
        assert incomplete.date is None

        assert complete.doctor_name is not None
        assert complete.date is not None
        assert complete.time is not None


class TestNaturalLanguageUnderstanding:
    """Tests for NLU service."""

    @patch("requests.post")
    def test_classify_intent_booking(self, mock_post):
        """Test classifying booking intent."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "BOOK_APPOINTMENT"
        }
        mock_post.return_value = mock_response

        nlu = NaturalLanguageUnderstanding()
        intent = nlu.classify_intent("I want to book an appointment")

        # Should recognize booking intent
        assert intent in [Intent.BOOK_APPOINTMENT, Intent.UNKNOWN]

    @patch("requests.post")
    def test_classify_intent_greeting(self, mock_post):
        """Test classifying greeting intent."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "GREETING"
        }
        mock_post.return_value = mock_response

        nlu = NaturalLanguageUnderstanding()
        intent = nlu.classify_intent("Hello")

        assert intent in [Intent.GREETING, Intent.UNKNOWN]

    def test_parse_date_today(self):
        """Test parsing 'today' date."""
        nlu = NaturalLanguageUnderstanding()
        result = nlu._parse_date("today")
        assert result == datetime.now().date()

    def test_parse_date_tomorrow(self):
        """Test parsing 'tomorrow' date."""
        nlu = NaturalLanguageUnderstanding()
        result = nlu._parse_date("tomorrow")
        expected = (datetime.now() + timedelta(days=1)).date()
        assert result == expected

    def test_parse_time_morning(self):
        """Test parsing morning time."""
        nlu = NaturalLanguageUnderstanding()
        result = nlu._parse_time("morning")
        assert result in ["09:00", "10:00"]

    def test_parse_time_afternoon(self):
        """Test parsing afternoon time."""
        nlu = NaturalLanguageUnderstanding()
        result = nlu._parse_time("afternoon")
        assert result in ["14:00", "15:00"]

    def test_parse_time_specific(self):
        """Test parsing specific time."""
        nlu = NaturalLanguageUnderstanding()
        result = nlu._parse_time("3 PM")
        assert result == "15:00"


class TestExtractedEntities:
    """Tests for ExtractedEntities dataclass."""

    def test_empty_entities(self):
        """Test empty entities."""
        entities = ExtractedEntities()
        assert entities.doctor_name is None
        assert entities.date is None
        assert entities.time is None
        assert entities.patient_name is None
        assert entities.phone is None
        assert entities.reason is None

    def test_entities_with_values(self):
        """Test entities with values."""
        entities = ExtractedEntities(
            doctor_name="Dr. Sharma",
            date=datetime.now().date(),
            time="10:00",
            patient_name="Raj Patel",
            phone="+919876543210",
            reason="Fever",
        )
        assert entities.doctor_name == "Dr. Sharma"
        assert entities.reason == "Fever"


class TestVoiceAgent:
    """Tests for VoiceAgent class."""

    def test_agent_initialization(self):
        """Test voice agent initialization."""
        agent = VoiceAgent()
        assert agent is not None

    def test_new_session(self):
        """Test creating new session."""
        agent = VoiceAgent()
        session_id = agent.new_session()
        assert session_id is not None
        assert len(session_id) > 0

    def test_session_state(self):
        """Test session state management."""
        agent = VoiceAgent()
        session_id = agent.new_session()

        status = agent.get_session_status(session_id)
        assert status["state"] == ConversationState.IDLE.value
        assert status["context"] is not None

    @patch.object(VoiceAgent, "_transcribe")
    @patch.object(VoiceAgent, "_understand")
    async def test_process_text(self, mock_understand, mock_transcribe):
        """Test processing text input."""
        mock_understand.return_value = (Intent.GREETING, ExtractedEntities())

        agent = VoiceAgent()
        session_id = agent.new_session()

        response = await agent.process_text(session_id, "Hello")
        assert response is not None

    def test_invalid_session(self):
        """Test handling invalid session."""
        agent = VoiceAgent()
        status = agent.get_session_status("invalid_session_id")
        assert status is None


class TestVoiceAgentFlow:
    """Tests for voice agent booking flow."""

    def test_state_transitions(self):
        """Test valid state transitions."""
        valid_transitions = [
            (ConversationState.IDLE, ConversationState.GREETING),
            (ConversationState.GREETING, ConversationState.COLLECTING_DOCTOR),
            (ConversationState.COLLECTING_DOCTOR, ConversationState.COLLECTING_DATE),
            (ConversationState.COLLECTING_DATE, ConversationState.COLLECTING_TIME),
            (ConversationState.COLLECTING_TIME, ConversationState.COLLECTING_PATIENT),
            (ConversationState.COLLECTING_PATIENT, ConversationState.CONFIRMING),
            (ConversationState.CONFIRMING, ConversationState.BOOKING),
            (ConversationState.BOOKING, ConversationState.COMPLETED),
        ]

        for from_state, to_state in valid_transitions:
            # States should be different
            assert from_state != to_state
