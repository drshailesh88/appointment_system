"""
Integrations module for DocAssist Practice Manager.

Provides integration with:
- EMR (Electronic Medical Records) - SQLite sync
- SMS/WhatsApp (MSG91)
- Payments (Razorpay)
- WhatsApp Bot (two-way messaging)
"""

from app.integrations.emr import EMRIntegration
from app.integrations.sms import SMSService
from app.integrations.razorpay import RazorpayService
from app.integrations.whatsapp_bot import WhatsAppBot, get_whatsapp_bot

__all__ = [
    "EMRIntegration",
    "SMSService",
    "RazorpayService",
    "WhatsAppBot",
    "get_whatsapp_bot",
]
