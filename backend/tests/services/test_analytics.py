"""
Tests for Analytics Service.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from app.services.analytics import (
    AnalyticsService,
    AppointmentStats,
    RevenueStats,
    DoctorUtilization,
    DailyMetric,
    PatientDemographics,
    get_analytics_service,
)


class TestAppointmentStats:
    """Tests for AppointmentStats dataclass."""

    def test_create_stats(self):
        """Test creating appointment stats."""
        stats = AppointmentStats(
            total=100,
            completed=80,
            cancelled=10,
            no_show=5,
            scheduled=5,
            completion_rate=80.0,
            cancellation_rate=10.0,
            no_show_rate=5.0,
        )
        assert stats.total == 100
        assert stats.completed == 80
        assert stats.completion_rate == 80.0


class TestRevenueStats:
    """Tests for RevenueStats dataclass."""

    def test_create_stats(self):
        """Test creating revenue stats."""
        stats = RevenueStats(
            total_revenue=Decimal("50000"),
            collected=Decimal("45000"),
            pending=Decimal("5000"),
            refunded=Decimal("0"),
            collection_rate=90.0,
            average_invoice=Decimal("500"),
        )
        assert stats.total_revenue == Decimal("50000")
        assert stats.collection_rate == 90.0


class TestDoctorUtilization:
    """Tests for DoctorUtilization dataclass."""

    def test_create_utilization(self):
        """Test creating doctor utilization."""
        util = DoctorUtilization(
            doctor_id=uuid4(),
            doctor_name="Dr. Sharma",
            total_slots=160,
            booked_slots=120,
            completed_appointments=100,
            utilization_rate=75.0,
            average_duration_minutes=15.5,
            revenue_generated=Decimal("10000"),
        )
        assert util.doctor_name == "Dr. Sharma"
        assert util.utilization_rate == 75.0


class TestDailyMetric:
    """Tests for DailyMetric dataclass."""

    def test_create_metric(self):
        """Test creating daily metric."""
        metric = DailyMetric(
            date=date.today(),
            appointments=25,
            revenue=Decimal("12500"),
            new_patients=5,
        )
        assert metric.appointments == 25
        assert metric.new_patients == 5


class TestPatientDemographics:
    """Tests for PatientDemographics dataclass."""

    def test_create_demographics(self):
        """Test creating patient demographics."""
        demo = PatientDemographics(
            total_patients=500,
            new_this_period=50,
            gender_breakdown={"male": 250, "female": 240, "other": 10},
            age_breakdown={"0-18": 50, "19-40": 200, "41-60": 150, "60+": 100},
            city_breakdown={"Mumbai": 300, "Thane": 150, "Navi Mumbai": 50},
        )
        assert demo.total_patients == 500
        assert demo.gender_breakdown["male"] == 250


class TestAnalyticsService:
    """Tests for AnalyticsService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create analytics service with mock db."""
        return AnalyticsService(mock_db)

    def test_initialization(self, mock_db):
        """Test service initialization."""
        service = AnalyticsService(mock_db)
        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_get_appointment_stats(self, service, mock_db):
        """Test getting appointment stats."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            total=100,
            completed=80,
            cancelled=10,
            no_show=5,
            scheduled=5,
        )
        mock_db.execute.return_value = mock_result

        clinic_id = uuid4()
        stats = await service.get_appointment_stats(
            clinic_id=clinic_id,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        assert stats.total == 100
        assert stats.completed == 80
        assert stats.completion_rate == 80.0

    @pytest.mark.asyncio
    async def test_get_revenue_stats(self, service, mock_db):
        """Test getting revenue stats."""
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(
            count=100,
            total=50000,
            paid=45000,
        )
        mock_db.execute.return_value = mock_result

        clinic_id = uuid4()
        stats = await service.get_revenue_stats(
            clinic_id=clinic_id,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        assert stats.total_revenue == Decimal("50000")
        assert stats.collected == Decimal("45000")

    @pytest.mark.asyncio
    async def test_get_patient_demographics(self, service, mock_db):
        """Test getting patient demographics."""
        # Mock multiple query results
        mock_db.execute.side_effect = [
            # Total patients
            MagicMock(scalar=MagicMock(return_value=500)),
            # New patients
            MagicMock(scalar=MagicMock(return_value=50)),
            # Gender breakdown
            MagicMock(all=MagicMock(return_value=[
                MagicMock(gender="male", count=250),
                MagicMock(gender="female", count=250),
            ])),
            # City breakdown
            MagicMock(all=MagicMock(return_value=[
                MagicMock(city="Mumbai", count=500),
            ])),
        ]

        clinic_id = uuid4()
        demo = await service.get_patient_demographics(
            clinic_id=clinic_id,
            start_date=date.today() - timedelta(days=30),
        )

        assert demo.total_patients == 500
        assert demo.new_this_period == 50

    @pytest.mark.asyncio
    async def test_get_no_show_analysis_empty(self, service, mock_db):
        """Test no-show analysis with no data."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        clinic_id = uuid4()
        analysis = await service.get_no_show_analysis(
            clinic_id=clinic_id,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        assert analysis["total_no_shows"] == 0
        assert analysis["worst_day"] is None


class TestGetAnalyticsService:
    """Tests for factory function."""

    def test_creates_service(self):
        """Test that factory creates service."""
        mock_db = AsyncMock()
        service = get_analytics_service(mock_db)
        assert isinstance(service, AnalyticsService)
        assert service.db == mock_db
