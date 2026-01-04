"""
Example integration guide for using the realtime service.

This file demonstrates how to integrate real-time WebSocket notifications
into existing services like appointments and waitlist.

DO NOT import this file in production code. It's for documentation only.
"""

from datetime import datetime
from uuid import UUID

from app.services.realtime import (
    AppointmentEventData,
    EventType,
    NotificationEventData,
    WaitlistEventData,
    get_realtime_service,
)


# Example 1: Publishing appointment events
async def example_create_appointment(
    appointment_id: UUID,
    patient_id: UUID,
    patient_name: str,
    doctor_id: UUID,
    doctor_name: str,
    clinic_id: UUID,
    scheduled_start: datetime,
    scheduled_end: datetime,
) -> None:
    """Example: Notify clients when a new appointment is created."""
    realtime = get_realtime_service()

    appointment_data = AppointmentEventData(
        appointment_id=appointment_id,
        patient_id=patient_id,
        patient_name=patient_name,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status="scheduled",
        token_number=None,
        chief_complaint=None,
    )

    await realtime.publish_appointment_event(
        event_type=EventType.APPOINTMENT_CREATED,
        clinic_id=clinic_id,
        appointment_data=appointment_data,
        metadata={"created_by": "system"},
    )


# Example 2: Publishing appointment status changes
async def example_update_appointment_status(
    appointment_id: UUID,
    patient_id: UUID,
    patient_name: str,
    doctor_id: UUID,
    doctor_name: str,
    clinic_id: UUID,
    scheduled_start: datetime,
    scheduled_end: datetime,
    new_status: str,
    token_number: int | None = None,
) -> None:
    """Example: Notify clients when appointment status changes."""
    realtime = get_realtime_service()

    appointment_data = AppointmentEventData(
        appointment_id=appointment_id,
        patient_id=patient_id,
        patient_name=patient_name,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status=new_status,
        token_number=token_number,
    )

    # Map status to event type
    event_type_map = {
        "confirmed": EventType.APPOINTMENT_CONFIRMED,
        "checked_in": EventType.APPOINTMENT_CHECKED_IN,
        "in_progress": EventType.APPOINTMENT_STARTED,
        "completed": EventType.APPOINTMENT_COMPLETED,
        "cancelled": EventType.APPOINTMENT_CANCELLED,
        "no_show": EventType.APPOINTMENT_NO_SHOW,
    }

    event_type = event_type_map.get(new_status, EventType.APPOINTMENT_UPDATED)

    await realtime.publish_appointment_event(
        event_type=event_type,
        clinic_id=clinic_id,
        appointment_data=appointment_data,
        metadata={"previous_status": "scheduled", "updated_at": datetime.utcnow().isoformat()},
    )


# Example 3: Publishing waitlist events
async def example_add_to_waitlist(
    waitlist_id: UUID,
    patient_name: str,
    patient_phone: str,
    clinic_id: UUID,
    doctor_id: UUID | None,
    doctor_name: str | None,
    priority: str,
    queue_position: int,
    preferred_date: str,
) -> None:
    """Example: Notify clients when a patient joins the waitlist."""
    realtime = get_realtime_service()

    waitlist_data = WaitlistEventData(
        waitlist_id=waitlist_id,
        patient_name=patient_name,
        patient_phone=patient_phone,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        priority=priority,
        status="waiting",
        queue_position=queue_position,
        preferred_date=preferred_date,
    )

    await realtime.publish_waitlist_event(
        event_type=EventType.WAITLIST_JOINED,
        clinic_id=clinic_id,
        waitlist_data=waitlist_data,
        metadata={"estimated_wait_minutes": 30},
    )


# Example 4: Publishing waitlist slot availability
async def example_notify_slot_available(
    waitlist_id: UUID,
    patient_name: str,
    patient_phone: str,
    clinic_id: UUID,
    doctor_id: UUID,
    doctor_name: str,
    priority: str,
    queue_position: int,
    preferred_date: str,
    offered_slot_time: datetime,
) -> None:
    """Example: Notify patient when a slot becomes available."""
    realtime = get_realtime_service()

    waitlist_data = WaitlistEventData(
        waitlist_id=waitlist_id,
        patient_name=patient_name,
        patient_phone=patient_phone,
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        priority=priority,
        status="notified",
        queue_position=queue_position,
        preferred_date=preferred_date,
        offered_slot_time=offered_slot_time,
    )

    await realtime.publish_waitlist_event(
        event_type=EventType.WAITLIST_SLOT_AVAILABLE,
        clinic_id=clinic_id,
        waitlist_data=waitlist_data,
        metadata={
            "expires_in_minutes": 30,
            "slot_time": offered_slot_time.isoformat(),
        },
    )


