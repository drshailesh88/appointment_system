"""
Tests for AI Assistant Service.

Phase 16a: Practice AI Assistant
"""

import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4

from app.services.ai_assistant import (
    PracticeAIAssistant,
    FunctionName,
    FunctionCall,
    ConversationSession,
    Message,
)


class TestAIAssistant:
    """Test AI Assistant service."""

    @pytest.fixture
    def assistant(self):
        """Create AI assistant instance."""
        return PracticeAIAssistant()

    @pytest.fixture
    def clinic_id(self):
        """Sample clinic ID."""
        return uuid4()

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return uuid4()

    @pytest.mark.asyncio


    async def test_fallback_parse_procedure_query(self, assistant):
        """Test fallback parsing for procedure queries."""
        result = assistant._fallback_parse("How many echos this month?")

        assert result is not None
        assert result.function == FunctionName.GET_PROCEDURE_STATS
        assert "start_date" in result.arguments
        assert "end_date" in result.arguments

    @pytest.mark.asyncio


    async def test_fallback_parse_revenue_query(self, assistant):
        """Test fallback parsing for revenue queries."""
        result = assistant._fallback_parse("What's my revenue today?")

        assert result is not None
        assert result.function == FunctionName.GET_REVENUE_ANALYTICS
        assert result.arguments["start_date"] == date.today()
        assert result.arguments["end_date"] == date.today()

    @pytest.mark.asyncio


    async def test_fallback_parse_appointment_query(self, assistant):
        """Test fallback parsing for appointment queries."""
        result = assistant._fallback_parse("No-show rate this week")

        assert result is not None
        assert result.function == FunctionName.GET_APPOINTMENT_STATS

    @pytest.mark.asyncio


    async def test_fallback_parse_patient_search(self, assistant):
        """Test fallback parsing for patient search."""
        result = assistant._fallback_parse("Find patient Ramesh")

        assert result is not None
        assert result.function == FunctionName.SEARCH_PATIENTS
        assert "query" in result.arguments

    @pytest.mark.asyncio


    async def test_fallback_parse_doctor_query(self, assistant):
        """Test fallback parsing for doctor stats."""
        result = assistant._fallback_parse("Dr. Sharma's performance this month")

        assert result is not None
        assert result.function == FunctionName.GET_DOCTOR_STATS

    @pytest.mark.asyncio


    async def test_parse_relative_date_today(self, assistant):
        """Test parsing 'today'."""
        result = assistant._parse_relative_date("today")
        assert result == date.today()

    @pytest.mark.asyncio


    async def test_parse_relative_date_yesterday(self, assistant):
        """Test parsing 'yesterday'."""
        result = assistant._parse_relative_date("yesterday")
        assert result == date.today() - timedelta(days=1)

    @pytest.mark.asyncio


    async def test_parse_relative_date_this_week(self, assistant):
        """Test parsing 'this week start'."""
        result = assistant._parse_relative_date("this week start")
        today = date.today()
        expected = today - timedelta(days=today.weekday())
        assert result == expected

    @pytest.mark.asyncio


    async def test_parse_relative_date_this_month(self, assistant):
        """Test parsing 'this month start'."""
        result = assistant._parse_relative_date("this month start")
        assert result == date.today().replace(day=1)

    @pytest.mark.asyncio


    async def test_parse_relative_date_last_month(self, assistant):
        """Test parsing 'last month start'."""
        result = assistant._parse_relative_date("last month start")
        today = date.today()
        first = today.replace(day=1)
        last_month = first - timedelta(days=1)
        assert result == last_month.replace(day=1)

    @pytest.mark.asyncio


    async def test_generate_suggestions_procedure(self, assistant):
        """Test suggestion generation for procedure stats."""
        function_call = FunctionCall(
            function=FunctionName.GET_PROCEDURE_STATS,
            arguments={},
        )
        suggestions = assistant._generate_suggestions(function_call, {})

        assert len(suggestions) > 0
        assert any("doctor" in s.lower() for s in suggestions)

    @pytest.mark.asyncio


    async def test_generate_suggestions_revenue(self, assistant):
        """Test suggestion generation for revenue analytics."""
        function_call = FunctionCall(
            function=FunctionName.GET_REVENUE_ANALYTICS,
            arguments={},
        )
        suggestions = assistant._generate_suggestions(function_call, {})

        assert len(suggestions) > 0
        assert any("breakdown" in s.lower() or "outstanding" in s.lower() for s in suggestions)

    @pytest.mark.asyncio


    async def test_mock_procedure_stats(self, assistant):
        """Test mock procedure stats response."""
        response, data = assistant._mock_procedure_stats({})

        assert "procedures" in response.lower()
        assert "total" in data
        assert "by_category" in data
        assert data["total"] > 0

    @pytest.mark.asyncio


    async def test_mock_revenue_analytics(self, assistant):
        """Test mock revenue analytics response."""
        response, data = assistant._mock_revenue_analytics({})

        assert "revenue" in response.lower()
        assert "total_revenue" in data
        assert "collected" in data
        assert "pending" in data

    @pytest.mark.asyncio


    async def test_mock_appointment_stats(self, assistant):
        """Test mock appointment stats response."""
        response, data = assistant._mock_appointment_stats({})

        assert "appointment" in response.lower()
        assert "total" in data
        assert "completed" in data
        assert "no_show" in data

    @pytest.mark.asyncio


    async def test_session_management(self, assistant, clinic_id, user_id):
        """Test session creation and retrieval."""
        session_id = str(uuid4())
        session = ConversationSession(
            session_id=session_id,
            user_id=str(user_id),
            clinic_id=str(clinic_id),
        )

        # Store session
        assistant._sessions[session_id] = session

        # Retrieve session
        retrieved = assistant.get_session(session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id
        assert retrieved.user_id == str(user_id)

    @pytest.mark.asyncio


    async def test_session_clear(self, assistant, clinic_id, user_id):
        """Test session clearing."""
        session_id = str(uuid4())
        session = ConversationSession(
            session_id=session_id,
            user_id=str(user_id),
            clinic_id=str(clinic_id),
        )

        assistant._sessions[session_id] = session

        # Clear session
        success = assistant.clear_session(session_id)
        assert success is True

        # Verify cleared
        retrieved = assistant.get_session(session_id)
        assert retrieved is None

    @pytest.mark.asyncio


    async def test_session_cleanup(self, assistant, clinic_id, user_id):
        """Test cleanup of old sessions."""
        # Create old session
        old_session_id = str(uuid4())
        old_session = ConversationSession(
            session_id=old_session_id,
            user_id=str(user_id),
            clinic_id=str(clinic_id),
            created_at=datetime.utcnow() - timedelta(hours=25),
            updated_at=datetime.utcnow() - timedelta(hours=25),
        )
        assistant._sessions[old_session_id] = old_session

        # Create recent session
        new_session_id = str(uuid4())
        new_session = ConversationSession(
            session_id=new_session_id,
            user_id=str(user_id),
            clinic_id=str(clinic_id),
        )
        assistant._sessions[new_session_id] = new_session

        # Cleanup with 24 hour threshold
        assistant.cleanup_old_sessions(max_age_hours=24)

        # Old session should be removed
        assert assistant.get_session(old_session_id) is None

        # New session should remain
        assert assistant.get_session(new_session_id) is not None

    @pytest.mark.asyncio
    @pytest.mark.asyncio

    async def test_chat_creates_session(self, assistant, clinic_id, user_id):
        """Test that chat creates a new session."""
        response = await assistant.chat(
            message="How many procedures this month?",
            clinic_id=clinic_id,
            user_id=user_id,
        )

        assert response.session_id is not None
        assert len(response.response) > 0

        # Session should exist
        session = assistant.get_session(response.session_id)
        assert session is not None
        assert len(session.messages) == 2  # User + Assistant

    @pytest.mark.asyncio
    @pytest.mark.asyncio

    async def test_chat_continues_session(self, assistant, clinic_id, user_id):
        """Test that chat continues existing session."""
        # First message
        response1 = await assistant.chat(
            message="How many procedures this month?",
            clinic_id=clinic_id,
            user_id=user_id,
        )
        session_id = response1.session_id

        # Follow-up message
        response2 = await assistant.chat(
            message="Breakdown by doctor",
            clinic_id=clinic_id,
            user_id=user_id,
            session_id=session_id,
        )

        assert response2.session_id == session_id

        # Session should have 4 messages now
        session = assistant.get_session(session_id)
        assert len(session.messages) == 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    @pytest.mark.asyncio

    async def test_chat_provides_suggestions(self, assistant, clinic_id, user_id):
        """Test that chat provides follow-up suggestions."""
        response = await assistant.chat(
            message="Revenue this month",
            clinic_id=clinic_id,
            user_id=user_id,
        )

        assert len(response.suggestions) > 0
        assert response.data is not None

    @pytest.mark.asyncio
    @pytest.mark.asyncio

    async def test_chat_handles_unclear_query(self, assistant, clinic_id, user_id):
        """Test that chat handles unclear queries gracefully."""
        response = await assistant.chat(
            message="Tell me something",
            clinic_id=clinic_id,
            user_id=user_id,
        )

        assert len(response.response) > 0
        assert "help" in response.response.lower() or "can" in response.response.lower()
        assert len(response.suggestions) > 0
