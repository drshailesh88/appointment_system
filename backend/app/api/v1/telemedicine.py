"""
Telemedicine API endpoints for video consultations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.appointment import Appointment
from app.models.consultation import Consultation, ConsultationStatus, ParticipantRole
from app.models.doctor import Doctor
from app.models.user import UserRole
from app.schemas.consultation import (
    ConnectionQualityUpdate,
    ConsultationCreate,
    ConsultationEndRequest,
    ConsultationResponse,
    DoctorQueueResponse,
    JoinRoomResponse,
    RatingRequest,
    RecordingConsentRequest,
    RecordingConsentResponse,
    WaitingRoomJoinResponse,
    WaitingRoomStatus,
)
from app.services.telemedicine import TelemedicineService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/consultations",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consultation(
    db: DbSession,
    current_user: CurrentUser,
    consultation_in: ConsultationCreate,
) -> Consultation:
    """
    Create a video consultation for an appointment.

    Creates a Jitsi room and prepares consultation session.
    """
    # Verify appointment exists
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.id == consultation_in.appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # Check access
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != appointment.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    service = TelemedicineService(db)

    try:
        consultation = await service.create_consultation(
            appointment_id=consultation_in.appointment_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return consultation


@router.get(
    "/consultations/{consultation_id}",
    response_model=ConsultationResponse,
)
async def get_consultation(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
) -> Consultation:
    """Get consultation details."""
    result = await db.execute(
        select(Consultation)
        .options(
            selectinload(Consultation.participants),
            selectinload(Consultation.recording),
            selectinload(Consultation.appointment),
        )
        .where(Consultation.id == consultation_id)
    )
    consultation = result.scalar_one_or_none()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    # Check access (verify user is part of this consultation's clinic)
    appointment_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.id == consultation.appointment_id)
    )
    appointment = appointment_result.scalar_one_or_none()

    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.clinic_id != appointment.doctor.clinic_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return consultation


@router.post(
    "/consultations/{consultation_id}/waiting-room/join",
    response_model=WaitingRoomJoinResponse,
)
async def join_waiting_room(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
    device_type: str | None = None,
    connection_type: str | None = None,
) -> WaitingRoomJoinResponse:
    """
    Patient joins the waiting room.

    Patient will wait here until doctor admits them to the consultation.
    """
    service = TelemedicineService(db)

    try:
        response = await service.join_waiting_room(
            consultation_id=consultation_id,
            user_id=current_user.id,
            device_type=device_type,
            connection_type=connection_type,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return response


@router.get(
    "/consultations/{consultation_id}/waiting-room/status",
    response_model=WaitingRoomStatus,
)
async def get_waiting_room_status(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
) -> WaitingRoomStatus:
    """
    Get current waiting room status.

    Returns queue position and estimated wait time.
    """
    service = TelemedicineService(db)

    try:
        status_info = await service.get_waiting_room_status(consultation_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return status_info


@router.post(
    "/consultations/{consultation_id}/admit",
    response_model=JoinRoomResponse,
)
async def admit_patient(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
) -> JoinRoomResponse:
    """
    Doctor admits patient from waiting room.

    Transitions consultation to IN_PROGRESS and provides room access.
    """
    # Verify user is a doctor
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.user_id == current_user.id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can admit patients",
        )

    service = TelemedicineService(db)

    try:
        response = await service.doctor_admits_patient(
            consultation_id=consultation_id,
            doctor_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return response


@router.post(
    "/consultations/{consultation_id}/join",
    response_model=JoinRoomResponse,
)
async def join_consultation(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
) -> JoinRoomResponse:
    """
    Join an active consultation.

    Returns room URL and JWT token to join the video call.
    Patient can only join after doctor has admitted them.
    """
    service = TelemedicineService(db)

    # Determine if user is doctor or patient
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.user_id == current_user.id)
    )
    is_doctor = doctor_result.scalar_one_or_none() is not None

    if is_doctor:
        # Doctor can join/rejoin anytime
        try:
            response = await service.doctor_admits_patient(
                consultation_id=consultation_id,
                doctor_id=current_user.id,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    else:
        # Patient joins after admission
        try:
            response = await service.patient_join_consultation(
                consultation_id=consultation_id,
                user_id=current_user.id,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    return response


@router.post(
    "/consultations/{consultation_id}/end",
    response_model=ConsultationResponse,
)
async def end_consultation(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
    end_request: ConsultationEndRequest | None = None,
) -> Consultation:
    """
    End the consultation.

    Either doctor or patient can end the call. Duration is automatically calculated.
    """
    service = TelemedicineService(db)

    try:
        consultation = await service.end_consultation(
            consultation_id=consultation_id,
            notes=end_request.notes if end_request else None,
            connection_quality=(
                end_request.connection_quality if end_request else None
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    logger.info(
        f"User {current_user.id} ended consultation {consultation_id}"
    )
    return consultation


@router.post(
    "/consultations/{consultation_id}/recording/consent",
    response_model=RecordingConsentResponse,
)
async def submit_recording_consent(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
    consent_request: RecordingConsentRequest,
) -> RecordingConsentResponse:
    """
    Submit consent for recording the consultation.

    Both doctor and patient must consent before recording can start.
    """
    # Determine user role
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.user_id == current_user.id)
    )
    is_doctor = doctor_result.scalar_one_or_none() is not None
    role = ParticipantRole.DOCTOR if is_doctor else ParticipantRole.PATIENT

    service = TelemedicineService(db)

    try:
        can_start, timestamp = await service.submit_recording_consent(
            consultation_id=consultation_id,
            user_id=current_user.id,
            role=role,
            consent=consent_request.consent,
            consent_text=consent_request.consent_text,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return RecordingConsentResponse(
        consultation_id=consultation_id,
        user_role=role,
        consent_given=consent_request.consent,
        consent_timestamp=timestamp,
        can_start_recording=can_start,
    )


@router.post(
    "/consultations/{consultation_id}/recording/start",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_recording(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
) -> dict:
    """
    Start recording the consultation.

    Requires both parties to have consented. This would typically trigger
    Jibri recording via Jitsi API.
    """
    # TODO: Implement Jibri integration for actual recording
    # For now, just verify consent exists

    result = await db.execute(
        select(Consultation)
        .options(selectinload(Consultation.recording))
        .where(Consultation.id == consultation_id)
    )
    consultation = result.scalar_one_or_none()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    if not consultation.recording or not consultation.recording.has_full_consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recording requires consent from both doctor and patient",
        )

    logger.info(f"Starting recording for consultation {consultation_id}")

    return {
        "message": "Recording started",
        "consultation_id": consultation_id,
        "note": "Jibri integration required for actual recording",
    }


@router.post(
    "/consultations/{consultation_id}/rating",
    response_model=ConsultationResponse,
)
async def submit_rating(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
    rating_request: RatingRequest,
) -> Consultation:
    """
    Submit post-consultation rating.

    Both doctor and patient can rate their experience (1-5 stars).
    """
    # Determine user role
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.user_id == current_user.id)
    )
    is_doctor = doctor_result.scalar_one_or_none() is not None
    role = ParticipantRole.DOCTOR if is_doctor else ParticipantRole.PATIENT

    service = TelemedicineService(db)

    try:
        consultation = await service.submit_rating(
            consultation_id=consultation_id,
            user_id=current_user.id,
            role=role,
            rating=rating_request.rating,
            feedback=rating_request.feedback,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return consultation


@router.get(
    "/consultations/queue",
    response_model=DoctorQueueResponse,
)
async def get_doctor_queue(
    db: DbSession,
    current_user: CurrentUser,
) -> DoctorQueueResponse:
    """
    Get doctor's waiting room queue.

    Returns list of patients waiting to be admitted to consultations.
    Only accessible by doctors.
    """
    # Verify user is a doctor
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.user_id == current_user.id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can view their queue",
        )

    service = TelemedicineService(db)
    queue = await service.get_doctor_queue(current_user.id)

    return DoctorQueueResponse(
        doctor_id=current_user.id,
        queue=queue,
        total_waiting=len(queue),
    )


@router.post(
    "/consultations/{consultation_id}/connection-quality",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_connection_quality(
    db: DbSession,
    current_user: CurrentUser,
    consultation_id: UUID,
    quality_update: ConnectionQualityUpdate,
) -> None:
    """
    Update connection quality metrics.

    Can be called periodically during consultation to track network quality.
    """
    result = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consultation = result.scalar_one_or_none()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    consultation.connection_quality = quality_update.quality.value

    # Update participant's connection info
    if quality_update.device_type or quality_update.connection_type:
        from app.models.consultation import ConsultationParticipant

        participant_result = await db.execute(
            select(ConsultationParticipant).where(
                ConsultationParticipant.consultation_id == consultation_id,
                ConsultationParticipant.user_id == current_user.id,
            )
        )
        participant = participant_result.scalar_one_or_none()

        if participant:
            if quality_update.device_type:
                participant.device_type = quality_update.device_type
            if quality_update.connection_type:
                participant.connection_type = quality_update.connection_type.value

    await db.commit()
    logger.debug(
        f"Updated connection quality for consultation {consultation_id}: "
        f"{quality_update.quality.value}"
    )