# Example 5: Publishing general notifications
async def example_send_reminder_notification(
    clinic_id: UUID,
    user_id: UUID,
    patient_name: str,
    appointment_time: datetime,
) -> None:
    """Example: Send a reminder notification to staff."""
    realtime = get_realtime_service()

    notification_data = NotificationEventData(
        notification_id=f"reminder_{datetime.utcnow().timestamp()}",
        title="Appointment Reminder",
        message=f"Reminder: {patient_name} has an appointment at {appointment_time.strftime('%I:%M %p')}",
        priority="normal",
        user_id=user_id,
    )

    await realtime.publish_notification_event(
        event_type=EventType.NOTIFICATION_REMINDER,
        clinic_id=clinic_id,
        notification_data=notification_data,
    )


# Example 6: Publishing system-wide announcements
async def example_system_maintenance_announcement() -> None:
    """Example: Broadcast a system maintenance message to all clients."""
    realtime = get_realtime_service()

    await realtime.publish_system_event(
        event_type=EventType.SYSTEM_MAINTENANCE,
        message="System will undergo maintenance in 10 minutes. Please save your work.",
        metadata={
            "severity": "warning",
            "scheduled_time": "2024-01-01T22:00:00Z",
            "duration_minutes": 30,
        },
    )


# Example 7: Integration in appointment service
"""
To integrate into your existing appointment service (e.g., app/api/v1/appointments.py):

@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    appointment: AppointmentCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Any:
    # ... existing appointment creation logic ...

    new_appointment = Appointment(**appointment.dict())
    db.add(new_appointment)
    await db.commit()
    await db.refresh(new_appointment)

    # Publish real-time event
    realtime = get_realtime_service()
    appointment_data = AppointmentEventData(
        appointment_id=new_appointment.id,
        patient_id=new_appointment.patient_id,
        patient_name=new_appointment.patient.name,  # Assuming relationship loaded
        doctor_id=new_appointment.doctor_id,
        doctor_name=new_appointment.doctor.name,
        scheduled_start=new_appointment.scheduled_start,
        scheduled_end=new_appointment.scheduled_end,
        status=new_appointment.status,
        token_number=new_appointment.token_number,
        chief_complaint=new_appointment.chief_complaint,
    )

    await realtime.publish_appointment_event(
        event_type=EventType.APPOINTMENT_CREATED,
        clinic_id=current_user.clinic_id,
        appointment_data=appointment_data,
        metadata={"created_by": str(current_user.id)},
    )

    return new_appointment
"""


# Example 8: Integration in waitlist service
"""
To integrate into your existing waitlist service (e.g., app/services/waitlist.py):

async def notify_waitlist_for_slot(
    db: AsyncSession,
    clinic_id: UUID,
    doctor_id: UUID,
    slot_time: datetime,
) -> None:
    # ... existing logic to find next waitlist entry ...

    if waitlist_entry:
        # Mark as notified
        waitlist_entry.mark_notified(offered_slot=slot_time, expires_in_minutes=30)
        await db.commit()

        # Publish real-time event
        realtime = get_realtime_service()
        waitlist_data = WaitlistEventData(
            waitlist_id=waitlist_entry.id,
            patient_name=waitlist_entry.patient_name,
            patient_phone=waitlist_entry.patient_phone,
            doctor_id=waitlist_entry.doctor_id,
            doctor_name=waitlist_entry.doctor.name if waitlist_entry.doctor else None,
            priority=waitlist_entry.priority,
            status=waitlist_entry.status,
            queue_position=waitlist_entry.queue_position,
            preferred_date=str(waitlist_entry.preferred_date),
            offered_slot_time=slot_time,
        )

        await realtime.publish_waitlist_event(
            event_type=EventType.WAITLIST_SLOT_AVAILABLE,
            clinic_id=clinic_id,
            waitlist_data=waitlist_data,
            metadata={"expires_in_minutes": 30},
        )

        # Also send via SMS/WhatsApp (existing logic)
        # ...
"""
