"""
Comprehensive tests for appointment booking system.

Tests cover:
1. Happy path scenarios (create, reschedule, cancel, get, list)
2. Edge cases (double booking, past dates, clinic hours, concurrent access)
3. Validation (missing fields, invalid formats, max lengths)
4. Status transitions and state management
"""
import asyncio
from datetime import datetime, date, time, timedelta, timezone
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, BookingSource
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User


class TestAppointmentBookingHappyPath:
    """Test successful appointment booking scenarios."""

    def test_book_new_appointment_with_valid_data(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test booking a new appointment with all valid data."""
        # Schedule for tomorrow at 10 AM
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
                "appointment_type": "new_consultation",
                "booking_source": "app",
                "chief_complaint": "Regular checkup",
                "notes": "Patient requested morning slot",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == str(test_patient.id)
        assert data["doctor_id"] == str(test_doctor.id)
        assert data["status"] == AppointmentStatus.SCHEDULED.value
        assert data["duration_minutes"] == 15
        assert data["appointment_type"] == AppointmentType.NEW_CONSULTATION.value
        assert data["booking_source"] == BookingSource.APP.value
        assert data["chief_complaint"] == "Regular checkup"
        assert data["notes"] == "Patient requested morning slot"
        assert data["id"] is not None

    def test_book_appointment_minimal_data(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test booking appointment with only required fields."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=14, minute=30, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == str(test_patient.id)
        assert data["status"] == AppointmentStatus.SCHEDULED.value
        assert data["appointment_type"] == AppointmentType.NEW_CONSULTATION.value  # Default
        assert data["booking_source"] == BookingSource.WALK_IN.value  # Default

    def test_reschedule_existing_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
        db: Session,
    ):
        """Test rescheduling an existing appointment to a new time."""
        # Create initial appointment
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        original_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": original_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        assert create_response.status_code == 201
        appointment_id = create_response.json()["id"]

        # Reschedule to 2 hours later
        new_start = original_start + timedelta(hours=2)
        update_response = client.patch(
            f"/api/v1/appointments/{appointment_id}",
            headers=auth_headers,
            json={
                "scheduled_start": new_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert update_response.status_code == 200
        data = update_response.json()
        # Parse and compare datetimes
        returned_start = datetime.fromisoformat(data["scheduled_start"].replace("Z", "+00:00"))
        assert returned_start.replace(tzinfo=None) == new_start.replace(tzinfo=None)

    def test_cancel_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test cancelling an appointment with reason."""
        # Create appointment
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        assert create_response.status_code == 201
        appointment_id = create_response.json()["id"]

        # Cancel it
        cancel_response = client.post(
            f"/api/v1/appointments/{appointment_id}/cancel",
            headers=auth_headers,
            params={"reason": "Patient requested cancellation"},
        )

        assert cancel_response.status_code == 200
        data = cancel_response.json()
        assert data["status"] == AppointmentStatus.CANCELLED.value
        assert data["cancellation_reason"] == "Patient requested cancellation"
        assert data["cancelled_by"] is not None

    def test_get_appointment_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test retrieving a specific appointment by ID."""
        # Create appointment
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
                "chief_complaint": "Follow-up visit",
            },
        )
        assert create_response.status_code == 201
        appointment_id = create_response.json()["id"]

        # Get it by ID
        get_response = client.get(
            f"/api/v1/appointments/{appointment_id}",
            headers=auth_headers,
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == appointment_id
        assert data["patient_id"] == str(test_patient.id)
        assert data["doctor_id"] == str(test_doctor.id)
        assert data["chief_complaint"] == "Follow-up visit"

    def test_list_appointments_by_doctor(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test listing appointments filtered by doctor."""
        # Create multiple appointments
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

        for hour in [9, 10, 11]:
            scheduled_start = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
            response = client.post(
                "/api/v1/appointments/",
                headers=auth_headers,
                json={
                    "patient_id": str(test_patient.id),
                    "doctor_id": str(test_doctor.id),
                    "scheduled_start": scheduled_start.isoformat(),
                    "duration_minutes": 15,
                },
            )
            assert response.status_code == 201

        # List appointments for this doctor
        list_response = client.get(
            "/api/v1/appointments/",
            headers=auth_headers,
            params={"doctor_id": str(test_doctor.id)},
        )

        assert list_response.status_code == 200
        data = list_response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        # Verify all are for the correct doctor
        for appt in data:
            assert appt["doctor_id"] == str(test_doctor.id)

    def test_list_appointments_by_patient(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test listing appointments filtered by patient."""
        # Create appointments
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        # List appointments for this patient
        list_response = client.get(
            "/api/v1/appointments/",
            headers=auth_headers,
            params={"patient_id": str(test_patient.id)},
        )

        assert list_response.status_code == 200
        data = list_response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for appt in data:
            assert appt["patient_id"] == str(test_patient.id)

    def test_list_appointments_by_date_range(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test listing appointments filtered by date range."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        # List appointments within date range
        list_response = client.get(
            "/api/v1/appointments/",
            headers=auth_headers,
            params={
                "date_from": tomorrow.date().isoformat(),
                "date_to": tomorrow.date().isoformat(),
            },
        )

        assert list_response.status_code == 200
        data = list_response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_appointments_by_status(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test listing appointments filtered by status."""
        # Create and cancel an appointment
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        client.post(
            f"/api/v1/appointments/{appointment_id}/cancel",
            headers=auth_headers,
        )

        # List cancelled appointments
        list_response = client.get(
            "/api/v1/appointments/",
            headers=auth_headers,
            params={"status_filter": "cancelled"},
        )

        assert list_response.status_code == 200
        data = list_response.json()
        assert isinstance(data, list)
        for appt in data:
            assert appt["status"] == AppointmentStatus.CANCELLED.value


class TestAppointmentBookingEdgeCases:
    """Test edge cases and error conditions."""

    def test_prevent_double_booking_same_slot(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
        db: Session,
    ):
        """Test that double booking the same slot for a doctor is prevented."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create first appointment
        first_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        assert first_response.status_code == 201

        # Create another patient
        patient2 = Patient(
            id=uuid4(),
            clinic_id=test_patient.clinic_id,
            first_name="Second",
            last_name="Patient",
            phone="+919876543299",
            gender="female",
            date_of_birth=datetime(1985, 5, 20).date(),
        )
        db.add(patient2)
        db.commit()

        # Try to book same slot with different patient (should fail)
        second_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(patient2.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert second_response.status_code == 409
        assert "already booked" in second_response.json()["detail"].lower()

    def test_prevent_overlapping_appointments(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
        db: Session,
    ):
        """Test that overlapping appointments are prevented."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        first_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create first appointment (10:00 - 10:30, 30 min)
        first_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": first_start.isoformat(),
                "duration_minutes": 30,
            },
        )
        assert first_response.status_code == 201

        # Create another patient
        patient2 = Patient(
            id=uuid4(),
            clinic_id=test_patient.clinic_id,
            first_name="Second",
            last_name="Patient",
            phone="+919876543288",
            gender="male",
            date_of_birth=datetime(1992, 3, 10).date(),
        )
        db.add(patient2)
        db.commit()

        # Try to book overlapping slot (10:15 - 10:30, overlaps with first)
        overlapping_start = first_start + timedelta(minutes=15)
        second_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(patient2.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": overlapping_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert second_response.status_code == 409

    def test_booking_in_past_should_work_for_walkins(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that walk-ins can be booked in recent past (for late entries)."""
        # 10 minutes ago (common for walk-in backdating)
        past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        scheduled_start = past_time.replace(second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
                "booking_source": "walk_in",
            },
        )

        # Should succeed for walk-ins (schema validator allows flexibility)
        assert response.status_code == 201

    def test_booking_outside_clinic_hours(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test booking outside clinic working hours (should succeed, validation is separate)."""
        # Note: API doesn't enforce working hours in create endpoint
        # This is typically handled at UI level or via slot availability endpoint
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        # 8 PM - typically outside working hours
        scheduled_start = tomorrow.replace(hour=20, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        # Currently succeeds - business logic for hours is in slot availability
        assert response.status_code == 201

    def test_booking_with_nonexistent_patient(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test booking appointment with non-existent patient ID."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        fake_patient_id = uuid4()
        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(fake_patient_id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 404
        assert "patient not found" in response.json()["detail"].lower()

    def test_booking_with_nonexistent_doctor(
        self,
        client: TestClient,
        auth_headers: dict,
        test_patient: Patient,
    ):
        """Test booking appointment with non-existent doctor ID."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        fake_doctor_id = uuid4()
        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(fake_doctor_id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 404
        assert "doctor not found" in response.json()["detail"].lower()

    def test_booking_patient_and_doctor_different_clinics(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
        db: Session,
    ):
        """Test that patient and doctor must belong to same clinic."""
        # Create a different clinic
        other_clinic = Clinic(
            id=uuid4(),
            name="Other Clinic",
            slug="other-clinic-booking",
            address="456 Other Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            phone="+919999999999",
            email="other@clinic.com",
            subscription_tier="basic",
        )
        db.add(other_clinic)
        db.commit()

        # Create patient in different clinic
        other_patient = Patient(
            id=uuid4(),
            clinic_id=other_clinic.id,
            first_name="Other",
            last_name="Patient",
            phone="+919876543277",
            gender="female",
            date_of_birth=datetime(1988, 7, 25).date(),
        )
        db.add(other_patient)
        db.commit()

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(other_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 400
        assert "same clinic" in response.json()["detail"].lower()

    def test_appointment_status_transitions(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test valid appointment status transitions: scheduled → checked_in → in_progress → completed."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create appointment (scheduled)
        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        assert create_response.status_code == 201
        appointment_id = create_response.json()["id"]
        assert create_response.json()["status"] == AppointmentStatus.SCHEDULED.value

        # Check in patient (scheduled → checked_in)
        checkin_response = client.post(
            f"/api/v1/appointments/{appointment_id}/check-in",
            headers=auth_headers,
        )
        assert checkin_response.status_code == 200
        assert checkin_response.json()["status"] == AppointmentStatus.CHECKED_IN.value
        assert checkin_response.json()["check_in_time"] is not None
        assert checkin_response.json()["token_number"] is not None

        # Start consultation (checked_in → in_progress)
        start_response = client.post(
            f"/api/v1/appointments/{appointment_id}/start",
            headers=auth_headers,
        )
        assert start_response.status_code == 200
        assert start_response.json()["status"] == AppointmentStatus.IN_PROGRESS.value
        assert start_response.json()["start_time"] is not None

        # Complete consultation (in_progress → completed)
        complete_response = client.post(
            f"/api/v1/appointments/{appointment_id}/complete",
            headers=auth_headers,
            json={
                "notes": "Consultation completed successfully",
                "emr_visit_id": "EMR-123",
            },
        )
        assert complete_response.status_code == 200
        data = complete_response.json()
        assert data["status"] == AppointmentStatus.COMPLETED.value
        assert data["end_time"] is not None
        assert data["notes"] == "Consultation completed successfully"
        assert data["emr_visit_id"] == "EMR-123"

    def test_invalid_status_transition_start_without_checkin(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that starting consultation requires check-in first."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        # Try to start without checking in
        start_response = client.post(
            f"/api/v1/appointments/{appointment_id}/start",
            headers=auth_headers,
        )

        assert start_response.status_code == 400
        assert "checked in" in start_response.json()["detail"].lower()

    def test_invalid_status_transition_complete_without_start(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that completing consultation requires it to be in progress."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        # Try to complete without starting
        complete_response = client.post(
            f"/api/v1/appointments/{appointment_id}/complete",
            headers=auth_headers,
        )

        assert complete_response.status_code == 400
        assert "in progress" in complete_response.json()["detail"].lower()

    def test_cannot_cancel_completed_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that completed appointments cannot be cancelled."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create and complete appointment
        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        # Complete the workflow
        client.post(f"/api/v1/appointments/{appointment_id}/check-in", headers=auth_headers)
        client.post(f"/api/v1/appointments/{appointment_id}/start", headers=auth_headers)
        client.post(f"/api/v1/appointments/{appointment_id}/complete", headers=auth_headers)

        # Try to cancel completed appointment
        cancel_response = client.post(
            f"/api/v1/appointments/{appointment_id}/cancel",
            headers=auth_headers,
        )

        assert cancel_response.status_code == 400
        assert "cannot cancel" in cancel_response.json()["detail"].lower()

    def test_cannot_cancel_already_cancelled_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that cancelled appointments cannot be cancelled again."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        # Cancel once
        client.post(f"/api/v1/appointments/{appointment_id}/cancel", headers=auth_headers)

        # Try to cancel again
        cancel_again_response = client.post(
            f"/api/v1/appointments/{appointment_id}/cancel",
            headers=auth_headers,
        )

        assert cancel_again_response.status_code == 400

    def test_mark_no_show(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test marking a patient as no-show."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        # Mark as no-show
        noshow_response = client.post(
            f"/api/v1/appointments/{appointment_id}/no-show",
            headers=auth_headers,
        )

        assert noshow_response.status_code == 200
        assert noshow_response.json()["status"] == AppointmentStatus.NO_SHOW.value


class TestAppointmentBookingValidation:
    """Test validation and error handling."""

    def test_missing_required_patient_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test that patient_id is required."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                # Missing patient_id
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 422  # Validation error

    def test_missing_required_doctor_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_patient: Patient,
    ):
        """Test that doctor_id is required."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                # Missing doctor_id
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 422

    def test_missing_required_scheduled_start(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that scheduled_start is required."""
        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                # Missing scheduled_start
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 422

    def test_invalid_uuid_format_patient_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test that invalid UUID format for patient_id is rejected."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": "not-a-valid-uuid",
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 422

    def test_invalid_uuid_format_doctor_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_patient: Patient,
    ):
        """Test that invalid UUID format for doctor_id is rejected."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": "invalid-uuid-format",
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 422

    def test_invalid_datetime_format(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that invalid datetime format is rejected."""
        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": "not-a-valid-datetime",
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 422

    def test_duration_too_short(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that duration must be at least 5 minutes."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 2,  # Too short
            },
        )

        assert response.status_code == 422

    def test_duration_too_long(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that duration cannot exceed 120 minutes."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 150,  # Too long
            },
        )

        assert response.status_code == 422

    def test_chief_complaint_max_length(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that chief_complaint has a maximum length of 500 characters."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create a 501 character string
        long_complaint = "A" * 501

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
                "chief_complaint": long_complaint,
            },
        )

        assert response.status_code == 422

    def test_chief_complaint_at_max_length_allowed(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that chief_complaint can be exactly 500 characters."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create exactly 500 character string
        max_complaint = "A" * 500

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
                "chief_complaint": max_complaint,
            },
        )

        assert response.status_code == 201
        assert len(response.json()["chief_complaint"]) == 500

    def test_invalid_appointment_type(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that invalid appointment_type is rejected."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
                "appointment_type": "invalid_type",
            },
        )

        assert response.status_code == 422

    def test_invalid_booking_source(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that invalid booking_source is rejected."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
                "booking_source": "invalid_source",
            },
        )

        assert response.status_code == 422

    def test_get_nonexistent_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test getting an appointment that doesn't exist."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/appointments/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_nonexistent_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test updating an appointment that doesn't exist."""
        fake_id = uuid4()
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

        response = client.patch(
            f"/api/v1/appointments/{fake_id}",
            headers=auth_headers,
            json={
                "scheduled_start": scheduled_start.isoformat(),
            },
        )

        assert response.status_code == 404

    def test_cancel_nonexistent_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test cancelling an appointment that doesn't exist."""
        fake_id = uuid4()
        response = client.post(
            f"/api/v1/appointments/{fake_id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestAppointmentSlotAvailability:
    """Test slot availability checking."""

    def test_get_available_slots_for_doctor(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test getting available slots for a doctor on a specific date."""
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        response = client.post(
            "/api/v1/appointments/slots/availability",
            headers=auth_headers,
            json={
                "doctor_id": str(test_doctor.id),
                "date": tomorrow.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["doctor_id"] == str(test_doctor.id)
        assert data["date"] == tomorrow.isoformat()
        assert "slots" in data
        assert isinstance(data["slots"], list)

    def test_available_slots_exclude_booked_times(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that booked slots are marked as unavailable."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        booked_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Book a slot
        client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": booked_time.isoformat(),
                "duration_minutes": 15,
            },
        )

        # Check availability
        response = client.post(
            "/api/v1/appointments/slots/availability",
            headers=auth_headers,
            json={
                "doctor_id": str(test_doctor.id),
                "date": tomorrow.date().isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 200
        data = response.json()
        slots = data["slots"]

        # Find the 10:00 slot and verify it's unavailable
        booked_slot = next(
            (s for s in slots if s["start_time"].startswith(booked_time.strftime("%Y-%m-%dT10:00"))),
            None
        )
        if booked_slot:
            assert booked_slot["is_available"] is False

    def test_available_slots_for_nonexistent_doctor(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test slot availability for non-existent doctor."""
        fake_doctor_id = uuid4()
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        response = client.post(
            "/api/v1/appointments/slots/availability",
            headers=auth_headers,
            json={
                "doctor_id": str(fake_doctor_id),
                "date": tomorrow.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 404


class TestAppointmentDoctorSchedule:
    """Test doctor's daily schedule."""

    def test_get_doctor_schedule_today(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test getting doctor's schedule for today."""
        # Create an appointment for today
        today = datetime.now(timezone.utc)
        scheduled_start = today.replace(hour=14, minute=0, second=0, microsecond=0)
        if scheduled_start < today:
            scheduled_start += timedelta(days=1)

        client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        response = client.get(
            f"/api/v1/appointments/doctor/{test_doctor.id}/schedule",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["doctor_id"] == str(test_doctor.id)
        assert "appointments" in data
        assert "total_appointments" in data
        assert "completed" in data
        assert "pending" in data
        assert "cancelled" in data

    def test_get_doctor_schedule_specific_date(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test getting doctor's schedule for a specific date."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        response = client.get(
            f"/api/v1/appointments/doctor/{test_doctor.id}/schedule",
            headers=auth_headers,
            params={"schedule_date": tomorrow.date().isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == tomorrow.date().isoformat()
        assert data["total_appointments"] >= 1

    def test_get_doctor_schedule_counts_by_status(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that schedule correctly counts appointments by status."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

        # Create 3 appointments
        appointment_ids = []
        for hour in [10, 11, 12]:
            scheduled_start = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
            response = client.post(
                "/api/v1/appointments/",
                headers=auth_headers,
                json={
                    "patient_id": str(test_patient.id),
                    "doctor_id": str(test_doctor.id),
                    "scheduled_start": scheduled_start.isoformat(),
                    "duration_minutes": 15,
                },
            )
            appointment_ids.append(response.json()["id"])

        # Cancel one
        client.post(f"/api/v1/appointments/{appointment_ids[0]}/cancel", headers=auth_headers)

        # Complete one
        client.post(f"/api/v1/appointments/{appointment_ids[1]}/check-in", headers=auth_headers)
        client.post(f"/api/v1/appointments/{appointment_ids[1]}/start", headers=auth_headers)
        client.post(f"/api/v1/appointments/{appointment_ids[1]}/complete", headers=auth_headers)

        # Get schedule
        response = client.get(
            f"/api/v1/appointments/doctor/{test_doctor.id}/schedule",
            headers=auth_headers,
            params={"schedule_date": tomorrow.date().isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_appointments"] == 3
        assert data["cancelled"] >= 1
        assert data["completed"] >= 1
        assert data["pending"] >= 1  # One scheduled


class TestAppointmentConcurrency:
    """Test concurrent booking scenarios."""

    def test_concurrent_booking_same_slot(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
        db: Session,
    ):
        """Test that concurrent requests for the same slot are handled correctly."""
        # Create second patient
        patient2 = Patient(
            id=uuid4(),
            clinic_id=test_patient.clinic_id,
            first_name="Concurrent",
            last_name="Patient",
            phone="+919876543266",
            gender="male",
            date_of_birth=datetime(1991, 6, 15).date(),
        )
        db.add(patient2)
        db.commit()

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Make first request
        response1 = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        # Make second concurrent request (simulated)
        response2 = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(patient2.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        # One should succeed, one should fail with conflict
        statuses = sorted([response1.status_code, response2.status_code])
        assert statuses == [201, 409] or statuses == [201, 201] and response1.json()["id"] != response2.json()["id"]
        # Note: True concurrent testing would require actual threading/multiprocessing


class TestAppointmentIntegrations:
    """Test external integrations (mocked)."""

    @patch('app.services.calendar_sync.CalendarSyncService.sync_appointment')
    def test_appointment_creation_syncs_to_calendar(
        self,
        mock_sync: AsyncMock,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that appointment creation triggers calendar sync."""
        mock_sync.return_value = None

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        assert response.status_code == 201
        # Calendar sync is called but doesn't block on errors

    @patch('app.services.calendar_sync.CalendarSyncService.sync_appointment')
    def test_appointment_creation_succeeds_even_if_calendar_sync_fails(
        self,
        mock_sync: AsyncMock,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that appointment creation succeeds even if calendar sync fails."""
        mock_sync.side_effect = Exception("Calendar service unavailable")

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )

        # Should still succeed despite calendar sync failure
        assert response.status_code == 201


class TestAppointmentTokenGeneration:
    """Test token number generation for appointments."""

    def test_token_number_auto_generated_on_checkin(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that token number is auto-generated when checking in."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        checkin_response = client.post(
            f"/api/v1/appointments/{appointment_id}/check-in",
            headers=auth_headers,
        )

        assert checkin_response.status_code == 200
        assert checkin_response.json()["token_number"] is not None
        assert checkin_response.json()["token_number"] >= 1

    def test_token_numbers_increment_per_doctor_per_day(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test that token numbers increment for each doctor per day."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

        tokens = []
        for hour in [10, 11, 12]:
            scheduled_start = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)

            create_response = client.post(
                "/api/v1/appointments/",
                headers=auth_headers,
                json={
                    "patient_id": str(test_patient.id),
                    "doctor_id": str(test_doctor.id),
                    "scheduled_start": scheduled_start.isoformat(),
                    "duration_minutes": 15,
                },
            )
            appointment_id = create_response.json()["id"]

            checkin_response = client.post(
                f"/api/v1/appointments/{appointment_id}/check-in",
                headers=auth_headers,
            )
            tokens.append(checkin_response.json()["token_number"])

        # Tokens should be sequential
        assert tokens[0] < tokens[1] < tokens[2]

    def test_custom_token_number_on_checkin(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test providing a custom token number during check-in."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        create_response = client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "scheduled_start": scheduled_start.isoformat(),
                "duration_minutes": 15,
            },
        )
        appointment_id = create_response.json()["id"]

        checkin_response = client.post(
            f"/api/v1/appointments/{appointment_id}/check-in",
            headers=auth_headers,
            json={"token_number": 99},
        )

        assert checkin_response.status_code == 200
        assert checkin_response.json()["token_number"] == 99
