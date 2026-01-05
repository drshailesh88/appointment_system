"""
Tests for Telemedicine Service.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import jwt

from app.models.appointment import Appointment, AppointmentStatus
from app.models.consultation import (
    Consultation,
    ConsultationStatus,
    ParticipantRole,
    ConnectionQuality,
)
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from app.services.telemedicine import TelemedicineService
from app.core.config import settings


@pytest.fixture
async def test_appointment(db_session, test_doctor, test_patient):
    """Create test appointment."""
    appointment = Appointment(
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        scheduled_start=datetime.utcnow() + timedelta(hours=1),
        scheduled_end=datetime.utcnow() + timedelta(hours=1, minutes=30),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED.value,
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest.fixture
async def telemedicine_service(db_session):
    """Create telemedicine service instance."""
    return TelemedicineService(db_session)


class TestConsultationCreation:
    """Test consultation creation."""

    async def test_create_consultation_success(
        self, telemedicine_service, test_appointment
    ):
        """Test successful consultation creation."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        assert consultation is not None
        assert consultation.appointment_id == test_appointment.id
        assert consultation.status == ConsultationStatus.SCHEDULED.value
        assert consultation.room_name.startswith("docassist-")
        assert consultation.room_url is not None
        assert settings.jitsi_domain in consultation.room_url

    async def test_create_consultation_duplicate_fails(
        self, telemedicine_service, test_appointment
    ):
        """Test that creating duplicate consultation fails."""
        # Create first consultation
        await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await telemedicine_service.create_consultation(
                appointment_id=test_appointment.id
            )

    async def test_create_consultation_invalid_appointment(
        self, telemedicine_service
    ):
        """Test creating consultation with invalid appointment."""
        invalid_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await telemedicine_service.create_consultation(
                appointment_id=invalid_id
            )


class TestJWTTokenGeneration:
    """Test JWT token generation."""

    async def test_generate_jwt_token_for_patient(
        self, telemedicine_service, test_appointment, db_session
    ):
        """Test JWT token generation for patient."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        user_id = uuid4()
        token = telemedicine_service.generate_jwt_token(
            consultation=consultation,
            user_id=user_id,
            user_name="John Doe",
            is_moderator=False,
        )

        # Decode and verify token
        decoded = jwt.decode(
            token, settings.jitsi_jwt_secret, algorithms=["HS256"]
        )

        assert decoded["room"] == consultation.room_name
        assert decoded["context"]["user"]["id"] == str(user_id)
        assert decoded["context"]["user"]["name"] == "John Doe"
        assert decoded["context"]["user"]["moderator"] == "false"

    async def test_generate_jwt_token_for_doctor(
        self, telemedicine_service, test_appointment, db_session
    ):
        """Test JWT token generation for doctor (moderator)."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        user_id = uuid4()
        token = telemedicine_service.generate_jwt_token(
            consultation=consultation,
            user_id=user_id,
            user_name="Dr. Smith",
            is_moderator=True,
        )

        decoded = jwt.decode(
            token, settings.jitsi_jwt_secret, algorithms=["HS256"]
        )

        assert decoded["context"]["user"]["moderator"] == "true"

    async def test_jwt_token_expiration(
        self, telemedicine_service, test_appointment, db_session
    ):
        """Test JWT token has correct expiration."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        token = telemedicine_service.generate_jwt_token(
            consultation=consultation,
            user_id=uuid4(),
            user_name="Test User",
        )

        decoded = jwt.decode(
            token, settings.jitsi_jwt_secret, algorithms=["HS256"]
        )

        # Token should expire in ~2 hours
        exp_time = datetime.fromtimestamp(decoded["exp"])
        now = datetime.utcnow()
        time_diff = (exp_time - now).total_seconds()

        assert 7000 < time_diff < 7400  # ~2 hours with some tolerance


class TestWaitingRoom:
    """Test waiting room functionality."""

    async def test_join_waiting_room(
        self, telemedicine_service, test_appointment, db_session
    ):
        """Test patient joining waiting room."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        user_id = uuid4()
        response = await telemedicine_service.join_waiting_room(
            consultation_id=consultation.id,
            user_id=user_id,
            device_type="android",
            connection_type="wifi",
        )

        assert response.status == ConsultationStatus.WAITING
        assert response.position is not None

        # Verify consultation status updated
        await db_session.refresh(consultation)
        assert consultation.status == ConsultationStatus.WAITING.value
        assert consultation.patient_joined_at is not None

    async def test_get_queue_position(
        self, telemedicine_service, test_appointment, test_doctor, db_session
    ):
        """Test queue position calculation."""
        # Create multiple consultations
        consultations = []
        for i in range(3):
            appointment = Appointment(
                patient_id=test_appointment.patient_id,
                doctor_id=test_appointment.doctor_id,
                scheduled_start=datetime.utcnow() + timedelta(hours=i + 1),
                scheduled_end=datetime.utcnow()
                + timedelta(hours=i + 1, minutes=30),
                duration_minutes=30,
            )
            db_session.add(appointment)
            await db_session.commit()
            await db_session.refresh(appointment)

            consultation = await telemedicine_service.create_consultation(
                appointment_id=appointment.id
            )
            consultations.append(consultation)

        # Have patients join in order
        for i, consultation in enumerate(consultations):
            await telemedicine_service.join_waiting_room(
                consultation_id=consultation.id,
                user_id=uuid4(),
            )

            status = await telemedicine_service.get_waiting_room_status(
                consultation.id
            )
            assert status.position == i + 1


