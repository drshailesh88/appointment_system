"""
Voice Bot service for phone-based appointment booking.

Phase 18: Voice Bot / Phone Automation
"""

from app.services.voice_bot.bot import AppointmentBookingBot, ConversationState
from app.services.voice_bot.telephony import TelephonyService

__all__ = [
    "AppointmentBookingBot",
    "ConversationState",
    "TelephonyService",
]
