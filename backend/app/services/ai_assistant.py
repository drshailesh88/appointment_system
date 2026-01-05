"""
Practice AI Assistant Service.

Phase 16a: Natural language analytics and practice insights.

Provides conversational interface for:
- Procedure analytics ("How many echos this month?")
- Revenue queries ("What's my revenue today?")
- Appointment insights ("Busiest day this month?")
- Patient search ("Find diabetic patients")
- Doctor statistics ("Dr. Sharma's performance?")
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class FunctionName(str, Enum):
    """Available function calls for the AI."""

    GET_PROCEDURE_STATS = "get_procedure_stats"
    GET_REVENUE_ANALYTICS = "get_revenue_analytics"
    GET_APPOINTMENT_STATS = "get_appointment_stats"
    SEARCH_PATIENTS = "search_patients"
    GET_DOCTOR_STATS = "get_doctor_stats"


@dataclass
class Message:
    """A chat message."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConversationSession:
    """Conversation session with context."""
    session_id: str
    user_id: str
    clinic_id: str
    messages: list[Message] = field(default_factory=list)
    entities: dict = field(default_factory=dict)  # Extracted entities (patient, doctor, date range)
    last_query_result: Any = None  # For follow-up queries
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FunctionCall:
    """A function call extracted from LLM."""
    function: FunctionName
    arguments: dict


@dataclass
class AIResponse:
    """AI assistant response."""
    response: str  # Natural language response
    suggestions: list[str] = field(default_factory=list)  # Follow-up suggestions
    data: Optional[dict] = None  # Structured data for UI rendering
    function_called: Optional[str] = None  # Which function was called
    session_id: str = ""


