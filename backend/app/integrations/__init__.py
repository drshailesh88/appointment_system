"""
Integrations module for DocAssist Practice Manager.

Provides integration with:
- EMR (Electronic Medical Records) - SQLite sync
- SMS/WhatsApp (MSG91)
- Payments (Razorpay)
"""

from app.integrations.emr import EMRIntegration
from app.integrations.sms import SMSService
from app.integrations.razorpay import RazorpayService

__all__ = [
    "EMRIntegration",
    "SMSService",
    "RazorpayService",
]
