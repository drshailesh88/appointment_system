"""
Appointment Reminder Service.

Sends appointment reminders via SMS and WhatsApp.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.sms import SMSService, get_sms_service
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient

logger = logging.getLogger(__name__)


class ReminderService:
    """
    Appointment reminder service.

    Sends reminders at configurable intervals before appointments.
    """

    def __init__(
        self,
        sms_service: Optional[SMSService] = None,
    ):
        """Initialize reminder service."""
        self.sms = sms_service or get_sms_service()

    async def send_reminders(
        self,
        db: AsyncSession,
        hours_before: int = 24,
    ) -> dict:
        """
        Send reminders for appointments happening in `hours_before` hours.

        Returns:
            Statistics about reminders sent
        """
        now = datetime.now(timezone.utc)
        reminder_window_start = now + timedelta(hours=hours_before - 1)
        reminder_window_end = now + timedelta(hours=hours_before + 1)

        # Find appointments needing reminders
        result = await db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor),
            )
            .where(
                and_(
                    Appointment.scheduled_start >= reminder_window_start,
                    Appointment.scheduled_start <= reminder_window_end,
                    Appointment.status == AppointmentStatus.SCHEDULED.value,
                    Appointment.reminder_sent == False,
                )
            )
        )
        appointments = result.scalars().all()

        stats = {
            "total": len(appointments),
            "sent": 0,
            "failed": 0,
            "skipped": 0,
        }

        for appointment in appointments:
            patient = appointment.patient
            doctor = appointment.doctor

            if not patient or not doctor:
                stats["skipped"] += 1
                continue

            # Check consent
            if not patient.sms_consent and not patient.whatsapp_consent:
                stats["skipped"] += 1
                continue

            try:
                # Send reminder
                result = await self.sms.send_appointment_reminder(
                    phone=patient.phone,
                    patient_name=patient.full_name,
                    doctor_name=doctor.name,
                    date=appointment.scheduled_start.strftime("%B %d, %Y"),
                    time=appointment.scheduled_start.strftime("%I:%M %p"),
                    prefer_whatsapp=patient.whatsapp_consent,
                )

                if result.success:
                    # Mark as sent
                    appointment.reminder_sent = True
                    appointment.reminder_sent_at = now
                    stats["sent"] += 1
                else:
                    logger.warning(
                        f"Failed to send reminder for appointment {appointment.id}: "
                        f"{result.error}"
                    )
                    stats["failed"] += 1

            except Exception as e:
                logger.error(f"Error sending reminder: {e}")
                stats["failed"] += 1

        await db.commit()

        logger.info(
            f"Reminder batch complete: {stats['sent']} sent, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )

        return stats

    async def send_confirmation(
        self,
        appointment: Appointment,
        db: AsyncSession,
    ) -> bool:
        """Send appointment confirmation immediately after booking."""
        # Load relationships if not already loaded
        if not appointment.patient:
            result = await db.execute(
                select(Patient).where(Patient.id == appointment.patient_id)
            )
            patient = result.scalar_one_or_none()
        else:
            patient = appointment.patient

        if not appointment.doctor:
            result = await db.execute(
                select(Doctor).where(Doctor.id == appointment.doctor_id)
            )
            doctor = result.scalar_one_or_none()
        else:
            doctor = appointment.doctor

        if not patient or not doctor:
            return False

        if not patient.sms_consent and not patient.whatsapp_consent:
            return False

        # Get clinic address
        clinic_address = ""
        if doctor.clinic:
            clinic = doctor.clinic
            clinic_address = f"{clinic.address}, {clinic.city}" if clinic.address else ""

        result = await self.sms.send_appointment_confirmation(
            phone=patient.phone,
            patient_name=patient.full_name,
            doctor_name=doctor.name,
            date=appointment.scheduled_start.strftime("%B %d, %Y"),
            time=appointment.scheduled_start.strftime("%I:%M %p"),
            token=str(appointment.token_number) if appointment.token_number else None,
            clinic_address=clinic_address,
            prefer_whatsapp=patient.whatsapp_consent,
        )

        return result.success

    async def send_cancellation_notice(
        self,
        appointment: Appointment,
        db: AsyncSession,
    ) -> bool:
        """Send cancellation notice."""
        if not appointment.patient:
            result = await db.execute(
                select(Patient).where(Patient.id == appointment.patient_id)
            )
            patient = result.scalar_one_or_none()
        else:
            patient = appointment.patient

        if not appointment.doctor:
            result = await db.execute(
                select(Doctor).where(Doctor.id == appointment.doctor_id)
            )
            doctor = result.scalar_one_or_none()
        else:
            doctor = appointment.doctor

        if not patient or not doctor:
            return False

        # Send via SMS only for cancellations
        from app.integrations.sms import MessageType

        result = await self.sms.send_sms(
            phone=patient.phone,
            message_type=MessageType.APPOINTMENT_CANCELLATION,
            variables={
                "doctor_name": doctor.name,
                "date": appointment.scheduled_start.strftime("%B %d"),
                "time": appointment.scheduled_start.strftime("%I:%M %p"),
            },
        )

        return result.success


# Background task for periodic reminders
async def reminder_task(db_session_factory):
    """
    Background task to send reminders periodically.

    Should be run with asyncio.create_task() on app startup.
    """
    reminder_service = ReminderService()

    while True:
        try:
            async with db_session_factory() as db:
                # Send 24-hour reminders
                await reminder_service.send_reminders(db, hours_before=24)

                # Send 1-hour reminders
                await reminder_service.send_reminders(db, hours_before=1)

        except Exception as e:
            logger.error(f"Reminder task error: {e}")

        # Run every 30 minutes
        await asyncio.sleep(30 * 60)
