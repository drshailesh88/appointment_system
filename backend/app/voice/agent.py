"""
Voice Agent - Orchestrates STT, NLU, and TTS for voice-based appointment booking.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, BookingSource
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.voice.nlu import Intent, NaturalLanguageUnderstanding, NLUResult
from app.voice.stt import SpeechToTextAsync
from app.voice.tts import TextToSpeechAsync, VOICE_RESPONSES

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """States in the booking conversation flow."""

    IDLE = "idle"
    GREETING = "greeting"
    COLLECTING_DOCTOR = "collecting_doctor"
    COLLECTING_DATE = "collecting_date"
    COLLECTING_TIME = "collecting_time"
    COLLECTING_PATIENT = "collecting_patient"
    COLLECTING_REASON = "collecting_reason"
    CONFIRMING = "confirming"
    BOOKING = "booking"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class BookingContext:
    """Context for an ongoing booking conversation."""

    session_id: str
    clinic_id: UUID
    state: ConversationState = ConversationState.IDLE
    doctor_id: Optional[UUID] = None
    doctor_name: Optional[str] = None
    patient_id: Optional[UUID] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    reason: Optional[str] = None
    appointment_type: str = "new_consultation"
    language: str = "en"
    conversation_history: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VoiceResponse:
    """Response from the voice agent."""

    text: str
    audio: Optional[bytes] = None
    state: ConversationState = ConversationState.IDLE
    booking_complete: bool = False
    appointment_id: Optional[UUID] = None
    next_action: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class VoiceAgent:
    """
    Voice-based appointment booking agent.

    Handles the complete flow:
    1. Listen to user speech (STT)
    2. Understand intent and extract entities (NLU)
    3. Execute booking logic
    4. Respond with voice (TTS)
    """

    def __init__(
        self,
        stt_model: str = "base.en",
        tts_voice: str = "en_IN",
        nlu_model: str = None,
    ):
        """
        Initialize Voice Agent.

        Args:
            stt_model: Whisper model for STT
            tts_voice: Voice for TTS
            nlu_model: Ollama model for NLU
        """
        self.stt = SpeechToTextAsync(stt_model)
        self.tts = TextToSpeechAsync(tts_voice)
        self.nlu = NaturalLanguageUnderstanding(nlu_model)

        # Active booking sessions
        self.sessions: dict[str, BookingContext] = {}

    async def process_audio(
        self,
        audio_data: bytes,
        session_id: str,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> VoiceResponse:
        """
        Process audio input and return voice response.

        Args:
            audio_data: Audio bytes from user
            session_id: Unique session identifier
            clinic_id: Clinic context
            db: Database session

        Returns:
            VoiceResponse with text and audio
        """
        # Get or create session context
        context = self.sessions.get(session_id)
        if not context:
            context = BookingContext(session_id=session_id, clinic_id=clinic_id)
            self.sessions[session_id] = context

        context.last_activity = datetime.now(timezone.utc)

        try:
            # Step 1: Speech to Text
            transcription = await self.stt.transcribe(audio_data)
            user_text = transcription["text"]
            logger.info(f"Transcribed: {user_text}")

            if not user_text.strip():
                return await self._respond(
                    "I didn't catch that. Could you please repeat?",
                    context,
                )

            # Step 2: Process text
            return await self.process_text(user_text, session_id, clinic_id, db)

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            context.state = ConversationState.ERROR
            return await self._respond(
                "I'm sorry, I encountered an error. Please try again.",
                context,
            )

    async def process_text(
        self,
        text: str,
        session_id: str,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> VoiceResponse:
        """
        Process text input (for testing or text-based interaction).
        """
        context = self.sessions.get(session_id)
        if not context:
            context = BookingContext(session_id=session_id, clinic_id=clinic_id)
            self.sessions[session_id] = context

        context.last_activity = datetime.now(timezone.utc)

        # Add to conversation history
        context.conversation_history.append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            # Step 1: NLU - Understand intent and extract entities
            nlu_result = await self.nlu.process(
                text,
                context.conversation_history,
            )
            logger.info(f"Intent: {nlu_result.intent}, Entities: {nlu_result.entities}")

            # Step 2: Update context with extracted entities
            self._update_context_from_entities(context, nlu_result)

            # Step 3: Handle based on current state and intent
            response = await self._handle_state(context, nlu_result, db)

            # Add response to history
            context.conversation_history.append({
                "role": "assistant",
                "content": response.text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return response

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            context.state = ConversationState.ERROR
            return await self._respond(
                "I apologize, something went wrong. Let me start over. How can I help you?",
                context,
            )

    def _update_context_from_entities(
        self,
        context: BookingContext,
        nlu_result: NLUResult,
    ):
        """Update booking context with extracted entities."""
        entities = nlu_result.entities

        if entities.doctor_name:
            context.doctor_name = entities.doctor_name
        if entities.date:
            context.appointment_date = entities.date
        if entities.time:
            context.appointment_time = entities.time
        if entities.patient_name:
            context.patient_name = entities.patient_name
        if entities.patient_phone:
            context.patient_phone = entities.patient_phone
        if entities.reason:
            context.reason = entities.reason
        if entities.appointment_type:
            context.appointment_type = entities.appointment_type

    async def _handle_state(
        self,
        context: BookingContext,
        nlu_result: NLUResult,
        db: AsyncSession,
    ) -> VoiceResponse:
        """Handle conversation based on current state."""

        # Handle special intents regardless of state
        if nlu_result.intent == Intent.GREETING:
            context.state = ConversationState.GREETING
            return await self._respond(
                VOICE_RESPONSES["greeting"]["en"],
                context,
                next_action="ask_doctor",
            )

        if nlu_result.intent == Intent.GOODBYE:
            context.state = ConversationState.COMPLETED
            self._cleanup_session(context.session_id)
            return await self._respond(
                VOICE_RESPONSES["goodbye"]["en"],
                context,
            )

        if nlu_result.intent == Intent.DENY:
            if context.state == ConversationState.CONFIRMING:
                context.state = ConversationState.CANCELLED
                return await self._respond(
                    "No problem. Is there anything else I can help you with?",
                    context,
                )

        if nlu_result.intent == Intent.BOOK_APPOINTMENT or context.state == ConversationState.GREETING:
            return await self._handle_booking_flow(context, nlu_result, db)

        if nlu_result.intent == Intent.CHECK_AVAILABILITY:
            return await self._handle_availability_check(context, nlu_result, db)

        if nlu_result.intent == Intent.CONFIRM:
            if context.state == ConversationState.CONFIRMING:
                return await self._complete_booking(context, db)

        # Default: try to continue booking flow
        if context.state not in [ConversationState.IDLE, ConversationState.COMPLETED]:
            return await self._handle_booking_flow(context, nlu_result, db)

        # Unknown - ask for clarification
        return await self._respond(
            nlu_result.response_suggestion or "How can I help you today? Would you like to book an appointment?",
            context,
        )

    async def _handle_booking_flow(
        self,
        context: BookingContext,
        nlu_result: NLUResult,
        db: AsyncSession,
    ) -> VoiceResponse:
        """Handle the appointment booking flow."""

        # Check what information we still need
        if not context.doctor_id and not context.doctor_name:
            context.state = ConversationState.COLLECTING_DOCTOR

            # Get available doctors
            doctors = await self._get_doctors(context.clinic_id, db)
            doctor_names = [d.name for d in doctors]

            return await self._respond(
                f"Which doctor would you like to see? We have {', '.join(doctor_names)}.",
                context,
                metadata={"doctors": [{"id": str(d.id), "name": d.name} for d in doctors]},
            )

        # Resolve doctor name to ID
        if context.doctor_name and not context.doctor_id:
            doctor = await self._find_doctor(context.clinic_id, context.doctor_name, db)
            if doctor:
                context.doctor_id = doctor.id
                context.doctor_name = doctor.name
            else:
                return await self._respond(
                    f"I couldn't find a doctor named {context.doctor_name}. Could you please try again?",
                    context,
                )

        if not context.appointment_date:
            context.state = ConversationState.COLLECTING_DATE
            return await self._respond(
                VOICE_RESPONSES["ask_date"]["en"],
                context,
            )

        if not context.appointment_time:
            context.state = ConversationState.COLLECTING_TIME

            # Get available slots
            slots = await self._get_available_slots(
                context.doctor_id,
                context.appointment_date,
                db,
            )

            if not slots:
                return await self._respond(
                    f"I'm sorry, there are no available slots on {context.appointment_date}. Would you like to try another date?",
                    context,
                )

            slot_times = [s.strftime("%I:%M %p") for s in slots[:5]]
            return await self._respond(
                f"Available times are: {', '.join(slot_times)}. Which time works for you?",
                context,
                metadata={"available_slots": [s.isoformat() for s in slots]},
            )

        if not context.patient_phone:
            context.state = ConversationState.COLLECTING_PATIENT
            return await self._respond(
                "May I have the patient's phone number please?",
                context,
            )

        # Resolve patient
        if context.patient_phone and not context.patient_id:
            patient = await self._find_patient(context.clinic_id, context.patient_phone, db)
            if patient:
                context.patient_id = patient.id
                context.patient_name = patient.full_name
            else:
                # Patient doesn't exist - would need to create
                return await self._respond(
                    f"I couldn't find a patient with phone {context.patient_phone}. Would you like to register as a new patient?",
                    context,
                )

        if not context.reason:
            context.state = ConversationState.COLLECTING_REASON
            return await self._respond(
                "What is the reason for this visit?",
                context,
            )

        # We have all information - confirm
        context.state = ConversationState.CONFIRMING
        confirmation_text = VOICE_RESPONSES["confirm"]["en"].format(
            doctor=context.doctor_name,
            date=context.appointment_date.strftime("%B %d"),
            time=context.appointment_time.strftime("%I:%M %p"),
        )

        return await self._respond(confirmation_text, context)

    async def _complete_booking(
        self,
        context: BookingContext,
        db: AsyncSession,
    ) -> VoiceResponse:
        """Complete the appointment booking."""
        context.state = ConversationState.BOOKING

        try:
            # Create appointment datetime
            appointment_dt = datetime.combine(
                context.appointment_date,
                context.appointment_time,
                tzinfo=timezone.utc,
            )

            # Get doctor for slot duration
            doctor = await db.get(Doctor, context.doctor_id)
            duration = doctor.slot_duration if doctor else 15

            # Create appointment
            appointment = Appointment(
                patient_id=context.patient_id,
                doctor_id=context.doctor_id,
                scheduled_start=appointment_dt,
                scheduled_end=appointment_dt + timedelta(minutes=duration),
                duration_minutes=duration,
                status=AppointmentStatus.SCHEDULED.value,
                appointment_type=context.appointment_type,
                booking_source=BookingSource.VOICE_AGENT.value,
                chief_complaint=context.reason,
                voice_booking_metadata={
                    "session_id": context.session_id,
                    "conversation_turns": len(context.conversation_history),
                    "language": context.language,
                },
            )

            db.add(appointment)
            await db.commit()
            await db.refresh(appointment)

            context.state = ConversationState.COMPLETED

            return await self._respond(
                f"Your appointment has been booked successfully! Your confirmation number is {str(appointment.id)[:8]}. "
                "You will receive an SMS confirmation shortly. Is there anything else I can help you with?",
                context,
                booking_complete=True,
                appointment_id=appointment.id,
            )

        except Exception as e:
            logger.error(f"Booking error: {e}")
            context.state = ConversationState.ERROR
            return await self._respond(
                "I'm sorry, I couldn't complete the booking due to a system error. Please try again or contact the clinic directly.",
                context,
            )

    async def _handle_availability_check(
        self,
        context: BookingContext,
        nlu_result: NLUResult,
        db: AsyncSession,
    ) -> VoiceResponse:
        """Handle availability check request."""
        if not context.doctor_id and not context.doctor_name:
            return await self._respond(
                "Which doctor's availability would you like to check?",
                context,
            )

        if context.doctor_name and not context.doctor_id:
            doctor = await self._find_doctor(context.clinic_id, context.doctor_name, db)
            if doctor:
                context.doctor_id = doctor.id
                context.doctor_name = doctor.name

        check_date = context.appointment_date or date.today()
        slots = await self._get_available_slots(context.doctor_id, check_date, db)

        if slots:
            slot_times = [s.strftime("%I:%M %p") for s in slots[:5]]
            return await self._respond(
                f"{context.doctor_name} is available on {check_date.strftime('%B %d')} at: {', '.join(slot_times)}. "
                "Would you like to book an appointment?",
                context,
            )
        else:
            return await self._respond(
                f"Unfortunately, {context.doctor_name} has no available slots on {check_date.strftime('%B %d')}. "
                "Would you like to check another date?",
                context,
            )

    async def _get_doctors(
        self,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> list[Doctor]:
        """Get available doctors for a clinic."""
        result = await db.execute(
            select(Doctor)
            .where(Doctor.clinic_id == clinic_id)
            .where(Doctor.is_active == True)
            .where(Doctor.accepting_new_patients == True)
        )
        return list(result.scalars().all())

    async def _find_doctor(
        self,
        clinic_id: UUID,
        name: str,
        db: AsyncSession,
    ) -> Optional[Doctor]:
        """Find a doctor by name."""
        result = await db.execute(
            select(Doctor)
            .where(Doctor.clinic_id == clinic_id)
            .where(Doctor.name.ilike(f"%{name}%"))
            .where(Doctor.is_active == True)
        )
        return result.scalar_one_or_none()

    async def _find_patient(
        self,
        clinic_id: UUID,
        phone: str,
        db: AsyncSession,
    ) -> Optional[Patient]:
        """Find a patient by phone."""
        # Normalize phone
        phone = phone.replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            if phone.startswith("0"):
                phone = "+91" + phone[1:]
            else:
                phone = "+91" + phone

        result = await db.execute(
            select(Patient)
            .where(Patient.clinic_id == clinic_id)
            .where(Patient.phone == phone)
            .where(Patient.is_active == True)
        )
        return result.scalar_one_or_none()

    async def _get_available_slots(
        self,
        doctor_id: UUID,
        target_date: date,
        db: AsyncSession,
    ) -> list[time]:
        """Get available time slots for a doctor on a date."""
        doctor = await db.get(Doctor, doctor_id)
        if not doctor:
            return []

        # Get working hours for the day
        day_name = target_date.strftime("%A").lower()
        working_hours = doctor.working_hours or {}
        day_schedule = working_hours.get(day_name, [])

        if not day_schedule:
            return []

        # Get existing appointments
        start_dt = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(target_date, time.max, tzinfo=timezone.utc)

        result = await db.execute(
            select(Appointment.scheduled_start)
            .where(Appointment.doctor_id == doctor_id)
            .where(Appointment.scheduled_start >= start_dt)
            .where(Appointment.scheduled_start <= end_dt)
            .where(Appointment.status.notin_(["cancelled", "no_show"]))
        )
        booked_times = {row[0].time() for row in result.all()}

        # Generate available slots
        slot_duration = doctor.slot_duration or 15
        available = []

        for period in day_schedule:
            period_start = datetime.strptime(period["start"], "%H:%M").time()
            period_end = datetime.strptime(period["end"], "%H:%M").time()

            current = datetime.combine(target_date, period_start)
            end = datetime.combine(target_date, period_end)

            while current + timedelta(minutes=slot_duration) <= end:
                slot_time = current.time()

                # Skip past slots for today
                if target_date == date.today():
                    if slot_time <= datetime.now().time():
                        current += timedelta(minutes=slot_duration)
                        continue

                if slot_time not in booked_times:
                    available.append(slot_time)

                current += timedelta(minutes=slot_duration)

        return available

    async def _respond(
        self,
        text: str,
        context: BookingContext,
        booking_complete: bool = False,
        appointment_id: Optional[UUID] = None,
        next_action: Optional[str] = None,
        metadata: dict = None,
    ) -> VoiceResponse:
        """Generate voice response."""
        # Generate audio
        try:
            audio = await self.tts.synthesize(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            audio = None

        return VoiceResponse(
            text=text,
            audio=audio,
            state=context.state,
            booking_complete=booking_complete,
            appointment_id=appointment_id,
            next_action=next_action,
            metadata=metadata or {},
        )

    def _cleanup_session(self, session_id: str):
        """Clean up completed session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_session(self, session_id: str) -> Optional[BookingContext]:
        """Get session context."""
        return self.sessions.get(session_id)

    def cleanup_stale_sessions(self, max_age_minutes: int = 30):
        """Remove sessions older than max_age_minutes."""
        now = datetime.now(timezone.utc)
        stale = [
            sid for sid, ctx in self.sessions.items()
            if (now - ctx.last_activity).total_seconds() > max_age_minutes * 60
        ]
        for sid in stale:
            del self.sessions[sid]
