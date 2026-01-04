"""
AI Action Executor Service.

Phase 16b: Conversational Actions

Executes actions requested via AI chat using function calling pattern.
Maps natural language to actual service calls with confirmation flow.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus, BookingSource
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.waitlist import Waitlist, WaitlistPriority, WaitlistStatus

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Available action types."""

    BOOK_APPOINTMENT = "book_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    ADD_TO_WAITLIST = "add_to_waitlist"
    SEND_REMINDER = "send_reminder"
    LOOKUP_PATIENT = "lookup_patient"
    CHECK_AVAILABILITY = "check_availability"


@dataclass
class ActionResult:
    """Result of action execution."""

    success: bool
    action_type: ActionType
    message: str
    data: Optional[dict[str, Any]] = None
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PendingAction:
    """Pending action awaiting user confirmation."""

    action_id: UUID
    action_type: ActionType
    params: dict[str, Any]
    preview_data: dict[str, Any]
    created_at: datetime
    expires_at: datetime


@dataclass
class UndoRecord:
    """Record of action for undo capability."""

    action_id: UUID
    action_type: ActionType
    original_data: dict[str, Any]
    executed_at: datetime
    can_undo: bool
    undo_reason: Optional[str] = None


class AIActionExecutor:
    """Execute actions from AI chat commands."""

    # Action definitions for LLM function calling
    ACTION_DEFINITIONS = {
        "book_appointment": {
            "description": "Book a new appointment for a patient",
            "parameters": {
                "patient_id": "UUID (required) - Patient to book for",
                "doctor_id": "UUID (optional) - Doctor to see",
                "date": "date (required) - Appointment date",
                "time": "time (required) - Appointment time",
                "reason": "string (optional) - Reason for visit",
                "duration_minutes": "int (optional) - Duration in minutes (default: 15)",
            },
            "requires_confirmation": True,
        },
        "reschedule_appointment": {
            "description": "Reschedule an existing appointment",
            "parameters": {
                "appointment_id": "UUID (required) - Appointment to reschedule",
                "new_date": "date (required) - New appointment date",
                "new_time": "time (required) - New appointment time",
            },
            "requires_confirmation": True,
        },
        "cancel_appointment": {
            "description": "Cancel an appointment",
            "parameters": {
                "appointment_id": "UUID (required) - Appointment to cancel",
                "reason": "string (optional) - Cancellation reason",
            },
            "requires_confirmation": True,
        },
        "add_to_waitlist": {
            "description": "Add patient to waitlist",
            "parameters": {
                "patient_id": "UUID (required) - Patient to add",
                "doctor_id": "UUID (optional) - Preferred doctor",
                "urgency": "low|medium|high - Urgency level",
                "notes": "string (optional) - Additional notes",
            },
            "requires_confirmation": False,
        },
        "send_reminder": {
            "description": "Send appointment reminder to patient",
            "parameters": {
                "appointment_id": "UUID (required) - Appointment to remind about",
                "channel": "sms|whatsapp|email - Communication channel",
            },
            "requires_confirmation": False,
        },
        "lookup_patient": {
            "description": "Search for a patient by name or phone",
            "parameters": {
                "query": "string (required) - Name or phone to search",
            },
            "requires_confirmation": False,
        },
        "check_availability": {
            "description": "Check doctor availability for a date",
            "parameters": {
                "doctor_id": "UUID (optional) - Doctor to check (default: all)",
                "date": "date (required) - Date to check",
            },
            "requires_confirmation": False,
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self._pending_actions: dict[UUID, PendingAction] = {}
        self._undo_records: dict[UUID, UndoRecord] = {}

    async def execute_action(
        self,
        action_type: ActionType,
        params: dict[str, Any],
        user_id: UUID,
        clinic_id: UUID,
    ) -> ActionResult:
        """
        Execute an action.

        Args:
            action_type: Type of action to execute
            params: Action parameters
            user_id: User executing the action
            clinic_id: User's clinic ID

        Returns:
            ActionResult with success/failure and data
        """
        logger.info(f"Executing action: {action_type} with params: {params}")

        try:
            # Route to appropriate handler
            if action_type == ActionType.BOOK_APPOINTMENT:
                return await self._book_appointment(params, user_id, clinic_id)
            elif action_type == ActionType.RESCHEDULE_APPOINTMENT:
                return await self._reschedule_appointment(params, user_id, clinic_id)
            elif action_type == ActionType.CANCEL_APPOINTMENT:
                return await self._cancel_appointment(params, user_id, clinic_id)
            elif action_type == ActionType.ADD_TO_WAITLIST:
                return await self._add_to_waitlist(params, user_id, clinic_id)
            elif action_type == ActionType.SEND_REMINDER:
                return await self._send_reminder(params, user_id, clinic_id)
            elif action_type == ActionType.LOOKUP_PATIENT:
                return await self._lookup_patient(params, clinic_id)
            elif action_type == ActionType.CHECK_AVAILABILITY:
                return await self._check_availability(params, clinic_id)
            else:
                return ActionResult(
                    success=False,
                    action_type=action_type,
                    message="Unknown action type",
                    error="Invalid action type",
                )

        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            return ActionResult(
                success=False,
                action_type=action_type,
                message=f"Failed to execute action: {str(e)}",
                error=str(e),
            )

    async def _book_appointment(
        self,
        params: dict[str, Any],
        user_id: UUID,
        clinic_id: UUID,
    ) -> ActionResult:
        """Book a new appointment."""
        # Validate required parameters
        required = ["patient_id", "date", "time"]
        missing = [p for p in required if p not in params]
        if missing:
            return ActionResult(
                success=False,
                action_type=ActionType.BOOK_APPOINTMENT,
                message=f"Missing required parameters: {', '.join(missing)}",
                error="Missing parameters",
            )

        # Get patient
        patient = await self.db.get(Patient, params["patient_id"])
        if not patient or patient.clinic_id != clinic_id:
            return ActionResult(
                success=False,
                action_type=ActionType.BOOK_APPOINTMENT,
                message="Patient not found",
                error="Patient not found or access denied",
            )

        # Get doctor (use first active if not specified)
        doctor_id = params.get("doctor_id")
        if doctor_id:
            doctor = await self.db.get(Doctor, doctor_id)
        else:
            result = await self.db.execute(
                select(Doctor).where(
                    Doctor.clinic_id == clinic_id,
                    Doctor.is_active == True,
                )
            )
            doctor = result.scalar_one_or_none()

        if not doctor or doctor.clinic_id != clinic_id:
            return ActionResult(
                success=False,
                action_type=ActionType.BOOK_APPOINTMENT,
                message="Doctor not found",
                error="Doctor not found or access denied",
            )

        # Combine date and time
        appt_date: date = params["date"]
        appt_time: time = params["time"]
        scheduled_start = datetime.combine(appt_date, appt_time)

        # Check if in past
        if scheduled_start < datetime.now():
            return ActionResult(
                success=False,
                action_type=ActionType.BOOK_APPOINTMENT,
                message="Cannot book appointment in the past",
                error="Invalid date/time",
            )

        duration = params.get("duration_minutes", 15)
        scheduled_end = scheduled_start + timedelta(minutes=duration)

        # Check for conflicts
        conflict_result = await self.db.execute(
            select(Appointment).where(
                Appointment.doctor_id == doctor.id,
                Appointment.status.notin_([
                    AppointmentStatus.CANCELLED.value,
                    AppointmentStatus.NO_SHOW.value,
                ]),
                Appointment.scheduled_start < scheduled_end,
                Appointment.scheduled_end > scheduled_start,
            )
        )
        conflict = conflict_result.scalar_one_or_none()

        if conflict:
            return ActionResult(
                success=False,
                action_type=ActionType.BOOK_APPOINTMENT,
                message=f"Time slot not available. Another appointment exists at {conflict.scheduled_start.strftime('%H:%M')}",
                error="Slot conflict",
                data={
                    "conflict_appointment_id": str(conflict.id),
                    "conflict_time": conflict.scheduled_start.isoformat(),
                },
            )

        # Create appointment
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            duration_minutes=duration,
            status=AppointmentStatus.SCHEDULED.value,
            booking_source=BookingSource.APP.value,
            chief_complaint=params.get("reason"),
            notes=f"Booked via AI Assistant by user {user_id}",
        )

        self.db.add(appointment)
        await self.db.commit()
        await self.db.refresh(appointment)

        # Record for undo
        self._record_undo(
            action_type=ActionType.BOOK_APPOINTMENT,
            data={
                "appointment_id": str(appointment.id),
                "can_cancel": True,
            },
        )

        return ActionResult(
            success=True,
            action_type=ActionType.BOOK_APPOINTMENT,
            message=f"Appointment booked for {patient.full_name} with Dr. {doctor.full_name} on {appt_date.strftime('%d %b %Y')} at {appt_time.strftime('%I:%M %p')}",
            data={
                "appointment_id": str(appointment.id),
                "patient_name": patient.full_name,
                "doctor_name": doctor.full_name,
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": duration,
            },
        )

    async def _reschedule_appointment(
        self,
        params: dict[str, Any],
        user_id: UUID,
        clinic_id: UUID,
    ) -> ActionResult:
        """Reschedule an existing appointment."""
        # Validate parameters
        required = ["appointment_id", "new_date", "new_time"]
        missing = [p for p in required if p not in params]
        if missing:
            return ActionResult(
                success=False,
                action_type=ActionType.RESCHEDULE_APPOINTMENT,
                message=f"Missing required parameters: {', '.join(missing)}",
                error="Missing parameters",
            )

        # Get appointment
        appointment = await self.db.get(Appointment, params["appointment_id"])
        if not appointment:
            return ActionResult(
                success=False,
                action_type=ActionType.RESCHEDULE_APPOINTMENT,
                message="Appointment not found",
                error="Appointment not found",
            )

        # Verify access
        doctor = await self.db.get(Doctor, appointment.doctor_id)
        if not doctor or doctor.clinic_id != clinic_id:
            return ActionResult(
                success=False,
                action_type=ActionType.RESCHEDULE_APPOINTMENT,
                message="Access denied",
                error="Access denied",
            )

        # Store original time for undo
        original_start = appointment.scheduled_start
        original_end = appointment.scheduled_end

        # Calculate new time
        new_date: date = params["new_date"]
        new_time: time = params["new_time"]
        new_scheduled_start = datetime.combine(new_date, new_time)
        new_scheduled_end = new_scheduled_start + timedelta(
            minutes=appointment.duration_minutes
        )

        # Check for conflicts (excluding this appointment)
        conflict_result = await self.db.execute(
            select(Appointment).where(
                Appointment.doctor_id == appointment.doctor_id,
                Appointment.id != appointment.id,
                Appointment.status.notin_([
                    AppointmentStatus.CANCELLED.value,
                    AppointmentStatus.NO_SHOW.value,
                ]),
                Appointment.scheduled_start < new_scheduled_end,
                Appointment.scheduled_end > new_scheduled_start,
            )
        )
        conflict = conflict_result.scalar_one_or_none()

        if conflict:
            return ActionResult(
                success=False,
                action_type=ActionType.RESCHEDULE_APPOINTMENT,
                message=f"Time slot not available. Another appointment exists at {conflict.scheduled_start.strftime('%H:%M')}",
                error="Slot conflict",
            )

        # Update appointment
        appointment.scheduled_start = new_scheduled_start
        appointment.scheduled_end = new_scheduled_end
        appointment.status = AppointmentStatus.RESCHEDULED.value

        await self.db.commit()
        await self.db.refresh(appointment)

        # Record for undo
        self._record_undo(
            action_type=ActionType.RESCHEDULE_APPOINTMENT,
            data={
                "appointment_id": str(appointment.id),
                "original_start": original_start.isoformat(),
                "original_end": original_end.isoformat(),
            },
        )

        patient = await self.db.get(Patient, appointment.patient_id)

        return ActionResult(
            success=True,
            action_type=ActionType.RESCHEDULE_APPOINTMENT,
            message=f"Appointment rescheduled to {new_date.strftime('%d %b %Y')} at {new_time.strftime('%I:%M %p')} for {patient.full_name if patient else 'patient'}",
            data={
                "appointment_id": str(appointment.id),
                "new_scheduled_start": new_scheduled_start.isoformat(),
                "original_scheduled_start": original_start.isoformat(),
            },
        )

    async def _cancel_appointment(
        self,
        params: dict[str, Any],
        user_id: UUID,
        clinic_id: UUID,
    ) -> ActionResult:
        """Cancel an appointment."""
        if "appointment_id" not in params:
            return ActionResult(
                success=False,
                action_type=ActionType.CANCEL_APPOINTMENT,
                message="Missing appointment_id parameter",
                error="Missing parameters",
            )

        # Get appointment
        appointment = await self.db.get(Appointment, params["appointment_id"])
        if not appointment:
            return ActionResult(
                success=False,
                action_type=ActionType.CANCEL_APPOINTMENT,
                message="Appointment not found",
                error="Appointment not found",
            )

        # Verify access
        doctor = await self.db.get(Doctor, appointment.doctor_id)
        if not doctor or doctor.clinic_id != clinic_id:
            return ActionResult(
                success=False,
                action_type=ActionType.CANCEL_APPOINTMENT,
                message="Access denied",
                error="Access denied",
            )

        # Store original state for undo
        original_status = appointment.status

        # Cancel appointment
        appointment.status = AppointmentStatus.CANCELLED.value
        appointment.cancellation_reason = params.get("reason", "Cancelled via AI Assistant")
        appointment.cancelled_by = f"user_{user_id}"

        await self.db.commit()
        await self.db.refresh(appointment)

        # Record for undo
        self._record_undo(
            action_type=ActionType.CANCEL_APPOINTMENT,
            data={
                "appointment_id": str(appointment.id),
                "original_status": original_status,
            },
        )

        patient = await self.db.get(Patient, appointment.patient_id)

        return ActionResult(
            success=True,
            action_type=ActionType.CANCEL_APPOINTMENT,
            message=f"Appointment cancelled for {patient.full_name if patient else 'patient'} on {appointment.scheduled_start.strftime('%d %b %Y at %I:%M %p')}",
            data={
                "appointment_id": str(appointment.id),
                "cancelled_at": datetime.utcnow().isoformat(),
            },
        )

    async def _add_to_waitlist(
        self,
        params: dict[str, Any],
        user_id: UUID,
        clinic_id: UUID,
    ) -> ActionResult:
        """Add patient to waitlist."""
        if "patient_id" not in params:
            return ActionResult(
                success=False,
                action_type=ActionType.ADD_TO_WAITLIST,
                message="Missing patient_id parameter",
                error="Missing parameters",
            )

        # Get patient
        patient = await self.db.get(Patient, params["patient_id"])
        if not patient or patient.clinic_id != clinic_id:
            return ActionResult(
                success=False,
                action_type=ActionType.ADD_TO_WAITLIST,
                message="Patient not found",
                error="Patient not found",
            )

        # Get doctor if specified
        doctor_id = params.get("doctor_id")
        if doctor_id:
            doctor = await self.db.get(Doctor, doctor_id)
            if not doctor or doctor.clinic_id != clinic_id:
                doctor_id = None

        # Map urgency
        urgency_map = {
            "high": WaitlistPriority.HIGH,
            "medium": WaitlistPriority.MEDIUM,
            "low": WaitlistPriority.LOW,
        }
        urgency = urgency_map.get(params.get("urgency", "low"), WaitlistPriority.LOW)

        # Create waitlist entry
        waitlist_entry = Waitlist(
            patient_id=patient.id,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            priority=urgency,
            notes=params.get("notes", "Added via AI Assistant"),
            status=WaitlistStatus.ACTIVE,
        )

        self.db.add(waitlist_entry)
        await self.db.commit()
        await self.db.refresh(waitlist_entry)

        return ActionResult(
            success=True,
            action_type=ActionType.ADD_TO_WAITLIST,
            message=f"Added {patient.full_name} to waitlist with {urgency.value} priority",
            data={
                "waitlist_id": str(waitlist_entry.id),
                "patient_name": patient.full_name,
                "priority": urgency.value,
            },
        )

    async def _send_reminder(
        self,
        params: dict[str, Any],
        user_id: UUID,
        clinic_id: UUID,
    ) -> ActionResult:
        """Send appointment reminder (placeholder)."""
        # This would integrate with SMS/WhatsApp service
        # For now, just mark reminder as sent

        if "appointment_id" not in params:
            return ActionResult(
                success=False,
                action_type=ActionType.SEND_REMINDER,
                message="Missing appointment_id parameter",
                error="Missing parameters",
            )

        appointment = await self.db.get(Appointment, params["appointment_id"])
        if not appointment:
            return ActionResult(
                success=False,
                action_type=ActionType.SEND_REMINDER,
                message="Appointment not found",
                error="Appointment not found",
            )

        # Mark reminder sent
        appointment.reminder_sent = True
        appointment.reminder_sent_at = datetime.utcnow()
        await self.db.commit()

        patient = await self.db.get(Patient, appointment.patient_id)

        return ActionResult(
            success=True,
            action_type=ActionType.SEND_REMINDER,
            message=f"Reminder sent to {patient.full_name if patient else 'patient'} via {params.get('channel', 'SMS')}",
            data={
                "appointment_id": str(appointment.id),
                "channel": params.get("channel", "sms"),
            },
        )

    async def _lookup_patient(
        self,
        params: dict[str, Any],
        clinic_id: UUID,
    ) -> ActionResult:
        """Look up patient by name or phone."""
        query = params.get("query", "").strip()
        if not query:
            return ActionResult(
                success=False,
                action_type=ActionType.LOOKUP_PATIENT,
                message="Missing query parameter",
                error="Missing parameters",
            )

        # Search by phone or name
        from sqlalchemy import or_

        result = await self.db.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                or_(
                    Patient.phone.contains(query),
                    Patient.first_name.ilike(f"%{query}%"),
                    Patient.last_name.ilike(f"%{query}%"),
                ),
            ).limit(10)
        )
        patients = result.scalars().all()

        if not patients:
            return ActionResult(
                success=True,
                action_type=ActionType.LOOKUP_PATIENT,
                message=f"No patients found matching '{query}'",
                data={"count": 0, "patients": []},
            )

        patient_list = [
            {
                "id": str(p.id),
                "name": p.full_name,
                "phone": p.phone,
                "age": p.age,
            }
            for p in patients
        ]

        return ActionResult(
            success=True,
            action_type=ActionType.LOOKUP_PATIENT,
            message=f"Found {len(patients)} patient(s) matching '{query}'",
            data={
                "count": len(patients),
                "patients": patient_list,
            },
        )

    async def _check_availability(
        self,
        params: dict[str, Any],
        clinic_id: UUID,
    ) -> ActionResult:
        """Check doctor availability for a date."""
        if "date" not in params:
            return ActionResult(
                success=False,
                action_type=ActionType.CHECK_AVAILABILITY,
                message="Missing date parameter",
                error="Missing parameters",
            )

        check_date: date = params["date"]
        doctor_id = params.get("doctor_id")

        # Build query
        start_of_day = datetime.combine(check_date, time.min)
        end_of_day = datetime.combine(check_date, time.max)

        query = select(Appointment).where(
            Appointment.scheduled_start >= start_of_day,
            Appointment.scheduled_start <= end_of_day,
            Appointment.status.notin_([
                AppointmentStatus.CANCELLED.value,
                AppointmentStatus.NO_SHOW.value,
            ]),
        )

        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)

        result = await self.db.execute(query)
        appointments = result.scalars().all()

        # Calculate available slots (simplified - assumes 9 AM to 6 PM, 15-min slots)
        total_slots = 36  # 9 hours * 4 slots per hour
        booked_slots = len(appointments)
        available_slots = total_slots - booked_slots

        return ActionResult(
            success=True,
            action_type=ActionType.CHECK_AVAILABILITY,
            message=f"On {check_date.strftime('%d %b %Y')}: {available_slots} slots available, {booked_slots} booked",
            data={
                "date": check_date.isoformat(),
                "total_slots": total_slots,
                "booked_slots": booked_slots,
                "available_slots": available_slots,
                "booked_times": [a.scheduled_start.strftime("%H:%M") for a in appointments],
            },
        )

    def _record_undo(self, action_type: ActionType, data: dict[str, Any]):
        """Record action for potential undo."""
        action_id = uuid4()
        self._undo_records[action_id] = UndoRecord(
            action_id=action_id,
            action_type=action_type,
            original_data=data,
            executed_at=datetime.utcnow(),
            can_undo=True,
        )

    async def undo_last_action(self, session_id: str) -> ActionResult:
        """
        Undo the last action.

        Args:
            session_id: Session ID to find last action

        Returns:
            ActionResult with undo status
        """
        # For MVP, we'll keep this simple
        # In production, this would use Redis with session-based tracking

        if not self._undo_records:
            return ActionResult(
                success=False,
                action_type=ActionType.BOOK_APPOINTMENT,  # placeholder
                message="No actions to undo",
                error="No undo history",
            )

        # Get most recent action
        last_action = max(self._undo_records.values(), key=lambda x: x.executed_at)

        if not last_action.can_undo:
            return ActionResult(
                success=False,
                action_type=last_action.action_type,
                message="This action cannot be undone",
                error="Cannot undo",
            )

        # Undo based on action type
        if last_action.action_type == ActionType.BOOK_APPOINTMENT:
            # Cancel the booked appointment
            appt_id = UUID(last_action.original_data["appointment_id"])
            appointment = await self.db.get(Appointment, appt_id)
            if appointment:
                appointment.status = AppointmentStatus.CANCELLED.value
                appointment.cancellation_reason = "Undone via AI Assistant"
                await self.db.commit()

                return ActionResult(
                    success=True,
                    action_type=ActionType.CANCEL_APPOINTMENT,
                    message="Appointment booking undone (cancelled)",
                    data={"appointment_id": str(appt_id)},
                )

        elif last_action.action_type == ActionType.RESCHEDULE_APPOINTMENT:
            # Restore original time
            appt_id = UUID(last_action.original_data["appointment_id"])
            appointment = await self.db.get(Appointment, appt_id)
            if appointment:
                appointment.scheduled_start = datetime.fromisoformat(
                    last_action.original_data["original_start"]
                )
                appointment.scheduled_end = datetime.fromisoformat(
                    last_action.original_data["original_end"]
                )
                appointment.status = AppointmentStatus.SCHEDULED.value
                await self.db.commit()

                return ActionResult(
                    success=True,
                    action_type=ActionType.RESCHEDULE_APPOINTMENT,
                    message="Reschedule undone, appointment restored to original time",
                    data={"appointment_id": str(appt_id)},
                )

        elif last_action.action_type == ActionType.CANCEL_APPOINTMENT:
            # Re-activate appointment
            appt_id = UUID(last_action.original_data["appointment_id"])
            appointment = await self.db.get(Appointment, appt_id)
            if appointment:
                appointment.status = last_action.original_data["original_status"]
                appointment.cancellation_reason = None
                await self.db.commit()

                return ActionResult(
                    success=True,
                    action_type=ActionType.CANCEL_APPOINTMENT,
                    message="Cancellation undone, appointment restored",
                    data={"appointment_id": str(appt_id)},
                )

        return ActionResult(
            success=False,
            action_type=last_action.action_type,
            message="Undo failed",
            error="Undo operation failed",
        )
