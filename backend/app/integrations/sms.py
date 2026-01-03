"""
SMS and WhatsApp Integration using MSG91.

MSG91 is a popular Indian SMS gateway that supports:
- Transactional SMS
- Promotional SMS
- WhatsApp Business API
- OTP services
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages."""

    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CANCELLATION = "appointment_cancellation"
    OTP = "otp"
    WELCOME = "welcome"
    PAYMENT_RECEIPT = "payment_receipt"


class MessageChannel(str, Enum):
    """Message delivery channels."""

    SMS = "sms"
    WHATSAPP = "whatsapp"


@dataclass
class MessageResult:
    """Result of sending a message."""

    success: bool
    message_id: Optional[str] = None
    channel: Optional[MessageChannel] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


# SMS Templates (DLT registered for India)
SMS_TEMPLATES = {
    MessageType.APPOINTMENT_CONFIRMATION: {
        "template_id": "1234567890",  # Replace with actual DLT template ID
        "template": (
            "Dear {patient_name}, your appointment with {doctor_name} is confirmed "
            "for {date} at {time}. Token: {token}. - DocAssist"
        ),
    },
    MessageType.APPOINTMENT_REMINDER: {
        "template_id": "1234567891",
        "template": (
            "Reminder: Your appointment with {doctor_name} is scheduled for "
            "{date} at {time}. Please arrive 10 mins early. - DocAssist"
        ),
    },
    MessageType.APPOINTMENT_CANCELLATION: {
        "template_id": "1234567892",
        "template": (
            "Your appointment with {doctor_name} on {date} at {time} has been "
            "cancelled. Please reschedule if needed. - DocAssist"
        ),
    },
    MessageType.OTP: {
        "template_id": "1234567893",
        "template": "{otp} is your OTP for DocAssist. Valid for {validity} minutes. Do not share.",
    },
    MessageType.WELCOME: {
        "template_id": "1234567894",
        "template": (
            "Welcome to {clinic_name}! We're happy to have you. "
            "Book appointments easily via our app. - DocAssist"
        ),
    },
    MessageType.PAYMENT_RECEIPT: {
        "template_id": "1234567895",
        "template": (
            "Payment of Rs.{amount} received for Invoice #{invoice_number}. "
            "Thank you! - {clinic_name}"
        ),
    },
}

# WhatsApp Templates
WHATSAPP_TEMPLATES = {
    MessageType.APPOINTMENT_CONFIRMATION: {
        "template_name": "appointment_confirmation",
        "template": (
            "✅ *Appointment Confirmed*\n\n"
            "👤 Patient: {patient_name}\n"
            "👨‍⚕️ Doctor: {doctor_name}\n"
            "📅 Date: {date}\n"
            "🕐 Time: {time}\n"
            "🎫 Token: {token}\n\n"
            "📍 Location: {clinic_address}\n\n"
            "Reply CANCEL to cancel this appointment."
        ),
    },
    MessageType.APPOINTMENT_REMINDER: {
        "template_name": "appointment_reminder",
        "template": (
            "⏰ *Appointment Reminder*\n\n"
            "Your appointment with *{doctor_name}* is tomorrow!\n\n"
            "📅 {date} at {time}\n\n"
            "Please arrive 10 minutes early.\n"
            "Reply YES to confirm or RESCHEDULE to change."
        ),
    },
}


