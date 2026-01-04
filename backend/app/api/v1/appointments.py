"""
Appointments API endpoints.
"""

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.appointment import (
    AppointmentCheckIn,
    AppointmentComplete,
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentSlot,
    AppointmentUpdate,
    DailySchedule,
    RescheduleRequest,
    SlotAvailabilityRequest,
    SlotAvailabilityResponse,
)
from app.services.calendar_sync import CalendarSyncService

router = APIRouter()


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    db: DbSession,
    current_user: CurrentUser,
    appointment_in: AppointmentCreate,
) -> Appointment:
    """Create a new appointment."""
    # Verify doctor exists and get clinic_id
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.id == appointment_in.doctor_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Verify patient exists and belongs to same clinic
    patient_result = await db.execute(
        select(Patient).where(Patient.id == appointment_in.patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if patient.clinic_id != doctor.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient and doctor must belong to the same clinic",
        )

    # Calculate end time
    scheduled_end = appointment_in.scheduled_start + timedelta(
        minutes=appointment_in.duration_minutes
    )

    # Check for conflicts
    conflict_result = await db.execute(
        select(Appointment).where(
            Appointment.doctor_id == appointment_in.doctor_id,
            Appointment.status.notin_([
                AppointmentStatus.CANCELLED.value,
                AppointmentStatus.NO_SHOW.value,
            ]),
            # Overlapping time check
            Appointment.scheduled_start < scheduled_end,
            Appointment.scheduled_end > appointment_in.scheduled_start,
        )
    )
    conflict = conflict_result.scalar_one_or_none()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot already booked",
        )

    appointment = Appointment(
        patient_id=appointment_in.patient_id,
        doctor_id=appointment_in.doctor_id,
        scheduled_start=appointment_in.scheduled_start,
        scheduled_end=scheduled_end,
        duration_minutes=appointment_in.duration_minutes,
        appointment_type=appointment_in.appointment_type.value,
        booking_source=appointment_in.booking_source.value,
        chief_complaint=appointment_in.chief_complaint,
        notes=appointment_in.notes,
        service_id=appointment_in.service_id,
        voice_booking_metadata=appointment_in.voice_booking_metadata,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    # Sync to Google Calendar (async, non-blocking)
    calendar_service = CalendarSyncService(db)
    try:
        await calendar_service.sync_appointment(appointment)
    except Exception as e:
        # Log but don't fail the appointment creation
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to sync appointment to calendar: {e}")

    return appointment


@router.get("/", response_model=list[AppointmentListResponse])
async def list_appointments(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: UUID | None = None,
    patient_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List appointments with filters."""
    query = (
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
    )

    # Filter by clinic access
    if current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.join(Doctor).where(Doctor.clinic_id == current_user.clinic_id)

    if doctor_id:
        query = query.where(Appointment.doctor_id == doctor_id)

    if patient_id:
        query = query.where(Appointment.patient_id == patient_id)

    if date_from:
        start = datetime.combine(date_from, time.min).replace(tzinfo=timezone.utc)
        query = query.where(Appointment.scheduled_start >= start)

    if date_to:
        end = datetime.combine(date_to, time.max).replace(tzinfo=timezone.utc)
        query = query.where(Appointment.scheduled_start <= end)

    if status_filter:
        query = query.where(Appointment.status == status_filter)

    query = (
        query.order_by(Appointment.scheduled_start.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    appointments = result.scalars().all()

    return [
        {
            **{
                "id": a.id,
                "patient_id": a.patient_id,
                "doctor_id": a.doctor_id,
                "scheduled_start": a.scheduled_start,
                "duration_minutes": a.duration_minutes,
                "status": a.status,
                "appointment_type": a.appointment_type,
                "token_number": a.token_number,
                "chief_complaint": a.chief_complaint,
            },
            "patient_name": a.patient.full_name if a.patient else "Unknown",
            "doctor_name": a.doctor.name if a.doctor else "Unknown",
        }
        for a in appointments
    ]


@router.get("/today", response_model=list[AppointmentListResponse])
async def get_today_appointments(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: UUID | None = None,
) -> list[dict]:
    """Get today's appointments."""
    today = date.today()
    start = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(today, time.max).replace(tzinfo=timezone.utc)

    query = (
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
        .where(Appointment.scheduled_start >= start)
        .where(Appointment.scheduled_start <= end)
    )

    if current_user.role != UserRole.ADMIN.value and current_user.clinic_id:
        query = query.join(Doctor).where(Doctor.clinic_id == current_user.clinic_id)

    if doctor_id:
        query = query.where(Appointment.doctor_id == doctor_id)

    query = query.order_by(Appointment.scheduled_start)
    result = await db.execute(query)
    appointments = result.scalars().all()

    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "patient_name": a.patient.full_name if a.patient else "Unknown",
            "doctor_id": a.doctor_id,
            "doctor_name": a.doctor.name if a.doctor else "Unknown",
            "scheduled_start": a.scheduled_start,
            "duration_minutes": a.duration_minutes,
            "status": a.status,
            "appointment_type": a.appointment_type,
            "token_number": a.token_number,
            "chief_complaint": a.chief_complaint,
        }
        for a in appointments
    ]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    db: DbSession,
    current_user: CurrentUser,
    appointment_id: UUID,
) -> Appointment:
    """Get a specific appointment."""
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    db: DbSession,
    current_user: CurrentUser,
    appointment_id: UUID,
    appointment_in: AppointmentUpdate,
) -> Appointment:
    """Update an appointment."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    update_data = appointment_in.model_dump(exclude_unset=True)

    # If rescheduling, update end time
    if "scheduled_start" in update_data:
        duration = update_data.get("duration_minutes", appointment.duration_minutes)
        update_data["scheduled_end"] = update_data["scheduled_start"] + timedelta(
            minutes=duration
        )

    for field, value in update_data.items():
        if field == "status" and value:
            setattr(appointment, field, value.value)
        else:
            setattr(appointment, field, value)

    await db.commit()
    await db.refresh(appointment)

    # Sync to Google Calendar (async, non-blocking)
    calendar_service = CalendarSyncService(db)
    try:
        await calendar_service.sync_appointment(appointment, force=True)
    except Exception as e:
        # Log but don't fail the appointment update
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to sync appointment to calendar: {e}")

    return appointment


@router.post("/{appointment_id}/check-in", response_model=AppointmentResponse)
async def check_in_patient(
    db: DbSession,
    current_user: CurrentUser,
    appointment_id: UUID,
    check_in_data: AppointmentCheckIn | None = None,
) -> Appointment:
    """Check in a patient for their appointment."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status != AppointmentStatus.SCHEDULED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in appointment with status: {appointment.status}",
        )

    appointment.status = AppointmentStatus.CHECKED_IN.value
    appointment.check_in_time = datetime.now(timezone.utc)

    if check_in_data and check_in_data.token_number:
        appointment.token_number = check_in_data.token_number
    else:
        # Auto-generate token number for the day
        today = date.today()
        start = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)
        end = datetime.combine(today, time.max).replace(tzinfo=timezone.utc)

        max_token_result = await db.execute(
            select(func.max(Appointment.token_number)).where(
                Appointment.doctor_id == appointment.doctor_id,
                Appointment.scheduled_start >= start,
                Appointment.scheduled_start <= end,
            )
        )
        max_token = max_token_result.scalar() or 0
        appointment.token_number = max_token + 1

    await db.commit()
    await db.refresh(appointment)

    return appointment


