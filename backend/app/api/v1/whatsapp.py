"""
WhatsApp Bot Webhook API endpoints.

Handles incoming WhatsApp messages and webhook verification.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.integrations.whatsapp_bot import WhatsAppBot, get_whatsapp_bot

logger = logging.getLogger(__name__)

router = APIRouter()


class WebhookPayload(BaseModel):
    """Incoming webhook payload."""
    object: str
    entry: list


class MessageResponse(BaseModel):
    """Response after processing message."""
    success: bool
    response_sent: bool
    message: str


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """
    Verify WhatsApp webhook subscription.

    Meta sends this request when setting up the webhook.
    Must return the challenge string to verify.
    """
    bot = get_whatsapp_bot()
    result = bot.verify_webhook(hub_mode, hub_token, hub_challenge)

    if result:
        return int(result)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Webhook verification failed",
    )


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: DbSession,
):
    """
    Receive incoming WhatsApp messages.

    Processes messages and sends responses via the bot.
    """
    try:
        from app.core.config import settings
        from app.core.security import verify_meta_webhook_signature

        # Get raw body for signature verification
        body = await request.body()

        # Verify webhook signature if app secret is configured
        if settings.whatsapp_app_secret:
            signature_header = request.headers.get("X-Hub-Signature-256", "")
            if not signature_header:
                logger.warning("WhatsApp webhook missing signature header")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing signature header",
                )

            if not verify_meta_webhook_signature(
                body,
                signature_header,
                settings.whatsapp_app_secret,
            ):
                logger.warning("WhatsApp webhook signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                )

        # Parse JSON body
        payload = request.json() if isinstance(body, bytes) else body
        if isinstance(body, bytes):
            import json
            payload = json.loads(body)
        logger.info(f"Received WhatsApp webhook: {payload}")

        # Verify it's a WhatsApp notification
        if payload.get("object") != "whatsapp_business_account":
            return {"status": "ignored"}

        bot = get_whatsapp_bot()
        message = bot.parse_webhook(payload)

        if not message:
            return {"status": "no_message"}

        # Get clinic ID (in production, would determine from phone number mapping)
        # For now, use a default or extract from message metadata
        clinic_id = await _get_clinic_for_phone(message.from_phone, db)

        if not clinic_id:
            logger.warning(f"No clinic found for phone {message.from_phone}")
            return {"status": "no_clinic"}

        # Process message and get response
        response_text = await bot.handle_message(message, db, clinic_id)

        # Send response
        success = await bot.send_message(message.from_phone, response_text)

        return {
            "status": "processed",
            "response_sent": success,
            "from": message.from_phone,
        }

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/send")
async def send_message(
    to_phone: str,
    message: str,
    current_user: CurrentUser,
):
    """
    Send a WhatsApp message manually.

    Admin endpoint to send messages to patients.
    """
    if current_user.role not in ["admin", "owner", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send messages",
        )

    bot = get_whatsapp_bot()
    success = await bot.send_message(to_phone, message)

    if success:
        return {"success": True, "message": "Message sent"}
    else:
        return {"success": False, "message": "Failed to send message"}


@router.post("/send-buttons")
async def send_buttons(
    to_phone: str,
    body: str,
    buttons: list[dict],
    current_user: CurrentUser,
):
    """
    Send a WhatsApp message with interactive buttons.

    Buttons should be a list of {id, title} objects (max 3).
    """
    if current_user.role not in ["admin", "owner", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send messages",
        )

    if len(buttons) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 3 buttons allowed",
        )

    bot = get_whatsapp_bot()
    success = await bot.send_interactive_buttons(to_phone, body, buttons)

    return {"success": success}


@router.post("/send-appointment-reminder")
async def send_appointment_reminder(
    appointment_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Send appointment reminder via WhatsApp.

    Fetches appointment details and sends reminder to patient.
    """
    from app.models.appointment import Appointment
    from app.models.patient import Patient
    from app.models.doctor import Doctor

    if current_user.role not in ["admin", "owner", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    patient = await db.get(Patient, appointment.patient_id)
    doctor = await db.get(Doctor, appointment.doctor_id)

    if not patient or not patient.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient phone not available",
        )

    message = (
        f"⏰ *Appointment Reminder*\n\n"
        f"Hi {patient.full_name}!\n\n"
        f"Your appointment with Dr. {doctor.name} is scheduled for:\n"
        f"📅 {appointment.scheduled_start.strftime('%B %d, %Y')}\n"
        f"🕐 {appointment.scheduled_start.strftime('%I:%M %p')}\n\n"
        f"Please arrive 10 minutes early.\n\n"
        f"Reply YES to confirm or RESCHEDULE to change."
    )

    bot = get_whatsapp_bot()
    success = await bot.send_message(patient.phone, message)

    return {
        "success": success,
        "patient": patient.full_name,
        "phone": patient.phone,
    }


@router.post("/send-waitlist-notification")
async def send_waitlist_notification(
    waitlist_id: UUID,
    slot_time: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Send waitlist slot availability notification.

    Notifies patient that a slot has opened up.
    """
    from app.models.waitlist import Waitlist
    from app.models.doctor import Doctor

    if current_user.role not in ["admin", "owner", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

    entry = await db.get(Waitlist, waitlist_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found",
        )

    doctor_name = "the doctor"
    if entry.doctor_id:
        doctor = await db.get(Doctor, entry.doctor_id)
        if doctor:
            doctor_name = f"Dr. {doctor.name}"

    message = (
        f"🎉 *Good News!*\n\n"
        f"Hi {entry.patient_name}!\n\n"
        f"An appointment slot has opened up with {doctor_name}!\n\n"
        f"📅 Available slot: {slot_time}\n\n"
        f"Reply YES to book this slot (expires in 30 minutes)\n"
        f"Reply NO to stay on the waitlist"
    )

    bot = get_whatsapp_bot()
    success = await bot.send_message(entry.patient_phone, message)

    return {
        "success": success,
        "patient": entry.patient_name,
        "phone": entry.patient_phone,
    }


async def _get_clinic_for_phone(phone: str, db) -> Optional[UUID]:
    """
    Get clinic ID for a phone number.

    In production, this would:
    1. Look up patient by phone
    2. Get their associated clinic
    3. Or use the clinic's WhatsApp number mapping
    """
    from app.models.patient import Patient
    from sqlalchemy import select

    # Try to find patient by phone
    result = await db.execute(
        select(Patient).where(Patient.phone == phone).limit(1)
    )
    patient = result.scalar_one_or_none()

    if patient:
        return patient.clinic_id

    # Could also look up by configured clinic phone numbers
    # For now, return None and let caller handle

    return None