class SMSService:
    """
    SMS and WhatsApp messaging service.

    Uses MSG91 API for sending messages.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sender_id: Optional[str] = None,
    ):
        """
        Initialize SMS service.

        Args:
            api_key: MSG91 API key
            sender_id: Sender ID for SMS
        """
        self.api_key = api_key or settings.sms_api_key
        self.sender_id = sender_id or settings.sms_sender_id
        self.base_url = "https://api.msg91.com/api/v5"
        self.whatsapp_url = "https://api.msg91.com/api/v5/whatsapp"

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "authkey": self.api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _format_phone(self, phone: str) -> str:
        """Format phone number for MSG91 (without + prefix)."""
        phone = phone.replace(" ", "").replace("-", "")
        if phone.startswith("+"):
            phone = phone[1:]
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone
        return phone

    async def send_sms(
        self,
        phone: str,
        message_type: MessageType,
        variables: dict,
    ) -> MessageResult:
        """
        Send an SMS message.

        Args:
            phone: Recipient phone number
            message_type: Type of message to send
            variables: Template variables

        Returns:
            MessageResult with status
        """
        if not self.api_key:
            logger.warning("SMS API key not configured. Message not sent.")
            return MessageResult(
                success=False,
                error="SMS service not configured",
                channel=MessageChannel.SMS,
            )

        template_config = SMS_TEMPLATES.get(message_type)
        if not template_config:
            return MessageResult(
                success=False,
                error=f"Unknown message type: {message_type}",
                channel=MessageChannel.SMS,
            )

        try:
            # Format message
            message = template_config["template"].format(**variables)
            phone = self._format_phone(phone)

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/flow/",
                json={
                    "template_id": template_config["template_id"],
                    "sender": self.sender_id,
                    "mobiles": phone,
                    "VAR1": variables.get("var1", ""),
                    "VAR2": variables.get("var2", ""),
                    "VAR3": variables.get("var3", ""),
                    # MSG91 uses positional variables
                },
            )

            if response.status_code == 200:
                result = response.json()
                return MessageResult(
                    success=True,
                    message_id=result.get("request_id"),
                    channel=MessageChannel.SMS,
                )
            else:
                return MessageResult(
                    success=False,
                    error=f"API error: {response.status_code} - {response.text}",
                    channel=MessageChannel.SMS,
                )

        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return MessageResult(
                success=False,
                error=str(e),
                channel=MessageChannel.SMS,
            )

    async def send_whatsapp(
        self,
        phone: str,
        message_type: MessageType,
        variables: dict,
    ) -> MessageResult:
        """
        Send a WhatsApp message.

        Args:
            phone: Recipient phone number
            message_type: Type of message to send
            variables: Template variables

        Returns:
            MessageResult with status
        """
        if not self.api_key:
            logger.warning("WhatsApp API key not configured. Message not sent.")
            return MessageResult(
                success=False,
                error="WhatsApp service not configured",
                channel=MessageChannel.WHATSAPP,
            )

        template_config = WHATSAPP_TEMPLATES.get(message_type)
        if not template_config:
            return MessageResult(
                success=False,
                error=f"WhatsApp template not available for: {message_type}",
                channel=MessageChannel.WHATSAPP,
            )

        try:
            phone = self._format_phone(phone)

            client = await self._get_client()
            response = await client.post(
                f"{self.whatsapp_url}/whatsapp/sendTemplateMessage",
                json={
                    "integrated_number": self.sender_id,
                    "destination": phone,
                    "template_name": template_config["template_name"],
                    "template_variables": list(variables.values()),
                },
            )

            if response.status_code == 200:
                result = response.json()
                return MessageResult(
                    success=True,
                    message_id=result.get("request_id"),
                    channel=MessageChannel.WHATSAPP,
                )
            else:
                return MessageResult(
                    success=False,
                    error=f"API error: {response.status_code}",
                    channel=MessageChannel.WHATSAPP,
                )

        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return MessageResult(
                success=False,
                error=str(e),
                channel=MessageChannel.WHATSAPP,
            )

    async def send_appointment_confirmation(
        self,
        phone: str,
        patient_name: str,
        doctor_name: str,
        date: str,
        time: str,
        token: Optional[str] = None,
        clinic_address: Optional[str] = None,
        prefer_whatsapp: bool = True,
    ) -> MessageResult:
        """Send appointment confirmation via preferred channel."""
        variables = {
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "date": date,
            "time": time,
            "token": token or "N/A",
            "clinic_address": clinic_address or "",
        }

        if prefer_whatsapp:
            result = await self.send_whatsapp(
                phone,
                MessageType.APPOINTMENT_CONFIRMATION,
                variables,
            )
            if result.success:
                return result
            # Fallback to SMS
            logger.info("WhatsApp failed, falling back to SMS")

        return await self.send_sms(
            phone,
            MessageType.APPOINTMENT_CONFIRMATION,
            variables,
        )

    async def send_appointment_reminder(
        self,
        phone: str,
        patient_name: str,
        doctor_name: str,
        date: str,
        time: str,
        prefer_whatsapp: bool = True,
    ) -> MessageResult:
        """Send appointment reminder."""
        variables = {
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "date": date,
            "time": time,
        }

        if prefer_whatsapp:
            result = await self.send_whatsapp(
                phone,
                MessageType.APPOINTMENT_REMINDER,
                variables,
            )
            if result.success:
                return result

        return await self.send_sms(
            phone,
            MessageType.APPOINTMENT_REMINDER,
            variables,
        )

    async def send_otp(
        self,
        phone: str,
        otp: str,
        validity_minutes: int = 10,
    ) -> MessageResult:
        """Send OTP via SMS."""
        return await self.send_sms(
            phone,
            MessageType.OTP,
            {
                "otp": otp,
                "validity": str(validity_minutes),
            },
        )

    async def send_payment_receipt(
        self,
        phone: str,
        amount: str,
        invoice_number: str,
        clinic_name: str,
    ) -> MessageResult:
        """Send payment receipt."""
        return await self.send_sms(
            phone,
            MessageType.PAYMENT_RECEIPT,
            {
                "amount": amount,
                "invoice_number": invoice_number,
                "clinic_name": clinic_name,
            },
        )


# Singleton instance
_sms_service: Optional[SMSService] = None


def get_sms_service() -> SMSService:
    """Get SMS service singleton."""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