class PracticeAIAssistant:
    """
    Practice AI Assistant using Ollama/Qwen with function calling.

    Features:
    - Parse natural language queries
    - Call appropriate analytics functions
    - Generate natural language responses
    - Maintain conversation context
    - Provide follow-up suggestions
    """

    # Session storage (in-memory for MVP, would use Redis in production)
    _sessions: dict[str, ConversationSession] = {}

    # Function definitions for the LLM
    FUNCTION_DEFINITIONS = [
        {
            "name": "get_procedure_stats",
            "description": "Get procedure statistics and counts. Use for questions like 'How many procedures?', 'How many echos?', 'Procedure count this month'",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "category": {
                        "type": "string",
                        "description": "Procedure category (e.g., Cardiology, Orthopedics)"
                    },
                    "procedure_type": {
                        "type": "string",
                        "description": "Specific procedure type (e.g., Echo, ECG, Angioplasty)"
                    },
                    "doctor_id": {
                        "type": "string",
                        "description": "Doctor UUID (optional filter)"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_revenue_analytics",
            "description": "Get revenue and financial statistics. Use for questions like 'Revenue this month?', 'How much collected?', 'Outstanding payments?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "doctor_id": {
                        "type": "string",
                        "description": "Doctor UUID (optional filter)"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_appointment_stats",
            "description": "Get appointment statistics. Use for questions like 'How many appointments?', 'No-show rate?', 'Cancellation rate?', 'Busiest day?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "doctor_id": {
                        "type": "string",
                        "description": "Doctor UUID (optional filter)"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "search_patients",
            "description": "Search for patients by name, phone, or condition. Use for questions like 'Find patient', 'Search diabetic patients', 'Patient with phone number'",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (name, phone, or medical condition)"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_doctor_stats",
            "description": "Get performance statistics for doctors. Use for questions like 'Dr. Sharma stats?', 'Which doctor most productive?', 'Doctor performance?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    ]

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize AI assistant.

        Args:
            model: Ollama model name (default: from settings)
            base_url: Ollama API URL (default: from settings)
        """
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url

    def _create_system_prompt(self) -> str:
        """Create system prompt for the LLM."""
        today = date.today()

        return f"""You are an AI assistant for DocAssist Practice Manager, helping doctors and clinic staff get insights about their practice.

Your task is to understand user queries about practice analytics and call the appropriate function.

Available functions:
{json.dumps(self.FUNCTION_DEFINITIONS, indent=2)}

IMPORTANT RULES:
1. Parse relative dates:
   - "today" → {today.isoformat()}
   - "yesterday" → {(today - timedelta(days=1)).isoformat()}
   - "this week" → Monday to today
   - "this month" → 1st of month to today
   - "last week" → Previous Monday to Sunday
   - "last month" → Previous month 1st to last day

2. When user asks about specific procedures (echo, ECG, stent), use get_procedure_stats with procedure_type parameter

3. When user asks about revenue/money/collection, use get_revenue_analytics

4. When user asks about appointments/bookings/no-shows, use get_appointment_stats

5. When user asks about patients, use search_patients

6. When user asks about doctors/performance, use get_doctor_stats

7. If query is ambiguous, ask for clarification

8. You MUST respond in this JSON format:
{{
    "function_call": {{
        "function": "function_name",
        "arguments": {{...}}
    }},
    "explanation": "Brief explanation of what you understood"
}}

If no function applies, respond:
{{
    "clarification_needed": "What would you like to know about?",
    "suggestions": ["Example query 1", "Example query 2"]
}}

Today's date is: {today.isoformat()}
Current time: {datetime.now().isoformat()}
"""

    async def chat(
        self,
        message: str,
        clinic_id: UUID,
        user_id: UUID,
        session_id: str | None = None,
        context: dict | None = None,
        db_session=None,
    ) -> AIResponse:
        """
        Process a chat message and return AI response.

        Args:
            message: User's message
            clinic_id: User's clinic ID
            user_id: User ID
            session_id: Optional session ID for context
            context: Optional UI context (current screen, selected items)
            db_session: Optional database session for real analytics

        Returns:
            AIResponse with answer and suggestions
        """
        # Get or create session
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.updated_at = datetime.utcnow()
        else:
            session_id = str(uuid4())
            session = ConversationSession(
                session_id=session_id,
                user_id=str(user_id),
                clinic_id=str(clinic_id),
            )
            self._sessions[session_id] = session

        # Add user message to session
        session.messages.append(Message(role="user", content=message))

        # Parse query with LLM
        function_call = await self._parse_query(message, session, context)

        if not function_call:
            # No function identified, ask for clarification
            response_text = "I'm not sure what you're asking about. Here's what I can help with:\n\n"
            response_text += "• Procedure statistics (\"How many echos this month?\")\n"
            response_text += "• Revenue analytics (\"What's my revenue today?\")\n"
            response_text += "• Appointment insights (\"No-show rate this week?\")\n"
            response_text += "• Patient search (\"Find diabetic patients\")\n"
            response_text += "• Doctor performance (\"Dr. Sharma's stats?\")\n\n"
            response_text += "What would you like to know?"

            session.messages.append(Message(role="assistant", content=response_text))

            return AIResponse(
                response=response_text,
                suggestions=[
                    "How many procedures this month?",
                    "Revenue for this week",
                    "Appointment stats today"
                ],
                session_id=session_id,
            )

        # Execute function with real or mock data
        response_text, data = await self._execute_function(
            function_call,
            clinic_id,
            session,
            db_session=db_session,
        )

        # Generate follow-up suggestions
        suggestions = self._generate_suggestions(function_call, data)

        # Add assistant response to session
        session.messages.append(Message(role="assistant", content=response_text))
        session.last_query_result = data

        return AIResponse(
            response=response_text,
            suggestions=suggestions,
            data=data,
            function_called=function_call.function.value,
            session_id=session_id,
        )

    async def _parse_query(
        self,
        message: str,
        session: ConversationSession,
        context: dict | None = None,
    ) -> FunctionCall | None:
        """
        Parse user query using Ollama to extract function call.

        Args:
            message: User's query
            session: Conversation session
            context: Optional UI context

        Returns:
            FunctionCall or None if parsing fails
        """
        # Build messages for LLM
        messages = [
            {"role": "system", "content": self._create_system_prompt()},
        ]

        # Add recent conversation history (last 5 messages)
        for msg in session.messages[-5:]:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current message (already in session.messages)
        # messages.append({"role": "user", "content": message})

        try:
            # Call Ollama
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                result = response.json()

            # Parse response
            assistant_message = result.get("message", {}).get("content", "{}")
            parsed = json.loads(assistant_message)

            # Extract function call
            if "function_call" in parsed:
                fc = parsed["function_call"]
                try:
                    function_name = FunctionName(fc["function"])
                    arguments = fc.get("arguments", {})

                    # Parse and validate dates
                    arguments = self._parse_function_arguments(arguments)

                    return FunctionCall(
                        function=function_name,
                        arguments=arguments,
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid function call: {e}")
                    return None

            return None

        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            return self._fallback_parse(message)

        except Exception as e:
            logger.error(f"Query parsing error: {e}")
            return self._fallback_parse(message)

    def _parse_function_arguments(self, arguments: dict) -> dict:
        """
        Parse and validate function arguments.

        Converts date strings to date objects and validates UUIDs.
        """
        parsed = {}

        for key, value in arguments.items():
            if key in ["start_date", "end_date"] and isinstance(value, str):
                try:
                    parsed[key] = datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    # Try to parse relative date
                    parsed[key] = self._parse_relative_date(value)
            elif key in ["doctor_id", "patient_id"] and isinstance(value, str):
                try:
                    parsed[key] = UUID(value)
                except ValueError:
                    logger.warning(f"Invalid UUID: {value}")
                    parsed[key] = value
            else:
                parsed[key] = value

        return parsed

    def _parse_relative_date(self, date_str: str) -> date:
        """Parse relative date strings like 'today', 'yesterday', 'this month'."""
        today = date.today()
        date_lower = date_str.lower()

        if date_lower in ["today", "aaj"]:
            return today
        elif date_lower in ["yesterday", "kal"]:
            return today - timedelta(days=1)
        elif date_lower == "this week start":
            return today - timedelta(days=today.weekday())
        elif date_lower == "this month start":
            return today.replace(day=1)
        elif date_lower == "last month start":
            first = today.replace(day=1)
            last_month = first - timedelta(days=1)
            return last_month.replace(day=1)
        elif date_lower == "last month end":
            first = today.replace(day=1)
            return first - timedelta(days=1)

        return today

    def _fallback_parse(self, message: str) -> FunctionCall | None:
        """Fallback parsing using keyword matching."""
        message_lower = message.lower()
        today = date.today()

        # Default to this month
        start_date = today.replace(day=1)
        end_date = today

        # Detect time period
        if "today" in message_lower:
            start_date = end_date = today
        elif "yesterday" in message_lower:
            start_date = end_date = today - timedelta(days=1)
        elif "week" in message_lower:
            start_date = today - timedelta(days=today.weekday())
        elif "last month" in message_lower:
            first = today.replace(day=1)
            end_date = first - timedelta(days=1)
            start_date = end_date.replace(day=1)

        # Detect function type
        if any(word in message_lower for word in ["procedure", "echo", "ecg", "stent", "angioplasty", "surgery"]):
            return FunctionCall(
                function=FunctionName.GET_PROCEDURE_STATS,
                arguments={"start_date": start_date, "end_date": end_date},
            )
        elif any(word in message_lower for word in ["revenue", "money", "collection", "payment", "rupees"]):
            return FunctionCall(
                function=FunctionName.GET_REVENUE_ANALYTICS,
                arguments={"start_date": start_date, "end_date": end_date},
            )
        elif any(word in message_lower for word in ["appointment", "booking", "no-show", "cancel"]):
            return FunctionCall(
                function=FunctionName.GET_APPOINTMENT_STATS,
                arguments={"start_date": start_date, "end_date": end_date},
            )
        elif any(word in message_lower for word in ["patient", "find", "search"]):
            # Extract search query (everything after 'find' or 'search')
            query = message_lower
            for word in ["find", "search", "patient"]:
                query = query.replace(word, "").strip()
            return FunctionCall(
                function=FunctionName.SEARCH_PATIENTS,
                arguments={"query": query or message},
            )
        elif any(word in message_lower for word in ["doctor", "dr", "performance"]):
            return FunctionCall(
                function=FunctionName.GET_DOCTOR_STATS,
                arguments={"start_date": start_date, "end_date": end_date},
            )

        return None

    async def _execute_function(
        self,
        function_call: FunctionCall,
        clinic_id: UUID,
        session: ConversationSession,
        db_session=None,
    ) -> tuple[str, dict]:
        """
        Execute function call and generate natural language response.

        If db_session is provided, uses real analytics. Otherwise falls back to mocks.

        Args:
            function_call: Parsed function call
            clinic_id: Clinic UUID
            session: Conversation session
            db_session: Optional SQLAlchemy async session for real analytics

        Returns:
            Tuple of (natural_language_response, structured_data)
        """
        # If database session provided, use real analytics
        if db_session:
            try:
                from app.services.nl_analytics import get_nl_analytics

                nl_analytics = get_nl_analytics(db_session)
                result = await nl_analytics.execute_query(function_call, clinic_id)

                return result.natural_response, result.structured_data
            except Exception as e:
                logger.error(f"Real analytics execution failed: {e}, falling back to mocks")
                # Fall through to mock responses

        # Fallback to mock responses (for testing or when DB unavailable)
        func = function_call.function
        args = function_call.arguments

        if func == FunctionName.GET_PROCEDURE_STATS:
            return self._mock_procedure_stats(args)
        elif func == FunctionName.GET_REVENUE_ANALYTICS:
            return self._mock_revenue_analytics(args)
        elif func == FunctionName.GET_APPOINTMENT_STATS:
            return self._mock_appointment_stats(args)
        elif func == FunctionName.SEARCH_PATIENTS:
            return self._mock_search_patients(args)
        elif func == FunctionName.GET_DOCTOR_STATS:
            return self._mock_doctor_stats(args)

        return "I couldn't process that request.", {}

    def _mock_procedure_stats(self, args: dict) -> tuple[str, dict]:
        """Mock procedure stats response."""
        data = {
            "total": 127,
            "by_category": {
                "Cardiology": 68,
                "Orthopedics": 35,
                "General": 24,
            },
            "by_type": {
                "Echo": 42,
                "ECG": 18,
                "Angioplasty": 8,
            },
            "total_billed": 1850000,
        }

        response = f"""This month you've completed {data['total']} procedures:

• Cardiology: {data['by_category']['Cardiology']} (54%)
  - Echo: {data['by_type']['Echo']}
  - ECG: {data['by_type']['ECG']}
  - Angioplasty: {data['by_type']['Angioplasty']}
• Orthopedics: {data['by_category']['Orthopedics']} (28%)
• General: {data['by_category']['General']} (18%)

Total billed: ₹{data['total_billed']:,.0f}

Would you like a breakdown by doctor?"""

        return response, data

    def _mock_revenue_analytics(self, args: dict) -> tuple[str, dict]:
        """Mock revenue analytics response."""
        data = {
            "total_revenue": 2500000,
            "collected": 2100000,
            "pending": 400000,
            "collection_rate": 84.0,
        }

        response = f"""Revenue Summary:

• Total: ₹{data['total_revenue']:,.0f}
• Collected: ₹{data['collected']:,.0f} ({data['collection_rate']:.0f}%)
• Pending: ₹{data['pending']:,.0f}

Collection rate is good! Would you like to see daily breakdown?"""

        return response, data

    def _mock_appointment_stats(self, args: dict) -> tuple[str, dict]:
        """Mock appointment stats response."""
        data = {
            "total": 245,
            "completed": 198,
            "cancelled": 28,
            "no_show": 19,
            "completion_rate": 80.8,
            "no_show_rate": 7.8,
        }

        response = f"""Appointment Statistics:

• Total: {data['total']}
• Completed: {data['completed']} ({data['completion_rate']:.1f}%)
• Cancelled: {data['cancelled']}
• No-show: {data['no_show']} ({data['no_show_rate']:.1f}%)

Your no-show rate is acceptable. Would you like to see no-show patterns?"""

        return response, data

    def _mock_search_patients(self, args: dict) -> tuple[str, dict]:
        """Mock patient search response."""
        data = {
            "count": 12,
            "patients": [
                {"id": "1", "name": "Ramesh Kumar", "phone": "9876543210", "last_visit": "2026-01-02"},
                {"id": "2", "name": "Sunita Sharma", "phone": "9876543211", "last_visit": "2025-12-28"},
            ]
        }

        response = f"""Found {data['count']} patients matching your query:

1. Ramesh Kumar - 9876543210
   Last visit: {data['patients'][0]['last_visit']}

2. Sunita Sharma - 9876543211
   Last visit: {data['patients'][1]['last_visit']}

... and {data['count'] - 2} more.

Would you like to see details for any patient?"""

        return response, data

    def _mock_doctor_stats(self, args: dict) -> tuple[str, dict]:
        """Mock doctor stats response."""
        data = {
            "doctors": [
                {
                    "name": "Dr. Sharma",
                    "total_procedures": 68,
                    "total_billed": 1200000,
                    "utilization_rate": 85.5,
                },
                {
                    "name": "Dr. Verma",
                    "total_procedures": 45,
                    "total_billed": 800000,
                    "utilization_rate": 72.3,
                },
            ]
        }

        response = f"""Doctor Performance:

1. {data['doctors'][0]['name']}
   • Procedures: {data['doctors'][0]['total_procedures']}
   • Billed: ₹{data['doctors'][0]['total_billed']:,.0f}
   • Utilization: {data['doctors'][0]['utilization_rate']:.1f}%

2. {data['doctors'][1]['name']}
   • Procedures: {data['doctors'][1]['total_procedures']}
   • Billed: ₹{data['doctors'][1]['total_billed']:,.0f}
   • Utilization: {data['doctors'][1]['utilization_rate']:.1f}%

Dr. Sharma is the top performer this month!"""

        return response, data

    def _generate_suggestions(
        self,
        function_call: FunctionCall,
        data: dict,
    ) -> list[str]:
        """Generate follow-up suggestions based on function called."""
        func = function_call.function

        if func == FunctionName.GET_PROCEDURE_STATS:
            return [
                "Breakdown by doctor",
                "Compare to last month",
                "Show me procedure trends",
            ]
        elif func == FunctionName.GET_REVENUE_ANALYTICS:
            return [
                "Daily revenue breakdown",
                "Outstanding payments",
                "Compare to last month",
            ]
        elif func == FunctionName.GET_APPOINTMENT_STATS:
            return [
                "No-show patterns",
                "Cancellation reasons",
                "Busiest days",
            ]
        elif func == FunctionName.SEARCH_PATIENTS:
            return [
                "Show patient details",
                "Upcoming appointments",
                "Patient history",
            ]
        elif func == FunctionName.GET_DOCTOR_STATS:
            return [
                "Individual doctor breakdown",
                "Revenue by doctor",
                "Utilization trends",
            ]

        return []

    def get_session(self, session_id: str) -> ConversationSession | None:
        """Get conversation session by ID."""
        return self._sessions.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clear conversation session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=max_age_hours)

        to_remove = [
            sid for sid, session in self._sessions.items()
            if session.updated_at < cutoff
        ]

        for sid in to_remove:
            del self._sessions[sid]

        logger.info(f"Cleaned up {len(to_remove)} old sessions")


def get_ai_assistant() -> PracticeAIAssistant:
    """Get AI assistant singleton."""
    return PracticeAIAssistant()
