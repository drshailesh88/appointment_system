"""
Natural Language Understanding using Ollama/Qwen.

Extracts intent and entities from user speech for appointment booking.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """User intents for appointment booking."""

    BOOK_APPOINTMENT = "book_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CHECK_AVAILABILITY = "check_availability"
    GET_APPOINTMENT_STATUS = "get_appointment_status"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    HELP = "help"
    CONFIRM = "confirm"
    DENY = "deny"
    UNKNOWN = "unknown"


@dataclass
class ExtractedEntities:
    """Entities extracted from user input."""

    doctor_name: Optional[str] = None
    specialization: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    appointment_type: Optional[str] = None
    reason: Optional[str] = None
    raw_entities: dict = field(default_factory=dict)


@dataclass
class NLUResult:
    """Result from NLU processing."""

    intent: Intent
    confidence: float
    entities: ExtractedEntities
    raw_text: str
    response_suggestion: Optional[str] = None


class NaturalLanguageUnderstanding:
    """
    NLU engine using Ollama with Qwen model.

    Handles:
    - Intent classification
    - Entity extraction (doctor, date, time, patient info)
    - Context management for multi-turn conversations
    """

    def __init__(
        self,
        model: str = None,
        base_url: str = None,
    ):
        """
        Initialize NLU engine.

        Args:
            model: Ollama model name
            base_url: Ollama API base URL
        """
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url
        self.conversation_context: list[dict] = []

    def _create_system_prompt(self) -> str:
        """Create system prompt for the LLM."""
        return """You are a helpful assistant for a medical clinic appointment booking system in India.
Your task is to understand user requests and extract relevant information.

You must respond in JSON format with the following structure:
{
    "intent": "one of: book_appointment, cancel_appointment, reschedule_appointment, check_availability, get_appointment_status, greeting, goodbye, help, confirm, deny, unknown",
    "confidence": 0.0 to 1.0,
    "entities": {
        "doctor_name": "extracted doctor name or null",
        "specialization": "medical specialization or null",
        "date": "YYYY-MM-DD format or null",
        "time": "HH:MM format (24-hour) or null",
        "patient_name": "patient name or null",
        "patient_phone": "phone number or null",
        "appointment_type": "new_consultation, follow_up, or null",
        "reason": "reason for visit or null"
    },
    "response_suggestion": "A helpful response to say to the user"
}

Important rules:
1. Parse relative dates like "tomorrow", "next Monday", "day after tomorrow"
2. Parse relative times like "morning", "afternoon", "evening", "3 PM"
3. Handle Indian names and phone numbers (10 digits, may start with +91)
4. Be polite and helpful in response suggestions
5. If unsure, ask for clarification in the response_suggestion

