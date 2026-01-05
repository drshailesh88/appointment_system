"""
Tests for doctor endpoints.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestDoctors:
    """Doctor endpoint tests."""

    @pytest.mark.asyncio

    async def test_get_doctors(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test getting list of doctors."""
        response = await client.get(
            "/api/v1/doctors/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_get_doctors_by_specialization(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test filtering doctors by specialization."""
        response = await client.get(
            f"/api/v1/doctors/?specialization={test_doctor.specialization}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(d["specialization"] == test_doctor.specialization for d in data)

    @pytest.mark.asyncio

    async def test_get_doctors_active_only(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test filtering only active doctors."""
        response = await client.get(
            "/api/v1/doctors/?active_only=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(d.get("is_active", True) for d in data)

    @pytest.mark.asyncio

    async def test_get_doctor_by_id(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test getting doctor by ID."""
        response = await client.get(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_doctor.id)
        assert data["name"] == test_doctor.name

    @pytest.mark.asyncio

    async def test_get_doctor_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test getting non-existent doctor."""
        response = await client.get(
            f"/api/v1/doctors/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_update_doctor(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test updating doctor details."""
        response = await client.patch(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
            json={
                "consultation_fee": 600.0,
                "accepting_new_patients": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["consultation_fee"] == 600.0
        assert data["accepting_new_patients"] == False

    @pytest.mark.asyncio

    async def test_update_doctor_working_hours(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test updating doctor's working hours."""
        new_hours = {
            "monday": {"start": "10:00", "end": "18:00"},
            "tuesday": {"start": "10:00", "end": "18:00"},
            "wednesday": {"start": "10:00", "end": "18:00"},
            "thursday": {"start": "10:00", "end": "18:00"},
            "friday": {"start": "10:00", "end": "18:00"},
            "saturday": {"start": "10:00", "end": "14:00"},
        }
        response = await client.patch(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
            json={"working_hours": new_hours},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["working_hours"]["saturday"]["start"] == "10:00"

    @pytest.mark.asyncio

    async def test_get_doctor_appointments(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
        test_appointment,
    ):
        """Test getting doctor's appointments."""
        response = await client.get(
            f"/api/v1/appointments?doctor_id={str(test_doctor.id)}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDoctorAvailability:
    """Tests for doctor availability."""

    @pytest.mark.asyncio

    async def test_get_doctor_availability(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test getting doctor availability info."""
        response = await client.get(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "working_hours" in data
        assert "slot_duration" in data
        assert "accepting_new_patients" in data

    @pytest.mark.asyncio

    async def test_doctor_deactivation(
        self,
        client: AsyncClient,
        auth_headers,
        test_doctor,
    ):
        """Test deactivating a doctor."""
        response = await client.patch(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
            json={"is_active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] == False

        # Verify doctor doesn't appear in active list
        response = await client.get(
            "/api/v1/doctors/?active_only=true",
            headers=auth_headers,
        )
        data = response.json()
        assert not any(d["id"] == str(test_doctor.id) for d in data)

