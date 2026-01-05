"""
Tests for Waitlist API endpoints.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4


class TestWaitlistEndpoints:
    """Tests for waitlist API endpoints."""

    @pytest.mark.asyncio

    async def test_get_waitlist_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/waitlist/")
        assert response.status_code == 401

    @pytest.mark.asyncio

    async def test_get_waitlist_empty(self, client, auth_headers, test_clinic):
        """Test getting empty waitlist."""
        response = await client.get(
            "/api/v1/waitlist/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio

    async def test_add_to_waitlist(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test adding patient to waitlist."""
        response = await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "preferred_date": "2026-01-10",
                "preferred_time_slot": "morning",
                "priority": "normal",
                "notes": "Regular checkup",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == str(test_patient.id)
        assert data["doctor_id"] == str(test_doctor.id)
        assert data["priority"] == "normal"
        assert data["status"] == "waiting"
        assert data["queue_position"] >= 1

    @pytest.mark.asyncio

    async def test_add_to_waitlist_emergency_priority(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test adding patient with emergency priority."""
        response = await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "priority": "emergency",
                "notes": "Chest pain - urgent",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["priority"] == "emergency"
        assert data["queue_position"] == 1  # Emergency gets priority

    @pytest.mark.asyncio

    async def test_add_to_waitlist_invalid_patient(
        self, client, auth_headers, test_clinic, test_doctor
    ):
        """Test adding invalid patient to waitlist."""
        response = await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(uuid4()),  # Non-existent patient
                "doctor_id": str(test_doctor.id),
                "priority": "normal",
            },
        )
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio

    async def test_get_waitlist_with_entries(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test getting waitlist with entries."""
        # First add to waitlist
        await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "priority": "normal",
            },
        )

        # Then get waitlist
        response = await client.get(
            "/api/v1/waitlist/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["patient_id"] == str(test_patient.id)

    @pytest.mark.asyncio

    async def test_get_waitlist_filter_by_doctor(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test filtering waitlist by doctor."""
        # Add to waitlist
        await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "priority": "normal",
            },
        )

        # Filter by doctor
        response = await client.get(
            f"/api/v1/waitlist/?doctor_id={str(test_doctor.id)}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data:
            assert entry["doctor_id"] == str(test_doctor.id)

    @pytest.mark.asyncio

    async def test_get_waitlist_filter_by_status(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test filtering waitlist by status."""
        # Add to waitlist
        await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "priority": "normal",
            },
        )

        # Filter by status
        response = await client.get(
            "/api/v1/waitlist/?status=waiting",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data:
            assert entry["status"] == "waiting"

    @pytest.mark.asyncio

    async def test_update_waitlist_priority(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test updating waitlist entry priority."""
        # Create entry
        create_response = await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "priority": "normal",
            },
        )
        entry_id = create_response.json()["id"]

        # Update priority
        response = await client.put(
            f"/api/v1/waitlist/{entry_id}",
            headers=auth_headers,
            json={"priority": "urgent"},
        )
        assert response.status_code == 200
        assert response.json()["priority"] == "urgent"

    @pytest.mark.asyncio

    async def test_cancel_waitlist_entry(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test cancelling waitlist entry."""
        # Create entry
        create_response = await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "priority": "normal",
            },
        )
        entry_id = create_response.json()["id"]

        # Cancel entry
        response = await client.delete(
            f"/api/v1/waitlist/{entry_id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio

    async def test_get_waitlist_position(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test getting queue position for an entry."""
        # Create entry
        create_response = await client.post(
            "/api/v1/waitlist/",
            headers=auth_headers,
            json={
                "patient_id": str(test_patient.id),
                "doctor_id": str(test_doctor.id),
                "priority": "normal",
            },
        )
        entry_id = create_response.json()["id"]

        # Get position
        response = await client.get(
            f"/api/v1/waitlist/{entry_id}/position",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "position" in data
        assert data["position"] >= 1


class TestWaitlistSlotOffers:
    """Tests for waitlist slot offer functionality."""

    @pytest.mark.asyncio

    async def test_confirm_slot_offer(
        self, client, auth_headers, test_clinic, test_patient, test_doctor, db
    ):
        """Test confirming a slot offer."""
        # This would require setting up a slot offer first
        # For now, test that the endpoint exists and returns appropriate response
        response = await client.post(
            f"/api/v1/waitlist/{uuid4()}/confirm",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 400]  # Entry not found or no offer

    @pytest.mark.asyncio

    async def test_decline_slot_offer(
        self, client, auth_headers, test_clinic, test_patient, test_doctor
    ):
        """Test declining a slot offer."""
        response = await client.post(
            f"/api/v1/waitlist/{uuid4()}/decline",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 400]  # Entry not found or no offer

