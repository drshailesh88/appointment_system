"""
Tests for Waitlist Service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from app.services.waitlist import (
    WaitlistService,
    WaitlistPriority,
    WaitlistStatus,
    get_waitlist_service,
)


class TestWaitlistService:
    """Tests for WaitlistService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_sms_service(self):
        """Create mock SMS service."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db, mock_sms_service):
        """Create waitlist service with mocks."""
        service = WaitlistService(mock_db)
        service.sms_service = mock_sms_service
        return service

    def test_initialization(self, mock_db):
        """Test service initialization."""
        service = WaitlistService(mock_db)
        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_add_to_waitlist(self, service, mock_db):
        """Test adding patient to waitlist."""
        patient_id = str(uuid4())
        doctor_id = str(uuid4())
        clinic_id = str(uuid4())

        # Mock patient query
        mock_patient = MagicMock()
        mock_patient.id = patient_id
        mock_patient.name = "Test Patient"
        mock_patient.phone = "+919876543210"
        mock_db.get.return_value = mock_patient

        # Mock queue position query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_count_result

        entry = await service.add_to_waitlist(
            patient_id=patient_id,
            doctor_id=doctor_id,
            clinic_id=clinic_id,
            preferred_date="2026-01-10",
            preferred_time_slot="morning",
            priority=WaitlistPriority.NORMAL,
            notes="Urgent checkup needed",
        )

        assert entry is not None
        assert entry.patient_id == patient_id
        assert entry.doctor_id == doctor_id
        assert entry.priority == WaitlistPriority.NORMAL
        assert entry.status == WaitlistStatus.WAITING
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_add_to_waitlist_invalid_patient(self, service, mock_db):
        """Test adding invalid patient to waitlist."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Patient not found"):
            await service.add_to_waitlist(
                patient_id="invalid-id",
                doctor_id=str(uuid4()),
                clinic_id=str(uuid4()),
            )

    @pytest.mark.asyncio
    async def test_get_queue_position(self, service, mock_db):
        """Test getting queue position."""
        entry_id = str(uuid4())
        doctor_id = str(uuid4())

        # Mock entry
        mock_entry = MagicMock()
        mock_entry.id = entry_id
        mock_entry.doctor_id = doctor_id
        mock_entry.priority = WaitlistPriority.NORMAL
        mock_entry.created_at = datetime.now()
        mock_entry.status = WaitlistStatus.WAITING

        mock_db.get.return_value = mock_entry

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3
        mock_db.execute.return_value = mock_count_result

        position = await service.get_queue_position(entry_id)
        assert position == 4  # 3 ahead + 1

    @pytest.mark.asyncio
    async def test_process_cancelled_slot(self, service, mock_db, mock_sms_service):
        """Test processing a cancelled slot."""
        doctor_id = str(uuid4())
        slot_time = datetime.now() + timedelta(days=1)

        # Mock waiting entries query
        mock_entry = MagicMock()
        mock_entry.id = str(uuid4())
        mock_entry.patient_id = str(uuid4())
        mock_entry.status = WaitlistStatus.WAITING
        mock_entry.priority = WaitlistPriority.NORMAL

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_entry
        mock_db.execute.return_value = mock_result

        # Mock patient for notification
        mock_patient = MagicMock()
        mock_patient.name = "Test Patient"
        mock_patient.phone = "+919876543210"
        mock_db.get.return_value = mock_patient

        result = await service.process_cancelled_slot(
            doctor_id=doctor_id,
            slot_time=slot_time,
        )

        assert result is not None
        assert mock_entry.status == WaitlistStatus.OFFERED
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_cancelled_slot_no_waiting(self, service, mock_db):
        """Test processing cancelled slot with no waiting patients."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.process_cancelled_slot(
            doctor_id=str(uuid4()),
            slot_time=datetime.now() + timedelta(days=1),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_confirm_slot(self, service, mock_db):
        """Test confirming a slot offer."""
        entry_id = str(uuid4())

        mock_entry = MagicMock()
        mock_entry.id = entry_id
        mock_entry.status = WaitlistStatus.OFFERED
        mock_entry.offered_slot_time = datetime.now() + timedelta(days=1)
        mock_entry.slot_offer_expires_at = datetime.now() + timedelta(minutes=30)
        mock_entry.patient_id = str(uuid4())
        mock_entry.doctor_id = str(uuid4())
        mock_entry.clinic_id = str(uuid4())

        mock_db.get.return_value = mock_entry

        appointment = await service.confirm_slot(entry_id)

        assert appointment is not None
        assert mock_entry.status == WaitlistStatus.CONFIRMED
        mock_db.add.assert_called()  # For new appointment
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_confirm_slot_expired(self, service, mock_db):
        """Test confirming an expired slot offer."""
        entry_id = str(uuid4())

        mock_entry = MagicMock()
        mock_entry.id = entry_id
        mock_entry.status = WaitlistStatus.OFFERED
        mock_entry.slot_offer_expires_at = datetime.now() - timedelta(minutes=5)

        mock_db.get.return_value = mock_entry

        with pytest.raises(ValueError, match="Slot offer has expired"):
            await service.confirm_slot(entry_id)

    @pytest.mark.asyncio
    async def test_confirm_slot_wrong_status(self, service, mock_db):
        """Test confirming slot with wrong status."""
        entry_id = str(uuid4())

        mock_entry = MagicMock()
        mock_entry.id = entry_id
        mock_entry.status = WaitlistStatus.WAITING

        mock_db.get.return_value = mock_entry

        with pytest.raises(ValueError, match="No slot offer pending"):
            await service.confirm_slot(entry_id)

    @pytest.mark.asyncio
    async def test_decline_slot(self, service, mock_db):
        """Test declining a slot offer."""
        entry_id = str(uuid4())

        mock_entry = MagicMock()
        mock_entry.id = entry_id
        mock_entry.status = WaitlistStatus.OFFERED
        mock_entry.doctor_id = str(uuid4())
        mock_entry.offered_slot_time = datetime.now() + timedelta(days=1)

        mock_db.get.return_value = mock_entry

        # Mock next waiting entry
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.decline_slot(entry_id)

        assert mock_entry.status == WaitlistStatus.WAITING
        assert mock_entry.offered_slot_time is None
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_waitlist_entry(self, service, mock_db):
        """Test cancelling a waitlist entry."""
        entry_id = str(uuid4())

        mock_entry = MagicMock()
        mock_entry.id = entry_id
        mock_entry.status = WaitlistStatus.WAITING

        mock_db.get.return_value = mock_entry

        await service.cancel_entry(entry_id)

        assert mock_entry.status == WaitlistStatus.CANCELLED
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_waitlist_by_doctor(self, service, mock_db):
        """Test getting waitlist for a doctor."""
        doctor_id = str(uuid4())

        mock_entries = [
            MagicMock(
                id=str(uuid4()),
                patient_id=str(uuid4()),
                status=WaitlistStatus.WAITING,
                priority=WaitlistPriority.URGENT,
            ),
            MagicMock(
                id=str(uuid4()),
                patient_id=str(uuid4()),
                status=WaitlistStatus.WAITING,
                priority=WaitlistPriority.NORMAL,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_entries
        mock_db.execute.return_value = mock_result

        entries = await service.get_waitlist(doctor_id=doctor_id)

        assert len(entries) == 2
        mock_db.execute.assert_called_once()


class TestWaitlistPriority:
    """Tests for WaitlistPriority enum."""

    def test_priority_values(self):
        """Test priority enum values."""
        assert WaitlistPriority.EMERGENCY.value == "emergency"
        assert WaitlistPriority.URGENT.value == "urgent"
        assert WaitlistPriority.NORMAL.value == "normal"
        assert WaitlistPriority.FLEXIBLE.value == "flexible"

    def test_priority_ordering(self):
        """Test that priorities can be compared for queue ordering."""
        priorities = [
            WaitlistPriority.NORMAL,
            WaitlistPriority.EMERGENCY,
            WaitlistPriority.URGENT,
            WaitlistPriority.FLEXIBLE,
        ]

        # Expected order: emergency, urgent, normal, flexible
        expected_order = [
            WaitlistPriority.EMERGENCY,
            WaitlistPriority.URGENT,
            WaitlistPriority.NORMAL,
            WaitlistPriority.FLEXIBLE,
        ]

        sorted_priorities = sorted(
            priorities,
            key=lambda p: ["emergency", "urgent", "normal", "flexible"].index(p.value)
        )
        assert sorted_priorities == expected_order


class TestWaitlistStatus:
    """Tests for WaitlistStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert WaitlistStatus.WAITING.value == "waiting"
        assert WaitlistStatus.OFFERED.value == "offered"
        assert WaitlistStatus.CONFIRMED.value == "confirmed"
        assert WaitlistStatus.EXPIRED.value == "expired"
        assert WaitlistStatus.CANCELLED.value == "cancelled"


class TestGetWaitlistService:
    """Tests for factory function."""

    def test_creates_service(self):
        """Test that factory creates service."""
        mock_db = AsyncMock()
        service = get_waitlist_service(mock_db)
        assert isinstance(service, WaitlistService)
        assert service.db == mock_db