@router.post("/{appointment_id}/start", response_model=AppointmentResponse)
async def start_consultation(
    db: DbSession,
    current_user: CurrentUser,
    appointment_id: UUID,
) -> Appointment:
    """Start the consultation."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status != AppointmentStatus.CHECKED_IN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient must be checked in first",
        )

    appointment.status = AppointmentStatus.IN_PROGRESS.value
    appointment.start_time = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(appointment)

    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_consultation(
    db: DbSession,
    current_user: CurrentUser,
    appointment_id: UUID,
    complete_data: AppointmentComplete | None = None,
) -> Appointment:
    """Complete the consultation."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status != AppointmentStatus.IN_PROGRESS.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consultation must be in progress",
        )

    appointment.status = AppointmentStatus.COMPLETED.value
    appointment.end_time = datetime.now(timezone.utc)

    if complete_data:
        if complete_data.notes:
            appointment.notes = complete_data.notes
        if complete_data.emr_visit_id:
            appointment.emr_visit_id = complete_data.emr_visit_id

    await db.commit()
    await db.refresh(appointment)

    return appointment


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    db: DbSession,
    current_user: CurrentUser,
    appointment_id: UUID,
    reason: str | None = None,
) -> Appointment:
    """Cancel an appointment."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status in [
        AppointmentStatus.COMPLETED.value,
        AppointmentStatus.CANCELLED.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment with status: {appointment.status}",
        )

    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.cancellation_reason = reason
    appointment.cancelled_by = current_user.name

    await db.commit()
    await db.refresh(appointment)

    return appointment


@router.post("/{appointment_id}/no-show", response_model=AppointmentResponse)
async def mark_no_show(
    db: DbSession,
    current_user: CurrentUser,
    appointment_id: UUID,
) -> Appointment:
    """Mark patient as no-show."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    appointment.status = AppointmentStatus.NO_SHOW.value

    await db.commit()
    await db.refresh(appointment)

    return appointment


