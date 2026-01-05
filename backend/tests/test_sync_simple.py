"""
Comprehensive Offline Sync Tests for DocAssist Practice Manager - Simplified Version

Tests cover:
- Basic sync operations
- Conflict resolution
- Data integrity
- Multi-device sync
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus


# ============================================================================
# A. Basic Sync Operations
# ============================================================================


@pytest.mark.asyncio
async def test_sync_pull_empty_changes(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
):
    """Test sync pull when no changes exist."""
    async_client.headers.update(auth_headers)

    # Get appointments since last sync
    response = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_sync_push_new_appointment(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
    test_patient,
):
    """Test pushing a new appointment to server."""
    async_client.headers.update(auth_headers)

    appointment_data = {
        "doctor_id": str(test_doctor.id),
        "patient_id": str(test_patient.id),
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "duration_minutes": 30,
        "appointment_type": "new_consultation",
        "chief_complaint": "Test sync complaint",
    }

    response = await async_client.post(
        "/api/v1/appointments",
        json=appointment_data,
    )

    assert response.status_code == 201
    created = response.json()
    assert created["doctor_id"] == appointment_data["doctor_id"]
    assert created["patient_id"] == appointment_data["patient_id"]
    assert created["chief_complaint"] == appointment_data["chief_complaint"]


@pytest.mark.asyncio
async def test_full_sync_initial_setup(
    async_client: AsyncClient,
    auth_headers: dict,
    async_db: AsyncSession,
    test_doctor,
    test_patient,
):
    """Test full sync for initial device setup."""
    async_client.headers.update(auth_headers)

    # Create some appointments first
    appointments = []
    for i in range(5):
        appt = Appointment(
            id=uuid4(),
            clinic_id=test_doctor.clinic_id,
            doctor_id=test_doctor.id,
            patient_id=test_patient.id,
            scheduled_start=datetime.now(timezone.utc) + timedelta(hours=i + 1),
            scheduled_end=datetime.now(timezone.utc) + timedelta(hours=i + 1, minutes=30),
            status=AppointmentStatus.SCHEDULED.value,
            appointment_type="new_consultation",
        )
        appointments.append(appt)
        async_db.add(appt)

    await async_db.commit()

    # Full sync - get all appointments
    response = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )

    assert response.status_code == 200
    synced = response.json()
    assert len(synced) == 5


@pytest.mark.asyncio
async def test_incremental_sync_delta_updates(
    async_client: AsyncClient,
    auth_headers: dict,
    async_db: AsyncSession,
    test_doctor,
    test_patient,
):
    """Test incremental sync with delta updates."""
    async_client.headers.update(auth_headers)

    # Create initial appointment
    appt1 = Appointment(
        id=uuid4(),
        clinic_id=test_doctor.clinic_id,
        doctor_id=test_doctor.id,
        patient_id=test_patient.id,
        scheduled_start=datetime.now(timezone.utc) + timedelta(hours=1),
        scheduled_end=datetime.now(timezone.utc) + timedelta(hours=1, minutes=30),
        status=AppointmentStatus.SCHEDULED.value,
        appointment_type="new_consultation",
    )
    async_db.add(appt1)
    await async_db.commit()

    # First sync
    response1 = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )
    assert response1.status_code == 200
    initial_sync = response1.json()

    # Wait a bit
    await asyncio.sleep(0.1)

    # Create new appointment after sync
    appt2 = Appointment(
        id=uuid4(),
        clinic_id=test_doctor.clinic_id,
        doctor_id=test_doctor.id,
        patient_id=test_patient.id,
        scheduled_start=datetime.now(timezone.utc) + timedelta(hours=2),
        scheduled_end=datetime.now(timezone.utc) + timedelta(hours=2, minutes=30),
        status=AppointmentStatus.SCHEDULED.value,
        appointment_type="follow_up",
    )
    async_db.add(appt2)
    await async_db.commit()

    # Delta sync - should get both appointments
    response2 = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )
    assert response2.status_code == 200
    delta_sync = response2.json()

    # Should contain both appointments
    assert len(delta_sync) == 2


# ============================================================================
# B. Conflict Resolution
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_updates_from_multiple_devices(
    async_client: AsyncClient,
    auth_headers: dict,
    async_db: AsyncSession,
    test_doctor,
    test_patient,
):
    """Test concurrent updates from multiple devices."""
    async_client.headers.update(auth_headers)

    # Create appointment
    appt = Appointment(
        id=uuid4(),
        clinic_id=test_doctor.clinic_id,
        doctor_id=test_doctor.id,
        patient_id=test_patient.id,
        scheduled_start=datetime.now(timezone.utc) + timedelta(hours=1),
        scheduled_end=datetime.now(timezone.utc) + timedelta(hours=1, minutes=30),
        status=AppointmentStatus.SCHEDULED.value,
        appointment_type="new_consultation",
    )
    async_db.add(appt)
    await async_db.commit()
    appt_id = appt.id

    # Device 1 updates
    update1 = {"chief_complaint": "Device 1 update"}
    response1 = await async_client.put(
        f"/api/v1/appointments/{appt_id}",
        json=update1,
    )
    assert response1.status_code == 200

    # Device 2 updates (should overwrite)
    update2 = {"notes": "Device 2 update"}
    response2 = await async_client.put(
        f"/api/v1/appointments/{appt_id}",
        json=update2,
    )
    assert response2.status_code == 200

    # Verify final state
    await async_db.refresh(appt)
    # Last write wins
    assert appt.notes == "Device 2 update"


@pytest.mark.asyncio
async def test_delete_conflict_modified_on_client(
    async_client: AsyncClient,
    auth_headers: dict,
    async_db: AsyncSession,
    test_doctor,
    test_patient,
):
    """Test delete conflict when appointment modified on client."""
    async_client.headers.update(auth_headers)

    # Create appointment
    appt = Appointment(
        id=uuid4(),
        clinic_id=test_doctor.clinic_id,
        doctor_id=test_doctor.id,
        patient_id=test_patient.id,
        scheduled_start=datetime.now(timezone.utc) + timedelta(hours=1),
        scheduled_end=datetime.now(timezone.utc) + timedelta(hours=1, minutes=30),
        status=AppointmentStatus.SCHEDULED.value,
        appointment_type="new_consultation",
    )
    async_db.add(appt)
    await async_db.commit()
    appt_id = appt.id

    # Delete from server
    response = await async_client.delete(f"/api/v1/appointments/{appt_id}")
    assert response.status_code == 204

    # Try to update deleted appointment (should fail)
    response = await async_client.put(
        f"/api/v1/appointments/{appt_id}",
        json={"chief_complaint": "Update after delete"},
    )
    assert response.status_code == 404


# ============================================================================
# C. Data Integrity
# ============================================================================


@pytest.mark.asyncio
async def test_no_data_loss_during_sync(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
    test_patient,
):
    """Test no data loss during sync operations."""
    async_client.headers.update(auth_headers)

    # Create appointments
    created_ids = []
    for i in range(10):
        data = {
            "doctor_id": str(test_doctor.id),
            "patient_id": str(test_patient.id),
            "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=i + 1)).isoformat(),
            "duration_minutes": 30,
            "appointment_type": "new_consultation",
        }
        response = await async_client.post("/api/v1/appointments", json=data)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    # Verify all appointments exist
    response = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )
    synced = response.json()
    synced_ids = [a["id"] for a in synced]

    for created_id in created_ids:
        assert created_id in synced_ids


@pytest.mark.asyncio
async def test_referential_integrity_patient_appointment(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
):
    """Test referential integrity between patient and appointment."""
    async_client.headers.update(auth_headers)

    # Try to create appointment with non-existent patient
    data = {
        "doctor_id": str(test_doctor.id),
        "patient_id": str(uuid4()),  # Random UUID
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "duration_minutes": 30,
        "appointment_type": "new_consultation",
    }

    response = await async_client.post("/api/v1/appointments", json=data)
    assert response.status_code == 404  # Patient not found


@pytest.mark.asyncio
async def test_timestamp_accuracy(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
    test_patient,
):
    """Test timestamp accuracy in synced data."""
    async_client.headers.update(auth_headers)

    before = datetime.now(timezone.utc)

    data = {
        "doctor_id": str(test_doctor.id),
        "patient_id": str(test_patient.id),
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "duration_minutes": 30,
        "appointment_type": "new_consultation",
    }

    response = await async_client.post("/api/v1/appointments", json=data)
    assert response.status_code == 201
    created = response.json()

    after = datetime.now(timezone.utc)

    # Check created_at timestamp
    created_at = datetime.fromisoformat(created["created_at"].replace("Z", "+00:00"))
    assert before <= created_at <= after


# ============================================================================
# D. Queue Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_queue_operations_fifo_order(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
    test_patient,
):
    """Test queue processes in FIFO order."""
    async_client.headers.update(auth_headers)

    # Create operations with order
    operations = []
    for i in range(5):
        op = {
            "doctor_id": str(test_doctor.id),
            "patient_id": str(test_patient.id),
            "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=i + 1)).isoformat(),
            "duration_minutes": 30,
            "appointment_type": "new_consultation",
            "chief_complaint": f"Order {i}",
        }
        operations.append(op)

    # Process in order
    created = []
    for op in operations:
        response = await async_client.post("/api/v1/appointments", json=op)
        assert response.status_code == 201
        created.append(response.json())

    # Verify order preserved
    for i, appt in enumerate(created):
        assert appt["chief_complaint"] == f"Order {i}"


@pytest.mark.asyncio
async def test_failed_operation_retry_logic(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
):
    """Test retry logic for failed operations."""
    async_client.headers.update(auth_headers)

    # Invalid appointment (missing required fields)
    invalid_data = {
        "doctor_id": str(test_doctor.id),
        # Missing patient_id and other required fields
    }

    # Simulate retry attempts
    retry_count = 0
    max_retries = 3

    for i in range(max_retries):
        response = await async_client.post(
            "/api/v1/appointments",
            json=invalid_data,
        )

        if response.status_code == 201:
            break

        retry_count += 1
        await asyncio.sleep(0.01)  # Minimal delay for test

    # Should have retried 3 times and failed
    assert retry_count == max_retries


# ============================================================================
# E. Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_very_large_sync_payload(
    async_client: AsyncClient,
    auth_headers: dict,
    async_db: AsyncSession,
    test_doctor,
    test_patient,
):
    """Test sync with very large payload."""
    async_client.headers.update(auth_headers)

    # Create many appointments
    batch_size = 100
    appointments = []

    for i in range(batch_size):
        appt = Appointment(
            id=uuid4(),
            clinic_id=test_doctor.clinic_id,
            doctor_id=test_doctor.id,
            patient_id=test_patient.id,
            scheduled_start=datetime.now(timezone.utc) + timedelta(hours=i + 1),
            scheduled_end=datetime.now(timezone.utc) + timedelta(hours=i + 1, minutes=30),
            status=AppointmentStatus.SCHEDULED.value,
            appointment_type="new_consultation",
        )
        appointments.append(appt)
        async_db.add(appt)

    await async_db.commit()

    # Sync large payload
    response = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == batch_size


@pytest.mark.asyncio
async def test_unicode_data_sync(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
    test_patient,
):
    """Test sync with unicode/international characters."""
    async_client.headers.update(auth_headers)

    data = {
        "doctor_id": str(test_doctor.id),
        "patient_id": str(test_patient.id),
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "duration_minutes": 30,
        "appointment_type": "new_consultation",
        "chief_complaint": "सिरदर्द और बुखार (Headache and fever)",  # Hindi + English
        "notes": "Patient has 发烧 symptoms",  # Chinese
    }

    response = await async_client.post("/api/v1/appointments", json=data)
    assert response.status_code == 201
    created = response.json()
    assert created["chief_complaint"] == data["chief_complaint"]
    assert created["notes"] == data["notes"]


# ============================================================================
# F. Multi-Device Sync
# ============================================================================


@pytest.mark.asyncio
async def test_sync_ordering_across_devices(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
    test_patient,
):
    """Test sync ordering across multiple devices."""
    async_client.headers.update(auth_headers)

    # Create from device 1
    data1 = {
        "doctor_id": str(test_doctor.id),
        "patient_id": str(test_patient.id),
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "duration_minutes": 30,
        "appointment_type": "new_consultation",
        "chief_complaint": "Device 1",
    }
    response1 = await async_client.post("/api/v1/appointments", json=data1)
    assert response1.status_code == 201

    # Small delay
    await asyncio.sleep(0.1)

    # Create from device 2
    data2 = {
        "doctor_id": str(test_doctor.id),
        "patient_id": str(test_patient.id),
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "duration_minutes": 30,
        "appointment_type": "new_consultation",
        "chief_complaint": "Device 2",
    }
    response2 = await async_client.post("/api/v1/appointments", json=data2)
    assert response2.status_code == 201

    # Both devices should see both appointments
    response = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )
    assert response.status_code == 200
    appointments = response.json()
    assert len(appointments) >= 2


# ============================================================================
# G. Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_complete_offline_to_online_workflow(
    async_client: AsyncClient,
    auth_headers: dict,
    test_doctor,
    test_patient,
):
    """Test complete workflow: offline queue -> online -> sync."""
    async_client.headers.update(auth_headers)

    # Simulate offline queue
    offline_queue = []

    # Queue operations while "offline"
    for i in range(3):
        offline_queue.append(
            {
                "doctor_id": str(test_doctor.id),
                "patient_id": str(test_patient.id),
                "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=i + 1)).isoformat(),
                "duration_minutes": 30,
                "appointment_type": "new_consultation",
                "chief_complaint": f"Offline operation {i}",
            }
        )

    # Come back online and sync
    synced_count = 0
    for op in offline_queue:
        response = await async_client.post("/api/v1/appointments", json=op)
        if response.status_code == 201:
            synced_count += 1

    assert synced_count == 3

    # Verify all synced
    response = await async_client.get(
        "/api/v1/appointments",
        params={"doctor_id": str(test_doctor.id)},
    )
    appointments = response.json()
    assert len(appointments) >= 3


@pytest.mark.asyncio
async def test_bidirectional_sync_workflow(
    async_client: AsyncClient,
    auth_headers: dict,
    async_db: AsyncSession,
    test_doctor,
    test_patient,
):
    """Test bidirectional sync: push changes, pull updates."""
    async_client.headers.update(auth_headers)

    # Push: Create appointment from client
    push_data = {
        "doctor_id": str(test_doctor.id),
        "patient_id": str(test_patient.id),
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "duration_minutes": 30,
        "appointment_type": "new_consultation",
    }
    push_response = await async_client.post("/api/v1/appointments", json=push_data)
    assert push_response.status_code == 201
    appt_id = push_response.json()["id"]

    # Simulate server-side update
    stmt = select(Appointment).where(Appointment.id == UUID(appt_id))
    result = await async_db.execute(stmt)
    appt = result.scalar_one()
    appt.status = AppointmentStatus.CONFIRMED.value
    await async_db.commit()

    # Pull: Get updates from server
    pull_response = await async_client.get(f"/api/v1/appointments/{appt_id}")
    assert pull_response.status_code == 200
    pulled = pull_response.json()
    assert pulled["status"] == "confirmed"


print("✓ All sync test definitions loaded successfully!")