class TestDoctorAdmission:
    """Test doctor admitting patients."""

    async def test_doctor_admits_patient(
        self, telemedicine_service, test_appointment, test_doctor, db_session
    ):
        """Test doctor admitting patient to consultation."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        # Patient joins waiting room
        await telemedicine_service.join_waiting_room(
            consultation_id=consultation.id,
            user_id=uuid4(),
        )

        # Doctor admits patient
        join_response = await telemedicine_service.doctor_admits_patient(
            consultation_id=consultation.id,
            doctor_id=test_doctor.user_id,
        )

        assert join_response is not None
        assert join_response.room_url == consultation.room_url
        assert join_response.jwt_token is not None
        assert join_response.role == ParticipantRole.DOCTOR

        # Verify consultation status
        await db_session.refresh(consultation)
        assert consultation.status == ConsultationStatus.IN_PROGRESS.value
        assert consultation.doctor_joined_at is not None
        assert consultation.started_at is not None

    async def test_admit_patient_not_waiting_fails(
        self, telemedicine_service, test_appointment, test_doctor, db_session
    ):
        """Test that admitting patient not in waiting room fails."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        # Try to admit without patient joining first
        with pytest.raises(ValueError, match="not in waiting state"):
            await telemedicine_service.doctor_admits_patient(
                consultation_id=consultation.id,
                doctor_id=test_doctor.user_id,
            )


class TestConsultationLifecycle:
    """Test consultation lifecycle."""

    async def test_end_consultation(
        self, telemedicine_service, test_appointment, test_doctor, db_session
    ):
        """Test ending a consultation."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        # Join waiting room and admit
        await telemedicine_service.join_waiting_room(
            consultation_id=consultation.id,
            user_id=uuid4(),
        )
        await telemedicine_service.doctor_admits_patient(
            consultation_id=consultation.id,
            doctor_id=test_doctor.user_id,
        )

        # End consultation
        ended = await telemedicine_service.end_consultation(
            consultation_id=consultation.id,
            notes="Consultation completed successfully",
            connection_quality=ConnectionQuality.GOOD,
        )

        assert ended.status == ConsultationStatus.COMPLETED.value
        assert ended.ended_at is not None
        assert ended.duration_minutes is not None
        assert ended.duration_minutes > 0
        assert ended.connection_quality == ConnectionQuality.GOOD.value

    async def test_consultation_duration_calculation(
        self, telemedicine_service, test_appointment, test_doctor, db_session
    ):
        """Test consultation duration is calculated correctly."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        # Set started time manually for testing
        consultation.started_at = datetime.utcnow() - timedelta(minutes=15)
        await db_session.commit()

        # End consultation
        ended = await telemedicine_service.end_consultation(
            consultation_id=consultation.id
        )

        # Duration should be around 15 minutes
        assert 14 <= ended.duration_minutes <= 16


class TestRecordingConsent:
    """Test recording consent functionality."""

    async def test_submit_patient_consent(
        self, telemedicine_service, test_appointment, db_session
    ):
        """Test patient submitting recording consent."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        can_start, timestamp = await telemedicine_service.submit_recording_consent(
            consultation_id=consultation.id,
            user_id=uuid4(),
            role=ParticipantRole.PATIENT,
            consent=True,
            consent_text="I consent to recording this consultation.",
        )

        # Should not be able to start yet (need doctor consent too)
        assert can_start is False
        assert timestamp is not None

    async def test_both_parties_consent(
        self, telemedicine_service, test_appointment, test_doctor, db_session
    ):
        """Test recording can start when both parties consent."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        # Patient consents
        await telemedicine_service.submit_recording_consent(
            consultation_id=consultation.id,
            user_id=uuid4(),
            role=ParticipantRole.PATIENT,
            consent=True,
        )

        # Doctor consents
        can_start, _ = await telemedicine_service.submit_recording_consent(
            consultation_id=consultation.id,
            user_id=test_doctor.user_id,
            role=ParticipantRole.DOCTOR,
            consent=True,
        )

        # Now recording can start
        assert can_start is True


class TestRatings:
    """Test post-consultation ratings."""

    async def test_submit_rating(
        self, telemedicine_service, test_appointment, db_session
    ):
        """Test submitting consultation rating."""
        consultation = await telemedicine_service.create_consultation(
            appointment_id=test_appointment.id
        )

        # Submit patient rating
        rated = await telemedicine_service.submit_rating(
            consultation_id=consultation.id,
            user_id=uuid4(),
            role=ParticipantRole.PATIENT,
            rating=5,
            feedback="Excellent consultation!",
        )

        assert rated.patient_rating == 5
        assert rated.metadata is not None
        assert "patient_feedback" in rated.metadata
        assert rated.metadata["patient_feedback"] == "Excellent consultation!"


class TestDoctorQueue:
    """Test doctor queue functionality."""

    async def test_get_doctor_queue(
        self, telemedicine_service, test_doctor, test_patient, db_session
    ):
        """Test getting doctor's waiting queue."""
        # Create multiple waiting consultations
        for i in range(3):
            appointment = Appointment(
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                scheduled_start=datetime.utcnow() + timedelta(hours=i + 1),
                scheduled_end=datetime.utcnow()
                + timedelta(hours=i + 1, minutes=30),
                duration_minutes=30,
                chief_complaint=f"Test complaint {i}",
            )
            db_session.add(appointment)
            await db_session.commit()
            await db_session.refresh(appointment)

            consultation = await telemedicine_service.create_consultation(
                appointment_id=appointment.id
            )
            await telemedicine_service.join_waiting_room(
                consultation_id=consultation.id,
                user_id=uuid4(),
            )

        # Get doctor's queue
        queue = await telemedicine_service.get_doctor_queue(
            doctor_id=test_doctor.user_id
        )

        assert len(queue) == 3
        # Should be ordered by join time
        for item in queue:
            assert item.patient_name == test_patient.full_name
            assert item.wait_time_minutes >= 0