@router.post("/slots/availability", response_model=SlotAvailabilityResponse)
async def get_slot_availability(
    db: DbSession,
    request: SlotAvailabilityRequest,
) -> dict:
    """Get available slots for a doctor on a specific date."""
    # Get doctor's working hours
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.id == request.doctor_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Get day of week
    day_name = request.date.strftime("%A").lower()
    working_hours = doctor.working_hours or {}
    day_schedule = working_hours.get(day_name)

    if not day_schedule:
        return {
            "doctor_id": request.doctor_id,
            "date": request.date,
            "slots": [],
        }

    # Get existing appointments for the day
    start = datetime.combine(request.date, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(request.date, time.max).replace(tzinfo=timezone.utc)

    existing_result = await db.execute(
        select(Appointment).where(
            Appointment.doctor_id == request.doctor_id,
            Appointment.scheduled_start >= start,
            Appointment.scheduled_start <= end,
            Appointment.status.notin_([
                AppointmentStatus.CANCELLED.value,
                AppointmentStatus.NO_SHOW.value,
            ]),
        )
    )
    existing_appointments = existing_result.scalars().all()

    # Build booked times
    booked_times = set()
    for appt in existing_appointments:
        booked_times.add(appt.scheduled_start.replace(tzinfo=None))

    # Generate available slots
    slots = []
    slot_duration = request.duration_minutes or doctor.slot_duration

    for period in day_schedule:
        period_start = datetime.strptime(period["start"], "%H:%M").time()
        period_end = datetime.strptime(period["end"], "%H:%M").time()

        current = datetime.combine(request.date, period_start)
        end_dt = datetime.combine(request.date, period_end)

        while current + timedelta(minutes=slot_duration) <= end_dt:
            slot_end = current + timedelta(minutes=slot_duration)
            is_available = current not in booked_times

            # Don't show past slots for today
            if request.date == date.today():
                now = datetime.now()
                if current < now:
                    is_available = False

            slots.append(AppointmentSlot(
                start_time=current.replace(tzinfo=timezone.utc),
                end_time=slot_end.replace(tzinfo=timezone.utc),
                is_available=is_available,
            ))

            current = slot_end

    return {
        "doctor_id": request.doctor_id,
        "date": request.date,
        "slots": slots,
    }


@router.get("/doctor/{doctor_id}/schedule", response_model=DailySchedule)
async def get_doctor_schedule(
    db: DbSession,
    current_user: CurrentUser,
    doctor_id: UUID,
    schedule_date: date | None = None,
) -> dict:
    """Get a doctor's daily schedule."""
    target_date = schedule_date or date.today()

    start = datetime.combine(target_date, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(target_date, time.max).replace(tzinfo=timezone.utc)

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
        .where(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_start >= start,
            Appointment.scheduled_start <= end,
        )
        .order_by(Appointment.scheduled_start)
    )
    appointments = result.scalars().all()

    # Count by status
    completed = sum(1 for a in appointments if a.status == AppointmentStatus.COMPLETED.value)
    cancelled = sum(1 for a in appointments if a.status == AppointmentStatus.CANCELLED.value)
    pending = len(appointments) - completed - cancelled

    return {
        "doctor_id": doctor_id,
        "date": target_date,
        "appointments": [
            {
                "id": a.id,
                "patient_id": a.patient_id,
                "patient_name": a.patient.full_name if a.patient else "Unknown",
                "doctor_id": a.doctor_id,
                "doctor_name": a.doctor.name if a.doctor else "Unknown",
                "scheduled_start": a.scheduled_start,
                "duration_minutes": a.duration_minutes,
                "status": a.status,
                "appointment_type": a.appointment_type,
                "token_number": a.token_number,
                "chief_complaint": a.chief_complaint,
            }
            for a in appointments
        ],
        "total_appointments": len(appointments),
        "completed": completed,
        "pending": pending,
        "cancelled": cancelled,
    }
