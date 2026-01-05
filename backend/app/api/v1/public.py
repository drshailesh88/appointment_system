"""
Public API endpoints for patient booking portal.

These endpoints are accessible without authentication.
"""

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, BookingSource
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.public import (
    OTPSendRequest,
    OTPSendResponse,
    OTPVerifyRequest,
    OTPVerifyResponse,
    PublicAppointmentResponse,
    PublicBookingRequest,
    PublicCancelRequest,
    PublicDoctorDetail,
    PublicDoctorListItem,
    PublicSlot,
    PublicSlotsResponse,
)
from app.services.otp_service import OTPService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def get_patient_from_token(
    authorization: str = Header(None),
    db: DbSession = None,
) -> str:
    """
    Dependency to get patient phone from OTP token.

    Args:
        authorization: Bearer token from header
        db: Database session

    Returns:
        str: Phone number

    Raises:
        HTTPException: If token is invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization.split(" ")[1]
    phone = OTPService.decode_token(token)

    if not phone:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return phone


# OTP Endpoints
@router.post("/otp/send", response_model=OTPSendResponse)
@limiter.limit("5/minute")  # Strict rate limit for OTP to prevent abuse
async def send_otp(
    request: Request,
    body: OTPSendRequest,
    db: DbSession,
) -> dict:
    """Send OTP to phone number."""
    otp_service = OTPService(db)
    otp = await otp_service.send_otp(body.phone)

    return {
        "message": "OTP sent successfully",
        "expires_in_seconds": OTPService.OTP_EXPIRY_MINUTES * 60,
    }


@router.post("/otp/verify", response_model=OTPVerifyResponse)
@limiter.limit("10/minute")  # Rate limit OTP verification
async def verify_otp(
    request: Request,
    body: OTPVerifyRequest,
    db: DbSession,
) -> dict:
    """Verify OTP and get access token."""
    otp_service = OTPService(db)
    token = await otp_service.verify_otp(body.phone, body.otp_code)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP",
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_seconds": OTPService.TOKEN_EXPIRY_HOURS * 3600,
    }


# Doctor Endpoints
@router.get("/doctors", response_model=list[PublicDoctorListItem])
async def list_doctors_public(
    db: DbSession,
    specialization: str | None = None,
    city: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[dict]:
    """List active doctors accepting new patients (public)."""
    query = (
        select(Doctor)
        .options(selectinload(Doctor.clinic))
        .where(Doctor.is_active == True)
        .where(Doctor.accepting_new_patients == True)
    )

    if specialization:
        query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))

    if city:
        query = query.join(Clinic).where(Clinic.city.ilike(f"%{city}%"))

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    doctors = result.scalars().all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "specialization": d.specialization,
            "qualification": d.qualification,
            "experience_years": d.experience_years,
            "consultation_fee": d.consultation_fee,
            "photo_url": d.photo_url,
            "languages": d.languages,
            "clinic_name": d.clinic.name if d.clinic else None,
            "clinic_address": d.clinic.address if d.clinic else None,
        }
        for d in doctors
    ]


@router.get("/doctors/{doctor_id}", response_model=PublicDoctorDetail)
async def get_doctor_public(
    db: DbSession,
    doctor_id: UUID,
) -> dict:
    """Get doctor details (public)."""
    result = await db.execute(
        select(Doctor)
        .options(selectinload(Doctor.clinic))
        .where(Doctor.id == doctor_id)
        .where(Doctor.is_active == True)
    )
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    return {
        "id": doctor.id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "consultation_fee": doctor.consultation_fee,
        "photo_url": doctor.photo_url,
        "languages": doctor.languages,
        "clinic_name": doctor.clinic.name if doctor.clinic else None,
        "clinic_address": doctor.clinic.address if doctor.clinic else None,
        "bio": doctor.bio,
        "registration_number": doctor.registration_number,
        "slot_duration": doctor.slot_duration,
        "working_hours": doctor.working_hours,
    }


# Slot Availability Endpoint
@router.get("/doctors/{doctor_id}/slots", response_model=PublicSlotsResponse)
async def get_doctor_slots(
    db: DbSession,
    doctor_id: UUID,
    date_param: date,
) -> dict:
    """Get available slots for a doctor on a specific date."""
    # Get doctor
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Get day of week
    day_name = date_param.strftime("%A").lower()
    working_hours = doctor.working_hours or {}
    day_schedule = working_hours.get(day_name)

    if not day_schedule:
        return {
            "doctor_id": doctor_id,
            "date": date_param,
            "slots": [],
        }

    # Get existing appointments
    start = datetime.combine(date_param, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(date_param, time.max).replace(tzinfo=timezone.utc)

    existing_result = await db.execute(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
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
    slot_duration = doctor.slot_duration

    for period in day_schedule:
        period_start = datetime.strptime(period["start"], "%H:%M").time()
        period_end = datetime.strptime(period["end"], "%H:%M").time()

        current = datetime.combine(date_param, period_start)
        end_dt = datetime.combine(date_param, period_end)

        while current + timedelta(minutes=slot_duration) <= end_dt:
            slot_end = current + timedelta(minutes=slot_duration)
            is_available = current not in booked_times

            # Don't show past slots for today
            if date_param == date.today():
                now = datetime.now()
                if current < now:
                    is_available = False

            slots.append(PublicSlot(
                start_time=current.replace(tzinfo=timezone.utc),
                end_time=slot_end.replace(tzinfo=timezone.utc),
                is_available=is_available,
            ))

            current = slot_end

    return {
        "doctor_id": doctor_id,
        "date": date_param,
        "slots": slots,
    }


# Appointment Booking Endpoints (require OTP token)
@router.post("/appointments", response_model=PublicAppointmentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")  # Rate limit appointment booking
async def book_appointment_public(
    request: Request,
    db: DbSession,
    booking: PublicBookingRequest,
    phone: str = Depends(get_patient_from_token),
) -> dict:
    """
    Book an appointment (requires OTP token).

    Creates patient record if new.
    """
    # Verify doctor exists
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.id == booking.doctor_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Find or create patient
    patient_result = await db.execute(
        select(Patient).where(Patient.phone == phone)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        # Create new patient
        patient = Patient(
            first_name=booking.first_name,
            last_name=booking.last_name,
            phone=phone,
            email=booking.email,
            date_of_birth=booking.date_of_birth,
            gender=booking.gender,
            clinic_id=doctor.clinic_id,
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

    # Calculate end time
    scheduled_end = booking.scheduled_start + timedelta(
        minutes=booking.duration_minutes
    )

    # Check for conflicts
    conflict_result = await db.execute(
        select(Appointment).where(
            Appointment.doctor_id == booking.doctor_id,
            Appointment.status.notin_([
                AppointmentStatus.CANCELLED.value,
                AppointmentStatus.NO_SHOW.value,
            ]),
            Appointment.scheduled_start < scheduled_end,
            Appointment.scheduled_end > booking.scheduled_start,
        )
    )
    conflict = conflict_result.scalar_one_or_none()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot already booked",
        )

    # Create appointment
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=booking.doctor_id,
        scheduled_start=booking.scheduled_start,
        scheduled_end=scheduled_end,
        duration_minutes=booking.duration_minutes,
        appointment_type=AppointmentType.CONSULTATION.value,
        booking_source=BookingSource.ONLINE_PORTAL.value,
        chief_complaint=booking.chief_complaint,
        notes=booking.notes,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    # TODO: Send SMS confirmation

    return {
        "id": appointment.id,
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor.name,
        "scheduled_start": appointment.scheduled_start,
        "duration_minutes": appointment.duration_minutes,
        "status": appointment.status,
        "appointment_type": appointment.appointment_type,
        "token_number": appointment.token_number,
        "chief_complaint": appointment.chief_complaint,
        "patient_name": patient.full_name,
    }


@router.get("/appointments", response_model=list[PublicAppointmentResponse])
async def get_patient_appointments(
    db: DbSession,
    phone: str = Depends(get_patient_from_token),
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[dict]:
    """Get appointments for the authenticated patient."""
    # Find patient
    patient_result = await db.execute(
        select(Patient).where(Patient.phone == phone)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        return []

    # Get appointments
    query = (
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.patient_id == patient.id)
    )

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
            "id": a.id,
            "doctor_id": a.doctor_id,
            "doctor_name": a.doctor.name if a.doctor else "Unknown",
            "scheduled_start": a.scheduled_start,
            "duration_minutes": a.duration_minutes,
            "status": a.status,
            "appointment_type": a.appointment_type,
            "token_number": a.token_number,
            "chief_complaint": a.chief_complaint,
            "patient_name": patient.full_name,
        }
        for a in appointments
    ]


@router.get("/appointments/{appointment_id}", response_model=PublicAppointmentResponse)
async def get_appointment_detail(
    db: DbSession,
    appointment_id: UUID,
    phone: str = Depends(get_patient_from_token),
) -> dict:
    """Get appointment details (patient must own the appointment)."""
    # Find patient
    patient_result = await db.execute(
        select(Patient).where(Patient.phone == phone)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Get appointment
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.id == appointment_id)
        .where(Appointment.patient_id == patient.id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return {
        "id": appointment.id,
        "doctor_id": appointment.doctor_id,
        "doctor_name": appointment.doctor.name if appointment.doctor else "Unknown",
        "scheduled_start": appointment.scheduled_start,
        "duration_minutes": appointment.duration_minutes,
        "status": appointment.status,
        "appointment_type": appointment.appointment_type,
        "token_number": appointment.token_number,
        "chief_complaint": appointment.chief_complaint,
        "patient_name": patient.full_name,
    }


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_200_OK)
async def cancel_appointment_public(
    db: DbSession,
    appointment_id: UUID,
    cancel_request: PublicCancelRequest,
    phone: str = Depends(get_patient_from_token),
) -> dict:
    """Cancel an appointment (patient must own it)."""
    # Find patient
    patient_result = await db.execute(
        select(Patient).where(Patient.phone == phone)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Get appointment
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .where(Appointment.patient_id == patient.id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # Check if already cancelled or completed
    if appointment.status in [
        AppointmentStatus.CANCELLED.value,
        AppointmentStatus.COMPLETED.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel appointment with status: {appointment.status}",
        )

    # Cancel appointment
    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.cancellation_reason = cancel_request.reason
    appointment.cancelled_by = patient.full_name

    await db.commit()

    # TODO: Send SMS cancellation confirmation

    return {
        "message": "Appointment cancelled successfully",
        "appointment_id": appointment.id,
    }
