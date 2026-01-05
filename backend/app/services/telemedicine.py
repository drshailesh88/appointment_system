"""
Telemedicine Service for video consultations.

Provides:
- JWT-authenticated Jitsi room access
- Virtual waiting room with queue management
- Recording consent and management
- Connection quality tracking
- Post-consultation ratings
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.consultation import (
    ConnectionQuality,
    Consultation,
    ConsultationParticipant,
    ConsultationRecording,
    ConsultationStatus,
    ParticipantRole,
)
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from app.schemas.consultation import (
    DoctorQueueItem,
    JoinRoomResponse,
    WaitingRoomJoinResponse,
    WaitingRoomStatus,
)

logger = logging.getLogger(__name__)


class TelemedicineService:
    """
    Telemedicine service for video consultations.

    Features:
    - Create consultation rooms
    - Generate JWT tokens for Jitsi
    - Manage waiting room queue
    - Handle recording consent
    - Track connection quality
    - Collect ratings
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_consultation(
        self,
        appointment_id: UUID,
    ) -> Consultation:
        """
        Create consultation room for an appointment.

        Args:
            appointment_id: ID of the appointment

        Returns:
            Created consultation

        Raises:
            ValueError: If appointment not found or already has consultation
        """
        # Get appointment
        result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")

        # Check if consultation already exists
        existing = await self.db.execute(
            select(Consultation).where(Consultation.appointment_id == appointment_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Consultation already exists for appointment {appointment_id}")

        # Generate unique room name
        room_name = f"docassist-{appointment_id.hex[:8]}-{secrets.token_hex(4)}"

        consultation = Consultation(
            appointment_id=appointment_id,
            room_name=room_name,
            room_url=f"https://{settings.jitsi_domain}/{room_name}",
            status=ConsultationStatus.SCHEDULED.value,
            scheduled_start=appointment.scheduled_start,
        )

        self.db.add(consultation)
        await self.db.commit()
        await self.db.refresh(consultation)

        logger.info(
            f"Created consultation {consultation.id} for appointment {appointment_id}"
        )
        return consultation

    def generate_jwt_token(
        self,
        consultation: Consultation,
        user_id: UUID,
        user_name: str,
        user_email: str = "",
        is_moderator: bool = False,
        avatar_url: str | None = None,
    ) -> str:
        """
        Generate JWT token for Jitsi room access.

        Args:
            consultation: Consultation to join
            user_id: User ID
            user_name: Display name in video call
            user_email: User email (optional)
            is_moderator: Whether user can control room (doctors are moderators)
            avatar_url: Avatar image URL

        Returns:
            JWT token string
        """
        now = datetime.utcnow()

        payload = {
            "context": {
                "user": {
                    "id": str(user_id),
                    "name": user_name,
                    "avatar": avatar_url or "",
                    "email": user_email,
                    "moderator": str(is_moderator).lower(),
                }
            },
            "aud": "jitsi",
            "iss": settings.jitsi_app_id,
            "sub": settings.jitsi_domain,
            "room": consultation.room_name,
            "iat": now,
            "exp": now + timedelta(hours=2),  # Token valid for 2 hours
            "nbf": now - timedelta(minutes=5),  # Allow 5 min clock skew
        }

        token = jwt.encode(payload, settings.jitsi_jwt_secret, algorithm="HS256")
        logger.debug(f"Generated JWT token for user {user_id} in room {consultation.room_name}")
        return token

    async def join_waiting_room(
        self,
        consultation_id: UUID,
        user_id: UUID,
        device_type: str | None = None,
        connection_type: str | None = None,
    ) -> WaitingRoomJoinResponse:
        """
        Patient joins waiting room.

        Args:
            consultation_id: Consultation ID
            user_id: Patient's user ID
            device_type: Device type (android, ios, web)
            connection_type: Network type (wifi, 4g, etc.)

        Returns:
            Waiting room status with queue position

        Raises:
            ValueError: If consultation not found
        """
        # Get consultation
        result = await self.db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()

        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        # Update consultation status
        consultation.status = ConsultationStatus.WAITING.value
        consultation.patient_joined_at = datetime.utcnow()

        # Create participant record
        participant = ConsultationParticipant(
            consultation_id=consultation_id,
            user_id=user_id,
            role=ParticipantRole.PATIENT.value,
            joined_at=datetime.utcnow(),
            device_type=device_type,
            connection_type=connection_type,
        )
        self.db.add(participant)

        await self.db.commit()

        # Get queue position and estimated wait
        position = await self._get_queue_position(consultation)
        estimated_wait = await self._estimate_wait_time(consultation)

        logger.info(
            f"Patient {user_id} joined waiting room for consultation {consultation_id}"
        )

        return WaitingRoomJoinResponse(
            consultation_id=consultation_id,
            status=ConsultationStatus.WAITING,
            message=f"You are #{position} in the queue" if position else "Waiting for doctor",
            position=position,
            estimated_wait_minutes=estimated_wait,
        )

    async def get_waiting_room_status(
        self,
        consultation_id: UUID,
    ) -> WaitingRoomStatus:
        """
        Get current waiting room status.

        Args:
            consultation_id: Consultation ID

        Returns:
            Current status with queue position
        """
        result = await self.db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()

        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        position = await self._get_queue_position(consultation)
        estimated_wait = await self._estimate_wait_time(consultation)

        return WaitingRoomStatus(
            status=ConsultationStatus(consultation.status),
            position=position,
            estimated_wait_minutes=estimated_wait,
            patient_joined_at=consultation.patient_joined_at,
        )

    async def doctor_admits_patient(
        self,
        consultation_id: UUID,
        doctor_id: UUID,
    ) -> JoinRoomResponse:
        """
        Doctor admits patient from waiting room to consultation.

        Args:
            consultation_id: Consultation ID
            doctor_id: Doctor's user ID

        Returns:
            Room URL and JWT token for doctor to join

        Raises:
            ValueError: If consultation not found or not in waiting state
        """
        # Get consultation with appointment
        result = await self.db.execute(
            select(Consultation)
            .options(selectinload(Consultation.appointment))
            .where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()

        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        if consultation.status != ConsultationStatus.WAITING.value:
            raise ValueError(
                f"Cannot admit patient: consultation is {consultation.status}"
            )

        # Get doctor details
        doctor_result = await self.db.execute(
            select(Doctor).where(Doctor.user_id == doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()

        if not doctor:
            raise ValueError(f"Doctor not found for user {doctor_id}")

        # Update consultation status
        consultation.status = ConsultationStatus.IN_PROGRESS.value
        consultation.doctor_joined_at = datetime.utcnow()
        consultation.started_at = datetime.utcnow()

        # Create doctor participant record
        doctor_participant = ConsultationParticipant(
            consultation_id=consultation_id,
            user_id=doctor_id,
            role=ParticipantRole.DOCTOR.value,
            joined_at=datetime.utcnow(),
        )
        self.db.add(doctor_participant)

        await self.db.commit()

        # Generate JWT token for doctor (moderator)
        jwt_token = self.generate_jwt_token(
            consultation=consultation,
            user_id=doctor_id,
            user_name=f"Dr. {doctor.name}",
            is_moderator=True,
        )

        logger.info(
            f"Doctor {doctor_id} admitted patient to consultation {consultation_id}"
        )

        return JoinRoomResponse(
            room_url=consultation.room_url or "",
            jwt_token=jwt_token,
            room_name=consultation.room_name,
            consultation_id=consultation_id,
            role=ParticipantRole.DOCTOR,
        )

    async def patient_join_consultation(
        self,
        consultation_id: UUID,
        user_id: UUID,
    ) -> JoinRoomResponse:
        """
        Patient joins active consultation.

        Args:
            consultation_id: Consultation ID
            user_id: Patient's user ID

        Returns:
            Room URL and JWT token for patient

        Raises:
            ValueError: If not admitted yet
        """
        # Get consultation
        result = await self.db.execute(
            select(Consultation)
            .options(selectinload(Consultation.appointment).selectinload(Appointment.patient))
            .where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()

        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        if consultation.status != ConsultationStatus.IN_PROGRESS.value:
            raise ValueError(
                f"Cannot join: consultation is {consultation.status}"
            )

        # Generate JWT token for patient
        patient = consultation.appointment.patient
        jwt_token = self.generate_jwt_token(
            consultation=consultation,
            user_id=user_id,
            user_name=patient.name,
            is_moderator=False,
        )

        logger.info(f"Patient {user_id} joining consultation {consultation_id}")

        return JoinRoomResponse(
            room_url=consultation.room_url or "",
            jwt_token=jwt_token,
            room_name=consultation.room_name,
            consultation_id=consultation_id,
            role=ParticipantRole.PATIENT,
        )

    async def end_consultation(
        self,
        consultation_id: UUID,
        notes: str | None = None,
        connection_quality: ConnectionQuality | None = None,
    ) -> Consultation:
        """
        End consultation and calculate duration.

        Args:
            consultation_id: Consultation ID
            notes: Optional notes about the consultation
            connection_quality: Overall connection quality

        Returns:
            Updated consultation

        Raises:
            ValueError: If consultation not found
        """
        result = await self.db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()

        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        consultation.status = ConsultationStatus.COMPLETED.value
        consultation.ended_at = datetime.utcnow()

        if connection_quality:
            consultation.connection_quality = connection_quality.value

        # Calculate duration
        if consultation.started_at:
            duration = (consultation.ended_at - consultation.started_at).total_seconds() / 60
            consultation.duration_minutes = int(duration)

        # Update metadata if notes provided
        if notes:
            if consultation.metadata is None:
                consultation.metadata = {}
            consultation.metadata["completion_notes"] = notes

        # Mark all participants as left
        await self.db.execute(
            update(ConsultationParticipant)
            .where(
                and_(
                    ConsultationParticipant.consultation_id == consultation_id,
                    ConsultationParticipant.left_at.is_(None),
                )
            )
            .values(left_at=datetime.utcnow())
        )

        await self.db.commit()
        await self.db.refresh(consultation)

        logger.info(
            f"Ended consultation {consultation_id}, duration: {consultation.duration_minutes} min"
        )
        return consultation

    async def submit_recording_consent(
        self,
        consultation_id: UUID,
        user_id: UUID,
        role: ParticipantRole,
        consent: bool,
        consent_text: str | None = None,
    ) -> tuple[bool, datetime]:
        """
        Submit recording consent from doctor or patient.

        Args:
            consultation_id: Consultation ID
            user_id: User submitting consent
            role: User's role (doctor or patient)
            consent: Whether they consent
            consent_text: Legal text shown to user

        Returns:
            Tuple of (can_start_recording, consent_timestamp)
        """
        # Get or create recording record
        result = await self.db.execute(
            select(ConsultationRecording).where(
                ConsultationRecording.consultation_id == consultation_id
            )
        )
        recording = result.scalar_one_or_none()

        if not recording:
            recording = ConsultationRecording(
                consultation_id=consultation_id,
                consent_text=consent_text,
            )
            self.db.add(recording)

        # Update consent based on role
        now = datetime.utcnow()
        if consent:
            if role == ParticipantRole.DOCTOR:
                recording.doctor_consent_at = now
            elif role == ParticipantRole.PATIENT:
                recording.patient_consent_at = now
        else:
            # Revoke consent
            if role == ParticipantRole.DOCTOR:
                recording.doctor_consent_at = None
            elif role == ParticipantRole.PATIENT:
                recording.patient_consent_at = None

        await self.db.commit()
        await self.db.refresh(recording)

        can_start = recording.has_full_consent
        logger.info(
            f"{role.value} {'consented' if consent else 'declined'} recording for "
            f"consultation {consultation_id}. Can start: {can_start}"
        )

        return can_start, now

    async def submit_rating(
        self,
        consultation_id: UUID,
        user_id: UUID,
        role: ParticipantRole,
        rating: int,
        feedback: str | None = None,
    ) -> Consultation:
        """
        Submit post-consultation rating.

        Args:
            consultation_id: Consultation ID
            user_id: User submitting rating
            role: User's role (doctor or patient)
            rating: Rating 1-5
            feedback: Optional text feedback

        Returns:
            Updated consultation
        """
        result = await self.db.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()

        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        # Store rating based on role
        if role == ParticipantRole.DOCTOR:
            consultation.doctor_rating = rating
        elif role == ParticipantRole.PATIENT:
            consultation.patient_rating = rating

        # Store feedback in metadata
        if feedback:
            if consultation.metadata is None:
                consultation.metadata = {}
            consultation.metadata[f"{role.value}_feedback"] = feedback

        await self.db.commit()
        await self.db.refresh(consultation)

        logger.info(
            f"{role.value} rated consultation {consultation_id}: {rating}/5"
        )
        return consultation

    async def get_doctor_queue(
        self,
        doctor_id: UUID,
    ) -> list[DoctorQueueItem]:
        """
        Get list of patients waiting for a doctor.

        Args:
            doctor_id: Doctor's user ID

        Returns:
            List of patients in waiting room
        """
        # Get doctor's appointments with waiting consultations
        query = (
            select(Consultation, Appointment, Patient)
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .where(
                and_(
                    Doctor.user_id == doctor_id,
                    Consultation.status == ConsultationStatus.WAITING.value,
                )
            )
            .order_by(Consultation.patient_joined_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        queue = []
        for consultation, appointment, patient in rows:
            wait_time = 0
            if consultation.patient_joined_at:
                delta = datetime.utcnow() - consultation.patient_joined_at
                wait_time = int(delta.total_seconds() / 60)

            queue.append(
                DoctorQueueItem(
                    consultation_id=consultation.id,
                    appointment_id=appointment.id,
                    patient_id=patient.id,
                    patient_name=patient.name,
                    patient_joined_at=consultation.patient_joined_at or datetime.utcnow(),
                    wait_time_minutes=wait_time,
                    chief_complaint=appointment.chief_complaint,
                    is_emergency=(appointment.appointment_type == "emergency"),
                )
            )

        logger.debug(f"Doctor {doctor_id} has {len(queue)} patients waiting")
        return queue

    async def _get_queue_position(
        self,
        consultation: Consultation,
    ) -> int | None:
        """
        Calculate patient's position in waiting queue.

        Args:
            consultation: Current consultation

        Returns:
            Position (1 = next) or None if not waiting
        """
        if consultation.status != ConsultationStatus.WAITING.value:
            return None

        # Count consultations waiting before this one
        result = await self.db.execute(
            select(func.count(Consultation.id))
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .where(
                and_(
                    Appointment.doctor_id
                    == (
                        select(Appointment.doctor_id).where(
                            Appointment.id == consultation.appointment_id
                        )
                    ),
                    Consultation.status == ConsultationStatus.WAITING.value,
                    Consultation.patient_joined_at < consultation.patient_joined_at,
                )
            )
        )
        count = result.scalar() or 0
        return count + 1

    async def _estimate_wait_time(
        self,
        consultation: Consultation,
    ) -> int | None:
        """
        Estimate wait time based on queue position and average consultation time.

        Args:
            consultation: Current consultation

        Returns:
            Estimated wait in minutes or None
        """
        position = await self._get_queue_position(consultation)
        if not position:
            return None

        # Get average consultation duration for this doctor (last 10 consultations)
        result = await self.db.execute(
            select(func.avg(Consultation.duration_minutes))
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .where(
                and_(
                    Appointment.doctor_id
                    == (
                        select(Appointment.doctor_id).where(
                            Appointment.id == consultation.appointment_id
                        )
                    ),
                    Consultation.status == ConsultationStatus.COMPLETED.value,
                    Consultation.duration_minutes.isnot(None),
                )
            )
            .limit(10)
        )
        avg_duration = result.scalar() or 15  # Default to 15 minutes

        # Estimate: (position - 1) * avg_duration
        # Position 1 means they're next, so wait time is close to avg_duration
        estimated_wait = (position - 1) * avg_duration if position > 1 else avg_duration

        return int(estimated_wait)
