"""
WhatsApp Bot Integration for two-way appointment booking.

Features:
- Receive messages via webhook
- Natural language understanding for booking
- Conversational appointment flow
- Quick reply buttons
- Appointment reminders
- Prescription sharing
- Payment links

Uses WhatsApp Business API (via MSG91 or direct).
"""

import asyncio
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.waitlist import WaitlistStatus
from app.voice.nlu import NaturalLanguageUnderstanding, Intent

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Incoming message types."""
    TEXT = "text"
    BUTTON = "button"
    LIST_REPLY = "list_reply"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"


class ConversationState(str, Enum):
    """WhatsApp conversation states."""
    IDLE = "idle"
    GREETING = "greeting"
    MENU = "menu"
    BOOKING_DOCTOR = "booking_doctor"
    BOOKING_DATE = "booking_date"
    BOOKING_TIME = "booking_time"
    BOOKING_CONFIRM = "booking_confirm"
    CANCEL_SELECT = "cancel_select"
    RESCHEDULE = "reschedule"
    WAITLIST = "waitlist"
    CHECK_STATUS = "check_status"


class MessageIntent(str, Enum):
    """
    Message intents for WhatsApp bot.

    Maps to NLU Intent enum for processing user messages.
    """
    BOOK_APPOINTMENT = "book_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    RESCHEDULE = "reschedule"
    CHECK_STATUS = "check_status"
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class WhatsAppMessage:
    """Incoming WhatsApp message."""
    message_id: str
    from_phone: str
    from_name: str
    message_type: MessageType
    text: Optional[str] = None
    button_id: Optional[str] = None
    button_text: Optional[str] = None
    list_id: Optional[str] = None
    list_title: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: dict = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context for an ongoing conversation."""
    phone: str
    state: ConversationState = ConversationState.IDLE
    clinic_id: Optional[UUID] = None
    patient_id: Optional[UUID] = None
    patient_name: Optional[str] = None
    doctor_id: Optional[UUID] = None
    doctor_name: Optional[str] = None
    appointment_date: Optional[datetime] = None
    appointment_time: Optional[str] = None
    selected_slot: Optional[datetime] = None
    appointment_id: Optional[UUID] = None
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_history: list[dict] = field(default_factory=list)


