"""
Voice bot for phone-based appointment booking.

Phase 18: Voice Bot / Phone Automation

Uses:
- faster-whisper for STT (already integrated)
- Chatterbox for TTS (already integrated, 23 Indian languages)
- Qwen2.5 via Ollama for NLU (already integrated)
- Entity Extractor (already integrated)
- Action Executor (already integrated)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.services.ai_action_executor import AIActionExecutor, ActionType
from app.services.ai_entity_extractor import EntityExtractor
from app.voice.stt import SpeechToTextAsync
from app.voice.tts import TextToSpeechAsync

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Voice bot conversation state."""

    call_id: UUID
    clinic_id: UUID
    language: str = "hi"  # Default Hindi
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_id: Optional[UUID] = None
    intent: Optional[str] = None
    extracted_date: Optional[str] = None
    extracted_time: Optional[str] = None
    extracted_doctor: Optional[str] = None
    awaiting_confirmation: bool = False
    confirmation_context: dict = field(default_factory=dict)
    conversation_history: list[dict] = field(default_factory=list)


class AppointmentBookingBot:
    """Voice bot for appointment booking via phone."""

    # Multilingual greetings
    GREETINGS = {
        "hi": "नमस्ते! DocAssist में आपका स्वागत है। मैं आपकी अपॉइंटमेंट बुक करने में मदद कर सकती हूं। कृपया अपना नाम बताएं।",
        "en": "Hello! Welcome to DocAssist. I can help you book an appointment. Please tell me your name.",
        "ta": "வணக்கம்! DocAssist க்கு வரவேற்கிறோம். நான் உங்கள் சந்திப்பை முன்பதிவு செய்ய உதவ முடியும். உங்கள் பெயரை சொல்லுங்கள்.",
        "te": "నమస్కారం! DocAssist కు స్వాగతం. నేను మీ అపాయింట్‌మెంట్ బుక్ చేయడానికి సహాయం చేయగలను. దయచేసి మీ పేరు చెప్పండి.",
        "bn": "নমস্কার! DocAssist এ আপনাকে স্বাগতম। আমি আপনার অ্যাপয়েন্টমেন্ট বুক করতে সাহায্য করতে পারি। দয়া করে আপনার নাম বলুন।",
        "mr": "नमस्कार! DocAssist मध्ये आपले स्वागत आहे. मी तुमची भेट बुक करण्यास मदत करू शकते. कृपया तुमचे नाव सांगा.",
    }

    PERSONALIZED_GREETINGS = {
        "hi": "नमस्ते {name} जी! DocAssist में आपका स्वागत है। क्या आप अपॉइंटमेंट बुक करना चाहते हैं?",
        "en": "Hello {name}! Welcome to DocAssist. Would you like to book an appointment?",
        "ta": "வணக்கம் {name}! DocAssist க்கு வரவேற்கிறோம். சந்திப்பை முன்பதிவு செய்ய விரும்புகிறீர்களா?",
    }

    PROMPTS = {
        "ask_name": {
            "hi": "कृपया अपना नाम बताएं।",
            "en": "Please tell me your name.",
        },
        "ask_date": {
            "hi": "किस दिन अपॉइंटमेंट चाहिए?",
            "en": "Which day would you like the appointment?",
        },
        "ask_time": {
            "hi": "किस समय अपॉइंटमेंट चाहिए?",
            "en": "What time would you like?",
        },
        "confirm_booking": {
            "hi": "{name} जी, आपकी अपॉइंटमेंट {date} को {time} बजे बुक करूं? कृपया हाँ या ना कहें।",
            "en": "Should I book appointment for {name} on {date} at {time}? Please say yes or no.",
        },
        "booking_success": {
            "hi": "बहुत बढ़िया! आपकी अपॉइंटमेंट बुक हो गई है। आपको SMS पर confirmation मिल जाएगा। धन्यवाद!",
            "en": "Great! Your appointment is booked. You'll receive an SMS confirmation. Thank you!",
        },
        "booking_failed": {
            "hi": "माफ़ कीजिए, यह समय उपलब्ध नहीं है। क्या कोई और समय बताएं?",
            "en": "Sorry, that slot is not available. Would you like to try another time?",
        },
        "booking_cancelled": {
            "hi": "ठीक है, कोई बात नहीं। क्या कोई और समय बताएं या कॉल समाप्त करें?",
            "en": "Okay, no problem. Would you like to try another time or end the call?",
        },
        "not_understood": {
            "hi": "मुझे समझ नहीं आया। कृपया दोबारा बताएं।",
            "en": "I didn't understand. Please try again.",
        },
        "goodbye": {
            "hi": "धन्यवाद! अपना ख्याल रखें।",
            "en": "Thank you! Take care.",
        },
    }

    def __init__(self, db: Session, clinic_id: UUID):
        """
        Initialize appointment booking bot.

        Args:
            db: Database session
            clinic_id: Clinic ID
        """
        self.db = db
        self.clinic_id = clinic_id
        self.stt = SpeechToTextAsync()
        self.tts = TextToSpeechAsync()
        self.action_executor = AIActionExecutor(db)
        self.entity_extractor = EntityExtractor(db)
        self.state = ConversationState(call_id=None, clinic_id=clinic_id)

    async def handle_call_start(
        self,
        call_sid: str,
        from_number: str,
        call_id: UUID,
    ) -> str:
        """
        Handle incoming call - return greeting.

        Args:
            call_sid: Twilio call SID
            from_number: Caller's phone number
            call_id: Phone call record ID

        Returns:
            Greeting message
        """
        self.state.call_id = call_id
        self.state.patient_phone = from_number

        # Try to identify patient by phone number
        patient = await self._lookup_patient_by_phone(from_number)

        if patient:
            self.state.patient_id = patient.id
            self.state.patient_name = patient.full_name

            # Personalized greeting
            template = self.PERSONALIZED_GREETINGS.get(
                self.state.language,
                self.PERSONALIZED_GREETINGS["en"],
            )
            return template.format(name=patient.first_name)

        # Default greeting
        return self.GREETINGS.get(self.state.language, self.GREETINGS["en"])

    async def process_speech(self, text: str) -> str:
        """
        Process user speech and return response.

        Args:
            text: Transcribed speech text

        Returns:
            Response message
        """
        # Add to conversation history
        self.state.conversation_history.append({
            "speaker": "caller",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Detect language
        lang = self._detect_language(text)
        if lang:
            self.state.language = lang

        # Extract entities
        entities = await self._extract_entities(text)

        # Update state with extracted entities
        if entities.get("patient_name"):
            self.state.patient_name = entities["patient_name"]
        if entities.get("date"):
            self.state.extracted_date = entities["date"]
        if entities.get("time"):
            self.state.extracted_time = entities["time"]

        # Determine intent and respond
        intent = self._detect_intent(text)
        self.state.intent = intent

        if intent == "book_appointment":
            response = await self._handle_booking_intent(text)
        elif intent == "check_availability":
            response = await self._handle_availability_intent(text)
        elif intent == "cancel_appointment":
            response = await self._handle_cancel_intent(text)
        elif intent == "confirm":
            response = await self._handle_confirmation(True)
        elif intent == "deny":
            response = await self._handle_confirmation(False)
        elif intent == "goodbye":
            response = self._get_prompt("goodbye")
        else:
            response = await self._handle_general_query(text)

        # Add to conversation history
        self.state.conversation_history.append({
            "speaker": "bot",
            "text": response,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return response

    async def _handle_booking_intent(self, text: str) -> str:
        """Handle appointment booking intent."""
        # Check what info we have
        missing = []

        if not self.state.patient_name:
            missing.append("name")
        if not self.state.extracted_date:
            missing.append("date")
        if not self.state.extracted_time:
            missing.append("time")

        # If missing info, ask for it
        if missing:
            return self._get_prompt(f"ask_{missing[0]}")

        # We have all info - prepare confirmation
        self.state.awaiting_confirmation = True
        self.state.confirmation_context = {
            "action": "book_appointment",
            "patient_name": self.state.patient_name,
            "date": self.state.extracted_date,
            "time": self.state.extracted_time,
        }

        template = self.PROMPTS["confirm_booking"][self.state.language]
        return template.format(
            name=self.state.patient_name,
            date=self.state.extracted_date,
            time=self.state.extracted_time,
        )

    async def _handle_confirmation(self, confirmed: bool) -> str:
        """Handle booking confirmation."""
        if not self.state.awaiting_confirmation:
            return self._get_prompt("not_understood")

        self.state.awaiting_confirmation = False

        if confirmed:
            # Book the appointment
            result = await self._book_appointment()

            if result["success"]:
                return self._get_prompt("booking_success")
            else:
                return self._get_prompt("booking_failed")
        else:
            return self._get_prompt("booking_cancelled")

    async def _handle_availability_intent(self, text: str) -> str:
        """Handle availability check intent."""
        # TODO: Implement availability check
        if self.state.language == "hi":
            return "उपलब्धता जांचने के लिए कृपया दिन और समय बताएं।"
        return "To check availability, please tell me the date and time."

    async def _handle_cancel_intent(self, text: str) -> str:
        """Handle appointment cancellation intent."""
        # TODO: Implement cancellation
        if self.state.language == "hi":
            return "अपॉइंटमेंट रद्द करने के लिए कृपया अपना नाम और अपॉइंटमेंट की तारीख बताएं।"
        return "To cancel an appointment, please tell me your name and appointment date."

    async def _handle_general_query(self, text: str) -> str:
        """Handle general queries."""
        return self._get_prompt("not_understood")

    async def _book_appointment(self) -> dict:
        """Actually book the appointment."""
        try:
            # Get or create patient
            if not self.state.patient_id:
                patient = await self._create_patient()
                if patient:
                    self.state.patient_id = patient.id
                else:
                    return {"success": False, "error": "Failed to create patient"}

            # Parse date/time using entity extractor
            date = await self.entity_extractor.extract_date(
                self.state.extracted_date,
                self.state.clinic_id,
            )
            time = await self.entity_extractor.extract_time(
                self.state.extracted_time,
                self.state.clinic_id,
            )

            if not date or not time:
                return {"success": False, "error": "Invalid date or time"}

            # Book via action executor
            result = await self.action_executor.execute_action(
                action_type=ActionType.BOOK_APPOINTMENT,
                params={
                    "patient_id": str(self.state.patient_id),
                    "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
                    "time": time.isoformat() if hasattr(time, "isoformat") else str(time),
                    "clinic_id": str(self.state.clinic_id),
                },
                user_id=None,  # System booking
                clinic_id=self.state.clinic_id,
            )

            return {
                "success": result.success,
                "appointment_id": result.data.get("appointment_id") if result.data else None,
            }

        except Exception as e:
            logger.error(f"Error booking appointment: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _create_patient(self) -> Optional[Patient]:
        """Create new patient record."""
        try:
            # Parse name
            name_parts = self.state.patient_name.split()
            first_name = name_parts[0] if name_parts else "Unknown"
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            patient = Patient(
                first_name=first_name,
                last_name=last_name,
                phone=self.state.patient_phone,
                clinic_id=self.state.clinic_id,
            )
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)

            logger.info(f"Created patient: {patient.id} - {patient.full_name}")
            return patient

        except Exception as e:
            logger.error(f"Error creating patient: {e}", exc_info=True)
            self.db.rollback()
            return None

    async def _lookup_patient_by_phone(self, phone: str) -> Optional[Patient]:
        """Lookup patient by phone number."""
        try:
            # Clean phone number
            phone_digits = "".join(filter(str.isdigit, phone))
            if len(phone_digits) >= 10:
                phone_digits = phone_digits[-10:]  # Last 10 digits

            patient = (
                self.db.query(Patient)
                .filter(
                    Patient.phone.contains(phone_digits),
                    Patient.clinic_id == self.state.clinic_id,
                )
                .first()
            )

            return patient

        except Exception as e:
            logger.error(f"Error looking up patient: {e}", exc_info=True)
            return None

    async def _extract_entities(self, text: str) -> dict:
        """Extract entities from text."""
        entities = {}

        try:
            # Extract patient name (if not already known)
            if not self.state.patient_id:
                patient = await self.entity_extractor.extract_patient(
                    text,
                    self.state.clinic_id,
                )
                if patient:
                    entities["patient_name"] = patient.full_name

            # Extract date
            date = await self.entity_extractor.extract_date(text, self.state.clinic_id)
            if date:
                entities["date"] = str(date)

            # Extract time
            time = await self.entity_extractor.extract_time(text, self.state.clinic_id)
            if time:
                entities["time"] = str(time)

        except Exception as e:
            logger.error(f"Error extracting entities: {e}", exc_info=True)

        return entities

    def _detect_intent(self, text: str) -> str:
        """Detect user intent from speech."""
        text_lower = text.lower()

        # Hindi + English intent detection
        if any(
            word in text_lower
            for word in [
                "book",
                "appointment",
                "बुक",
                "अपॉइंटमेंट",
                "चाहिए",
                "मिलना",
                "देखना",
            ]
        ):
            return "book_appointment"
        elif any(
            word in text_lower
            for word in ["available", "slot", "खाली", "उपलब्ध", "मिलेगा"]
        ):
            return "check_availability"
        elif any(word in text_lower for word in ["cancel", "रद्द", "कैंसल"]):
            return "cancel_appointment"
        elif any(
            word in text_lower
            for word in ["yes", "हाँ", "हां", "ठीक", "okay", "confirm", "जी"]
        ):
            return "confirm"
        elif any(word in text_lower for word in ["no", "नहीं", "ना", "नही"]):
            return "deny"
        elif any(
            word in text_lower for word in ["bye", "goodbye", "धन्यवाद", "thank"]
        ):
            return "goodbye"

        return "general"

    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language from text."""
        # Check for Devanagari script (Hindi, Marathi)
        devanagari_chars = set("अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसहा")
        if any(char in devanagari_chars for char in text):
            return "hi"

        # Check for Tamil script
        tamil_chars = set("அஆஇஈஉஊஎஏஐஒஓஔகஙசஞடணதநபமயரலவழளறனஜஷஸஹ")
        if any(char in tamil_chars for char in text):
            return "ta"

        # Check for Telugu script
        telugu_chars = set("అఆఇఈఉఊఎఏఐఒఓఔకఖగఘఙచఛజఝఞటఠడఢణతథదధనపఫబభమయరలవశషసహళ")
        if any(char in telugu_chars for char in text):
            return "te"

        # Default to English
        return "en"

    def _get_prompt(self, prompt_key: str) -> str:
        """Get prompt in current language."""
        if prompt_key in self.PROMPTS:
            return self.PROMPTS[prompt_key].get(
                self.state.language,
                self.PROMPTS[prompt_key]["en"],
            )
        return self.PROMPTS["not_understood"][self.state.language]

    def get_full_transcript(self) -> str:
        """Get full conversation transcript."""
        transcript_lines = []
        for entry in self.state.conversation_history:
            speaker = entry["speaker"].upper()
            text = entry["text"]
            transcript_lines.append(f"{speaker}: {text}")
        return "\n".join(transcript_lines)
