"""
Tests for EMR Integration API Endpoints (Phase 13).

Tests EMR sync status, patient timeline, and visit retrieval endpoints.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.procedure import Procedure


class TestEMRStatusEndpoints:
    """Test EMR status and sync endpoints."""

    @pytest.mark.asyncio

    async def test_get_emr_status(self, client, auth_headers):
        """Test getting EMR sync status."""
        response = await client.get(
            "/api/v1/emr/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "enabled" in data
        assert "available" in data
        assert "last_sync_time" in data
        assert "stats" in data
        assert "sync_interval_seconds" in data

    @pytest.mark.asyncio

    async def test_trigger_manual_sync_unavailable(self, client, auth_headers):
        """Test manual sync when EMR is unavailable."""
        response = await client.post(
            "/api/v1/emr/sync/",
            headers=auth_headers,
        )

        # EMR may not be available in test environment
        assert response.status_code == 200
        data = response.json()

        assert "message" in data


class TestPatientEMREndpoints:
    """Test patient-specific EMR endpoints."""

    @pytest.mark.asyncio

    async def test_get_patient_visits_not_found(self, client, auth_headers):
        """Test getting visits for non-existent patient."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/emr/patients/{fake_id}/visits",
            headers=auth_headers,
        )

        # Should return 404 or 503 depending on EMR availability
        assert response.status_code in [404, 503]

    @pytest.mark.asyncio

    async def test_get_patient_prescriptions_not_found(self, client, auth_headers):
        """Test getting prescriptions for non-existent patient."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/emr/patients/{fake_id}/prescriptions",
            headers=auth_headers,
        )

        # Should return 404 or 503 depending on EMR availability
        assert response.status_code in [404, 503]


class TestPatientTimeline:
    """Test patient timeline endpoint."""

    @pytest.mark.asyncio

    async def test_get_patient_timeline_success(
        self,
        client,
        auth_headers,
        test_patient,
        test_appointment,
    ):
        """Test getting patient timeline."""
        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/timeline",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["patient_id"] == str(test_patient.id)
        assert "patient_name" in data
        assert "total_events" in data
        assert "events" in data
        assert "emr_available" in data

        # Should have at least the test appointment
        assert data["total_events"] >= 1

    @pytest.mark.asyncio

    async def test_get_patient_timeline_with_appointment(
        self,
        client,
        auth_headers,
        db,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test timeline with multiple appointments."""
        # Create multiple appointments
        now = datetime.now()
        for i in range(3):
            appointment = Appointment(
                id=str(uuid4()),
                clinic_id=test_clinic.id,
                doctor_id=test_doctor.id,
                patient_id=test_patient.id,
                scheduled_start=now + timedelta(days=i),
                scheduled_end=now + timedelta(days=i, minutes=15),
                status="scheduled",
                appointment_type="follow_up",
            )
            db.add(appointment)
        await db.commit()

        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/timeline",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_events"] >= 3
        assert len(data["events"]) >= 3

        # Check event structure
        event = data["events"][0]
        assert "event_type" in event
        assert "timestamp" in event
        assert "title" in event
        assert "doctor_name" in event
        assert "source" in event

    @pytest.mark.asyncio

    async def test_get_patient_timeline_with_procedure(
        self,
        client,
        auth_headers,
        db,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test timeline with procedures."""
        # Create a procedure
        procedure = Procedure(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            category="Cardiology",
            procedure_type="Echocardiogram",
            name="Stress Echo",
            performed_at=datetime.now(),
            outcome="successful",
            severity="minor",
        )
        db.add(procedure)
        await db.commit()

        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/timeline",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should have procedure in timeline
        assert data["total_events"] >= 1

        # Find procedure event
        procedure_events = [
            e for e in data["events"] if e["event_type"] == "procedure"
        ]
        assert len(procedure_events) >= 1

        proc_event = procedure_events[0]
        assert "Echocardiogram" in proc_event["title"]
        assert proc_event["source"] == "practice_manager"

    @pytest.mark.asyncio

    async def test_get_patient_timeline_filtering(
        self,
        client,
        auth_headers,
        test_patient,
    ):
        """Test timeline with filtering options."""
        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/timeline",
            params={
                "limit": 10,
                "include_appointments": True,
                "include_visits": False,
                "include_procedures": False,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All events should be appointments only
        for event in data["events"]:
            assert event["event_type"] == "appointment"

    @pytest.mark.asyncio

    async def test_get_patient_timeline_not_found(self, client, auth_headers):
        """Test timeline for non-existent patient."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/emr/patients/{fake_id}/timeline",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_get_patient_timeline_limit(
        self,
        client,
        auth_headers,
        db,
        test_clinic,
        test_doctor,
        test_patient,
    ):
        """Test timeline limit parameter."""
        # Create 10 appointments
        now = datetime.now()
        for i in range(10):
            appointment = Appointment(
                id=str(uuid4()),
                clinic_id=test_clinic.id,
                doctor_id=test_doctor.id,
                patient_id=test_patient.id,
                scheduled_start=now + timedelta(days=i),
                scheduled_end=now + timedelta(days=i, minutes=15),
                status="scheduled",
                appointment_type="follow_up",
            )
            db.add(appointment)
        await db.commit()

        # Request only 5 events
        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/timeline",
            params={"limit": 5},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should return at most 5 events
        assert len(data["events"]) <= 5


class TestAppointmentVisitLinking:
    """Test appointment-visit linking endpoints."""

    @pytest.mark.asyncio

    async def test_link_appointment_to_visit_not_found(self, client, auth_headers):
        """Test linking non-existent appointment."""
        fake_appointment_id = str(uuid4())
        fake_visit_id = "visit-123"

        response = await client.post(
            f"/api/v1/emr/appointments/{fake_appointment_id}/link-visit/{fake_visit_id}",
            headers=auth_headers,
        )

        # Should return 400 or 503 depending on EMR availability
        assert response.status_code in [400, 503]