class WhatsAppBot:
    """
    WhatsApp Bot for appointment management.

    Handles two-way conversations for:
    - Booking appointments
    - Cancelling appointments
    - Checking appointment status
    - Rescheduling
    - Receiving reminders
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        verify_token: Optional[str] = None,
    ):
        """
        Initialize WhatsApp Bot.

        Args:
            api_url: WhatsApp Business API URL
            api_token: API access token
            phone_number_id: WhatsApp phone number ID
            verify_token: Webhook verification token
        """
        self.api_url = api_url or settings.whatsapp_api_url or "https://graph.facebook.com/v17.0"
        self.api_token = api_token or settings.whatsapp_api_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token or "docassist_whatsapp_verify"

        self._client: Optional[httpx.AsyncClient] = None
        self._nlu = NaturalLanguageUnderstanding()

        # Active conversations (in production, use Redis)
        self._conversations: dict[str, ConversationContext] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription.

        Args:
            mode: hub.mode from query params
            token: hub.verify_token from query params
            challenge: hub.challenge from query params

        Returns:
            Challenge string if valid, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("WhatsApp webhook verified")
            return challenge
        return None

    def parse_webhook(self, payload: dict) -> Optional[WhatsAppMessage]:
        """
        Parse incoming webhook payload.

        Args:
            payload: Raw webhook JSON payload

        Returns:
            Parsed WhatsAppMessage or None
        """
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return None

            msg = messages[0]
            contacts = value.get("contacts", [{}])
            contact = contacts[0] if contacts else {}

            message_type = MessageType.TEXT
            text = None
            button_id = None
            button_text = None
            list_id = None
            list_title = None

            if "text" in msg:
                message_type = MessageType.TEXT
                text = msg["text"]["body"]

            elif "button" in msg:
                message_type = MessageType.BUTTON
                button_id = msg["button"]["payload"]
                button_text = msg["button"]["text"]
                text = button_text

            elif "interactive" in msg:
                interactive = msg["interactive"]
                if interactive.get("type") == "button_reply":
                    message_type = MessageType.BUTTON
                    button_id = interactive["button_reply"]["id"]
                    button_text = interactive["button_reply"]["title"]
                    text = button_text
                elif interactive.get("type") == "list_reply":
                    message_type = MessageType.LIST_REPLY
                    list_id = interactive["list_reply"]["id"]
                    list_title = interactive["list_reply"]["title"]
                    text = list_title

            elif "image" in msg:
                message_type = MessageType.IMAGE

            elif "document" in msg:
                message_type = MessageType.DOCUMENT

            return WhatsAppMessage(
                message_id=msg.get("id", str(uuid4())),
                from_phone=msg.get("from", ""),
                from_name=contact.get("profile", {}).get("name", "Patient"),
                message_type=message_type,
                text=text,
                button_id=button_id,
                button_text=button_text,
                list_id=list_id,
                list_title=list_title,
                raw_data=payload,
            )

        except Exception as e:
            logger.error(f"Error parsing webhook: {e}")
            return None

    async def handle_message(
        self,
        message: WhatsAppMessage,
        db: AsyncSession,
        clinic_id: UUID,
    ) -> str:
        """
        Handle incoming message and return response.

        Args:
            message: Parsed WhatsApp message
            db: Database session
            clinic_id: Clinic to use for booking

        Returns:
            Response text to send
        """
        # Get or create conversation context
        context = self._get_context(message.from_phone, clinic_id)

        # Update activity
        context.last_activity = datetime.now(timezone.utc)
        context.patient_name = message.from_name

        # Add to history
        context.message_history.append({
            "role": "user",
            "content": message.text,
            "timestamp": message.timestamp.isoformat(),
        })

        # Handle button/list responses
        if message.message_type == MessageType.BUTTON:
            response = await self._handle_button(message, context, db)
        elif message.message_type == MessageType.LIST_REPLY:
            response = await self._handle_list_reply(message, context, db)
        else:
            # Natural language processing
            response = await self._handle_text(message, context, db)

        # Add response to history
        context.message_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return response

    def _get_context(self, phone: str, clinic_id: UUID) -> ConversationContext:
        """Get or create conversation context."""
        if phone not in self._conversations:
            self._conversations[phone] = ConversationContext(
                phone=phone,
                clinic_id=clinic_id,
            )
        return self._conversations[phone]

    async def _handle_text(
        self,
        message: WhatsAppMessage,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Handle text message using NLU."""
        text = message.text.lower().strip()

        # Check for keywords first
        if text in ["hi", "hello", "hey", "start"]:
            return await self._show_main_menu(context)

        if text in ["menu", "help", "options"]:
            return await self._show_main_menu(context)

        if text in ["book", "appointment", "schedule"]:
            context.state = ConversationState.BOOKING_DOCTOR
            return await self._show_doctor_list(context, db)

        if text in ["cancel"]:
            context.state = ConversationState.CANCEL_SELECT
            return await self._show_appointments_to_cancel(context, db)

        if text in ["status", "check", "my appointments"]:
            return await self._show_appointment_status(context, db)

        # Use NLU for natural language
        try:
            nlu_result = await self._nlu.process(text, [])
            intent = nlu_result.intent

            if intent == Intent.BOOK_APPOINTMENT:
                context.state = ConversationState.BOOKING_DOCTOR
                return await self._show_doctor_list(context, db)

            elif intent == Intent.CANCEL_APPOINTMENT:
                context.state = ConversationState.CANCEL_SELECT
                return await self._show_appointments_to_cancel(context, db)

            elif intent == Intent.CHECK_AVAILABILITY:
                return await self._show_availability(context, db)

            elif intent == Intent.GREETING:
                return await self._show_main_menu(context)

            elif intent == Intent.CONFIRM:
                if context.state == ConversationState.BOOKING_CONFIRM:
                    return await self._confirm_booking(context, db)

            elif intent == Intent.DENY:
                context.state = ConversationState.IDLE
                return "No problem! Let me know if you need anything else. 😊"

        except Exception as e:
            logger.error(f"NLU error: {e}")

        # Default response
        return await self._show_main_menu(context)

    async def _handle_button(
        self,
        message: WhatsAppMessage,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Handle button click."""
        button_id = message.button_id

        if button_id == "book_appointment":
            context.state = ConversationState.BOOKING_DOCTOR
            return await self._show_doctor_list(context, db)

        elif button_id == "my_appointments":
            return await self._show_appointment_status(context, db)

        elif button_id == "cancel_appointment":
            context.state = ConversationState.CANCEL_SELECT
            return await self._show_appointments_to_cancel(context, db)

        elif button_id == "contact_clinic":
            return self._get_contact_info()

        elif button_id.startswith("doctor_"):
            doctor_id = button_id.replace("doctor_", "")
            return await self._select_doctor(context, db, doctor_id)

        elif button_id.startswith("date_"):
            date_str = button_id.replace("date_", "")
            return await self._select_date(context, db, date_str)

        elif button_id.startswith("slot_"):
            slot_str = button_id.replace("slot_", "")
            return await self._select_slot(context, db, slot_str)

        elif button_id == "confirm_booking":
            return await self._confirm_booking(context, db)

        elif button_id == "cancel_booking":
            context.state = ConversationState.IDLE
            return "Booking cancelled. Let me know if you need anything else!"

        return await self._show_main_menu(context)

    async def _handle_list_reply(
        self,
        message: WhatsAppMessage,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Handle list selection."""
        list_id = message.list_id
        return await self._handle_button(message, context, db)

    async def _show_main_menu(self, context: ConversationContext) -> str:
        """Show main menu with options."""
        context.state = ConversationState.MENU
        return (
            f"👋 Hi {context.patient_name}! Welcome to DocAssist.\n\n"
            "How can I help you today?\n\n"
            "📅 *Book Appointment* - Schedule a new appointment\n"
            "📋 *My Appointments* - View your upcoming appointments\n"
            "❌ *Cancel Appointment* - Cancel an existing appointment\n"
            "📞 *Contact Clinic* - Get clinic contact info\n\n"
            "Just type what you need or reply with:\n"
            "• 'book' for new appointment\n"
            "• 'status' to check appointments\n"
            "• 'cancel' to cancel"
        )

    async def _show_doctor_list(
        self,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Show list of available doctors."""
        from app.models.doctor import Doctor
        from sqlalchemy import select

        result = await db.execute(
            select(Doctor)
            .where(Doctor.clinic_id == context.clinic_id)
            .where(Doctor.is_active == True)
        )
        doctors = result.scalars().all()

        if not doctors:
            return "Sorry, no doctors are currently available. Please try again later."

        doctor_list = "\n".join([
            f"{i+1}. 👨‍⚕️ Dr. {d.name} - {d.specialization}"
            for i, d in enumerate(doctors)
        ])

        return (
            "Please select a doctor:\n\n"
            f"{doctor_list}\n\n"
            "Reply with the doctor's number (1, 2, etc.)"
        )

    async def _select_doctor(
        self,
        context: ConversationContext,
        db: AsyncSession,
        doctor_id: str,
    ) -> str:
        """Handle doctor selection."""
        from app.models.doctor import Doctor

        doctor = await db.get(Doctor, UUID(doctor_id))
        if not doctor:
            return "Doctor not found. Please try again."

        context.doctor_id = doctor.id
        context.doctor_name = doctor.name
        context.state = ConversationState.BOOKING_DATE

        return await self._show_available_dates(context, db)

    async def _show_available_dates(
        self,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Show available dates for booking."""
        today = datetime.now().date()
        dates = []
        for i in range(7):
            d = today + timedelta(days=i)
            dates.append(f"{i+1}. 📅 {d.strftime('%A, %B %d')}")

        return (
            f"When would you like to see Dr. {context.doctor_name}?\n\n"
            + "\n".join(dates) +
            "\n\nReply with the number (1-7)"
        )

    async def _select_date(
        self,
        context: ConversationContext,
        db: AsyncSession,
        date_str: str,
    ) -> str:
        """Handle date selection."""
        try:
            from datetime import datetime as dt
            context.appointment_date = dt.strptime(date_str, "%Y-%m-%d")
            context.state = ConversationState.BOOKING_TIME
            return await self._show_available_slots(context, db)
        except Exception as e:
            return "Invalid date. Please try again."

    async def _show_available_slots(
        self,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Show available time slots."""
        # Mock available slots
        slots = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]

        slot_list = "\n".join([f"{i+1}. 🕐 {s}" for i, s in enumerate(slots)])

        return (
            f"Available slots for {context.appointment_date.strftime('%B %d')}:\n\n"
            f"{slot_list}\n\n"
            "Reply with the slot number"
        )

    async def _select_slot(
        self,
        context: ConversationContext,
        db: AsyncSession,
        slot_str: str,
    ) -> str:
        """Handle slot selection."""
        context.appointment_time = slot_str
        context.state = ConversationState.BOOKING_CONFIRM

        return (
            "📋 *Booking Summary*\n\n"
            f"👨‍⚕️ Doctor: Dr. {context.doctor_name}\n"
            f"📅 Date: {context.appointment_date.strftime('%B %d, %Y')}\n"
            f"🕐 Time: {context.appointment_time}\n"
            f"👤 Patient: {context.patient_name}\n\n"
            "Reply 'YES' to confirm or 'NO' to cancel"
        )

    async def _confirm_booking(
        self,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Confirm and create booking."""
        try:
            # In production, create actual appointment
            context.appointment_id = uuid4()
            context.state = ConversationState.IDLE

            return (
                "✅ *Appointment Confirmed!*\n\n"
                f"📋 Booking ID: {str(context.appointment_id)[:8]}\n"
                f"👨‍⚕️ Dr. {context.doctor_name}\n"
                f"📅 {context.appointment_date.strftime('%B %d, %Y')}\n"
                f"🕐 {context.appointment_time}\n\n"
                "📍 Please arrive 10 minutes early.\n"
                "We'll send you a reminder before your appointment.\n\n"
                "Reply 'menu' for more options"
            )
        except Exception as e:
            logger.error(f"Booking error: {e}")
            return "Sorry, there was an error booking your appointment. Please try again or contact the clinic."

    async def _show_appointment_status(
        self,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Show patient's upcoming appointments."""
        # In production, fetch actual appointments
        return (
            "📋 *Your Upcoming Appointments*\n\n"
            "No upcoming appointments found.\n\n"
            "Would you like to book a new appointment?\n"
            "Reply 'book' to schedule"
        )

    async def _show_appointments_to_cancel(
        self,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Show appointments that can be cancelled."""
        return (
            "You don't have any appointments to cancel.\n\n"
            "Reply 'menu' for options"
        )

    async def _show_availability(
        self,
        context: ConversationContext,
        db: AsyncSession,
    ) -> str:
        """Show doctor availability."""
        context.state = ConversationState.BOOKING_DOCTOR
        return await self._show_doctor_list(context, db)

    def _get_contact_info(self) -> str:
        """Get clinic contact information."""
        return (
            "📞 *Contact Us*\n\n"
            "🏥 DocAssist Clinic\n"
            "📍 123 Health Street, Mumbai\n"
            "📱 +91 98765 43210\n"
            "📧 help@docassist.in\n\n"
            "⏰ Mon-Sat: 9 AM - 6 PM"
        )

    async def send_message(
        self,
        to_phone: str,
        text: str,
    ) -> bool:
        """
        Send a text message.

        Args:
            to_phone: Recipient phone number
            text: Message text

        Returns:
            True if sent successfully
        """
        if not self.api_token:
            logger.warning("WhatsApp API not configured")
            return False

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.api_url}/{self.phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "to": to_phone,
                    "type": "text",
                    "text": {"body": text},
                },
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False

    async def send_interactive_buttons(
        self,
        to_phone: str,
        body: str,
        buttons: list[dict],
    ) -> bool:
        """
        Send message with buttons.

        Args:
            to_phone: Recipient phone number
            body: Message body text
            buttons: List of buttons [{id, title}]

        Returns:
            True if sent successfully
        """
        if not self.api_token:
            return False

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.api_url}/{self.phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "to": to_phone,
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": body},
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": b["id"], "title": b["title"]},
                                }
                                for b in buttons[:3]  # Max 3 buttons
                            ]
                        },
                    },
                },
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error sending buttons: {e}")
            return False

    def cleanup_stale_conversations(self, max_age_minutes: int = 60):
        """Remove stale conversation contexts."""
        now = datetime.now(timezone.utc)
        stale = [
            phone for phone, ctx in self._conversations.items()
            if (now - ctx.last_activity).total_seconds() > max_age_minutes * 60
        ]
        for phone in stale:
            del self._conversations[phone]


# Singleton
_whatsapp_bot: Optional[WhatsAppBot] = None


def get_whatsapp_bot() -> WhatsAppBot:
    """Get WhatsApp bot singleton."""
    global _whatsapp_bot
    if _whatsapp_bot is None:
        _whatsapp_bot = WhatsAppBot()
    return _whatsapp_bot
