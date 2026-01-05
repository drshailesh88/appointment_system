"""
SMS Service for DocAssist Practice Manager.

Provides high-level SMS sending functionality using MSG91 gateway
with DLT-compliant templates.
"""

import logging
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.integrations.msg91 import MSG91Client, SMSResponse, get_msg91_client
from app.integrations.sms_templates import MessageType, format_message

logger = logging.getLogger(__name__)


class SMSService:
    """
    High-level SMS service using MSG91.

    Handles template selection, phone number formatting, and delivery tracking.
    """

    def __init__(self, msg91_client: Optional[MSG91Client] = None):
        """
        Initialize SMS service.

        Args:
            msg91_client: MSG91 client instance (uses singleton if not provided)
        """
        self.client = msg91_client or get_msg91_client()

    async def send_appointment_confirmation(
        self,
        phone: str,
        patient_name: str,
        doctor_name: str,
        date: str,
        time: str,
        token: str,
        clinic_name: str,
    ) -> SMSResponse:
        """
        Send appointment confirmation SMS.

        Args:
            phone: Patient phone number
            patient_name: Patient name
            doctor_name: Doctor name
            date: Appointment date (formatted string)
            time: Appointment time (formatted string)
            token: Token/queue number
            clinic_name: Clinic name

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.APPOINTMENT_CONFIRMATION,
            patient_name=patient_name,
            doctor_name=doctor_name,
            date=date,
            time=time,
            token=token,
            clinic_name=clinic_name,
        )

        logger.info(
            f"Sending appointment confirmation to {phone}: "
            f"{doctor_name} on {date} at {time}"
        )

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_appointment_reminder(
        self,
        phone: str,
        doctor_name: str,
        time: str,
        clinic_phone: str,
    ) -> SMSResponse:
        """
        Send appointment reminder SMS (24 hours before).

        Args:
            phone: Patient phone number
            doctor_name: Doctor name
            time: Appointment time
            clinic_phone: Clinic phone number for queries

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.APPOINTMENT_REMINDER,
            doctor_name=doctor_name,
            time=time,
            clinic_phone=clinic_phone,
        )

        logger.info(f"Sending appointment reminder to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_appointment_cancellation(
        self,
        phone: str,
        doctor_name: str,
        date: str,
        time: str,
        reason: str = "Rescheduled by clinic",
    ) -> SMSResponse:
        """
        Send appointment cancellation SMS.

        Args:
            phone: Patient phone number
            doctor_name: Doctor name
            date: Appointment date
            time: Appointment time
            reason: Cancellation reason

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.APPOINTMENT_CANCELLATION,
            doctor_name=doctor_name,
            date=date,
            time=time,
            reason=reason,
        )

        logger.info(f"Sending appointment cancellation to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_appointment_rescheduled(
        self,
        phone: str,
        doctor_name: str,
        new_date: str,
        new_time: str,
        token: str,
    ) -> SMSResponse:
        """
        Send appointment rescheduled notification.

        Args:
            phone: Patient phone number
            doctor_name: Doctor name
            new_date: New appointment date
            new_time: New appointment time
            token: New token number

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.APPOINTMENT_RESCHEDULED,
            doctor_name=doctor_name,
            new_date=new_date,
            new_time=new_time,
            token=token,
        )

        logger.info(f"Sending reschedule notification to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_otp(
        self,
        phone: str,
        otp: str,
        validity_minutes: int = 5,
    ) -> SMSResponse:
        """
        Send OTP SMS.

        Args:
            phone: Patient phone number
            otp: OTP code
            validity_minutes: OTP validity in minutes

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.OTP,
            otp=otp,
            validity=str(validity_minutes),
        )

        logger.info(f"Sending OTP to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_welcome(
        self,
        phone: str,
        clinic_name: str,
    ) -> SMSResponse:
        """
        Send welcome message to new patient.

        Args:
            phone: Patient phone number
            clinic_name: Clinic name

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.WELCOME,
            clinic_name=clinic_name,
        )

        logger.info(f"Sending welcome message to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_payment_receipt(
        self,
        phone: str,
        amount: str,
        invoice_number: str,
        clinic_name: str,
    ) -> SMSResponse:
        """
        Send payment receipt SMS.

        Args:
            phone: Patient phone number
            amount: Payment amount
            invoice_number: Invoice number
            clinic_name: Clinic name

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.PAYMENT_RECEIPT,
            amount=amount,
            invoice_number=invoice_number,
            clinic_name=clinic_name,
        )

        logger.info(f"Sending payment receipt to {phone} for Rs. {amount}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_waitlist_notification(
        self,
        phone: str,
        doctor_name: str,
        date: str,
        time: str,
        clinic_phone: str,
    ) -> SMSResponse:
        """
        Send waitlist slot available notification.

        Args:
            phone: Patient phone number
            doctor_name: Doctor name
            date: Available date
            time: Available time
            clinic_phone: Clinic phone for booking

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.WAITLIST_NOTIFICATION,
            doctor_name=doctor_name,
            date=date,
            time=time,
            clinic_phone=clinic_phone,
        )

        logger.info(f"Sending waitlist notification to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_slot_offer(
        self,
        phone: str,
        doctor_name: str,
        date: str,
        time: str,
        clinic_phone: str,
    ) -> SMSResponse:
        """
        Send slot availability offer (promotional).

        Args:
            phone: Patient phone number
            doctor_name: Doctor name
            date: Available date
            time: Available time
            clinic_phone: Clinic phone

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.SLOT_OFFER,
            doctor_name=doctor_name,
            date=date,
            time=time,
            clinic_phone=clinic_phone,
        )

        logger.info(f"Sending slot offer to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_prescription_ready(
        self,
        phone: str,
        patient_name: str,
        clinic_name: str,
    ) -> SMSResponse:
        """
        Send prescription ready notification.

        Args:
            phone: Patient phone number
            patient_name: Patient name
            clinic_name: Clinic name

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.PRESCRIPTION_READY,
            patient_name=patient_name,
            clinic_name=clinic_name,
        )

        logger.info(f"Sending prescription ready notification to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def send_lab_report_ready(
        self,
        phone: str,
        patient_name: str,
        clinic_phone: str,
    ) -> SMSResponse:
        """
        Send lab report ready notification.

        Args:
            phone: Patient phone number
            patient_name: Patient name
            clinic_phone: Clinic phone for queries

        Returns:
            SMSResponse with delivery status
        """
        message, template_id = format_message(
            MessageType.LAB_REPORT_READY,
            patient_name=patient_name,
            clinic_phone=clinic_phone,
        )

        logger.info(f"Sending lab report ready notification to {phone}")

        return await self.client.send_sms(
            phone=phone,
            message=message,
            template_id=template_id,
        )

    async def close(self):
        """Close underlying HTTP client."""
        await self.client.close()


# Singleton instance
_sms_service: Optional[SMSService] = None


def get_sms_service() -> SMSService:
    """Get SMS service singleton."""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