Today's date is: """ + date.today().isoformat()

    async def process(
        self,
        text: str,
        context: Optional[list[dict]] = None,
    ) -> NLUResult:
        """
        Process user input and extract intent/entities.

        Args:
            text: User's spoken/typed text
            context: Optional conversation context

        Returns:
            NLUResult with intent, entities, and suggested response
        """
        if context:
            self.conversation_context = context

        # Build messages
        messages = [
            {"role": "system", "content": self._create_system_prompt()},
        ]

        # Add conversation context
        for ctx in self.conversation_context[-5:]:  # Last 5 turns
            messages.append(ctx)

        # Add current user message
        messages.append({"role": "user", "content": text})

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
            parsed = self._parse_llm_response(assistant_message)

            # Update context
            self.conversation_context.append({"role": "user", "content": text})
            self.conversation_context.append({"role": "assistant", "content": assistant_message})

            return NLUResult(
                intent=parsed["intent"],
                confidence=parsed["confidence"],
                entities=parsed["entities"],
                raw_text=text,
                response_suggestion=parsed.get("response_suggestion"),
            )

        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            return self._fallback_parse(text)

        except Exception as e:
            logger.error(f"NLU processing error: {e}")
            return self._fallback_parse(text)

    def _parse_llm_response(self, response: str) -> dict:
        """Parse the LLM's JSON response."""
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return self._default_response()
            else:
                return self._default_response()

        # Parse intent
        intent_str = data.get("intent", "unknown").lower()
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        # Parse entities
        entities_data = data.get("entities", {})
        entities = ExtractedEntities(
            doctor_name=entities_data.get("doctor_name"),
            specialization=entities_data.get("specialization"),
            date=self._parse_date(entities_data.get("date")),
            time=self._parse_time(entities_data.get("time")),
            patient_name=entities_data.get("patient_name"),
            patient_phone=entities_data.get("patient_phone"),
            appointment_type=entities_data.get("appointment_type"),
            reason=entities_data.get("reason"),
            raw_entities=entities_data,
        )

        return {
            "intent": intent,
            "confidence": float(data.get("confidence", 0.5)),
            "entities": entities,
            "response_suggestion": data.get("response_suggestion"),
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        # Handle relative dates
        today = date.today()
        date_lower = date_str.lower()

        if date_lower in ["today", "aaj"]:
            return today
        elif date_lower in ["tomorrow", "kal", "next day"]:
            return today + timedelta(days=1)
        elif date_lower in ["day after tomorrow", "parson"]:
            return today + timedelta(days=2)

        # Handle day names
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            if day in date_lower:
                days_ahead = i - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)

        return None

    def _parse_time(self, time_str: Optional[str]) -> Optional[time]:
        """Parse time string to time object."""
        if not time_str:
            return None

        # Try standard format
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            pass

        # Handle 12-hour format
        try:
            return datetime.strptime(time_str.upper(), "%I:%M %p").time()
        except ValueError:
            pass

        try:
            return datetime.strptime(time_str.upper(), "%I %p").time()
        except ValueError:
            pass

        # Handle relative times
        time_lower = time_str.lower()

        if "morning" in time_lower or "subah" in time_lower:
            return time(9, 0)
        elif "afternoon" in time_lower or "dopahar" in time_lower:
            return time(14, 0)
        elif "evening" in time_lower or "shaam" in time_lower:
            return time(17, 0)

        return None

    def _default_response(self) -> dict:
        """Return default response when parsing fails."""
        return {
            "intent": Intent.UNKNOWN,
            "confidence": 0.0,
            "entities": ExtractedEntities(),
            "response_suggestion": "I'm sorry, I didn't understand that. Could you please repeat?",
        }

    def _fallback_parse(self, text: str) -> NLUResult:
        """Fallback parsing using simple keyword matching."""
        text_lower = text.lower()

        # Simple intent detection
        if any(word in text_lower for word in ["book", "schedule", "appointment", "doctor"]):
            intent = Intent.BOOK_APPOINTMENT
        elif any(word in text_lower for word in ["cancel", "remove"]):
            intent = Intent.CANCEL_APPOINTMENT
        elif any(word in text_lower for word in ["reschedule", "change", "move"]):
            intent = Intent.RESCHEDULE_APPOINTMENT
        elif any(word in text_lower for word in ["available", "slot", "when"]):
            intent = Intent.CHECK_AVAILABILITY
        elif any(word in text_lower for word in ["hello", "hi", "namaste"]):
            intent = Intent.GREETING
        elif any(word in text_lower for word in ["bye", "goodbye", "thanks"]):
            intent = Intent.GOODBYE
        elif any(word in text_lower for word in ["yes", "ok", "confirm", "haan"]):
            intent = Intent.CONFIRM
        elif any(word in text_lower for word in ["no", "cancel", "nahi"]):
            intent = Intent.DENY
        else:
            intent = Intent.UNKNOWN

        return NLUResult(
            intent=intent,
            confidence=0.6,
            entities=ExtractedEntities(),
            raw_text=text,
            response_suggestion="I understood your request. Let me help you with that.",
        )

    def reset_context(self):
        """Reset conversation context."""
        self.conversation_context = []


class NLUSync:
    """Synchronous wrapper for NLU."""

    def __init__(self, model: str = None, base_url: str = None):
        self.nlu = NaturalLanguageUnderstanding(model, base_url)

    def process(self, text: str, context: Optional[list[dict]] = None) -> NLUResult:
        """Synchronous process (uses asyncio.run)."""
        import asyncio
        return asyncio.run(self.nlu.process(text, context))
