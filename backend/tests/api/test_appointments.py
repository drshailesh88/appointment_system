"""
Tests for appointment endpoints.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestAppointments:
    """Appointment endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_today_appointments(
        self,
        client: AsyncClient,
        auth_headers,
        test_appointment,
    ):
        """Test getting today's appointments."""
        response = await client.get(
            "/api/v1/appointments/today",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_appointments_with_filters(
        self,
        client: AsyncClient,
        auth_headers,
        test_appointment,
        test_doctor,
    ):
        """Test getting appointments with filters."""
        response = await client.get(
            f"/api/v1/appointments?doctor_id={str(test_doctor.id)}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_appointment(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
        test_patient,
    ):
        """Test creating an appointment."""
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

        response = await client.post(
            "/api/v1/appointments",
            headers=auth_headers,
            json={
                "doctor_id": str(test_doctor.id),
                "patient_id": str(test_patient.id),
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(minutes=15)).isoformat(),
                "appointment_type": "new_consultation",
                "chief_complaint": "Headache",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["doctor_id"] == test_doctor.id
        assert data["patient_id"] == test_patient.id
        assert data["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_create_appointment_invalid_doctor(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
    ):
        """Test creating appointment with invalid doctor."""
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

        response = await client.post(
            "/api/v1/appointments",
            headers=auth_headers,
            json={
                "doctor_id": str(uuid4()),
                "patient_id": str(test_patient.id),
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(minutes=15)).isoformat(),
                "appointment_type": "new_consultation",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_appointment_by_id(
        self,
        client: AsyncClient,
        auth_headers,
        test_appointment,
    ):
        """Test getting appointment by ID."""
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_appointment.id

    @pytest.mark.asyncio
    async def test_get_appointment_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test getting non-existent appointment."""
        response = await client.get(
            f"/api/v1/appointments/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_check_in_patient(
        self,
        client: AsyncClient,
        auth_headers,
        test_appointment,
    ):
        """Test checking in a patient."""
        response = await client.post(
            f"/api/v1/appointments/{test_appointment.id}/check-in",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "checked_in"
        assert "token_number" in data

    @pytest.mark.asyncio
    async def test_check_in_already_checked_in(
        self,
        client: AsyncClient,
        auth_headers,
        test_appointment,
        db,
    ):
        """Test checking in already checked-in patient."""
        # First check-in
        test_appointment.status = "checked_in"
        await db.commit()

        response = await client.post(
            f"/api/v1/appointments/{test_appointment.id}/check-in",
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_appointment_status(
        self,
        client: AsyncClient,
        auth_headers,
        test_appointment,
    ):
        """Test updating appointment status."""
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}",
            headers=auth_headers,
            json={"status": "cancelled"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_get_available_slots(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test getting available slots."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        response = await client.post(
            "/api/v1/appointments/slots/availability",
            headers=auth_headers,
            json={
                "doctor_id": str(test_doctor.id),
                "date": tomorrow,
                "duration_minutes": 15,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
        assert isinstance(data["slots"], list)

    @pytest.mark.asyncio
    async def test_get_doctor_schedule(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test getting doctor's schedule."""
        response = await client.get(
            f"/api/v1/appointments/doctor/{test_doctor.id}/schedule",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "doctor_id" in data


class TestAppointmentConflicts:
    """Tests for appointment conflict detection."""

    @pytest.mark.asyncio
    async def test_create_conflicting_appointment(
        self,
        client: AsyncClient,
        auth_headers,
        test_appointment,
        test_doctor,
        test_patient,
        db,
    ):
        """Test creating appointment at conflicting time."""
        # Try to create appointment at same time
        response = await client.post(
            "/api/v1/appointments",
            headers=auth_headers,
            json={
                "doctor_id": str(test_doctor.id),
                "patient_id": str(test_patient.id),
                "start_time": test_appointment.start_time.isoformat(),
                "end_time": test_appointment.end_time.isoformat(),
                "appointment_type": "new_consultation",
            },
        )
        # Should fail due to conflict
        assert response.status_code in [400, 409]
