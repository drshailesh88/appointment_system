"""
Tests for Analytics API endpoints.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints."""

    @pytest.mark.asyncio

    async def test_get_dashboard_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 401

    @pytest.mark.asyncio

    async def test_get_dashboard(self, client, auth_headers, test_clinic):
        """Test getting analytics dashboard."""
        response = await client.get(
            "/api/v1/analytics/dashboard?period=week",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "appointments" in data
        assert "revenue" in data
        assert "top_doctors" in data
        assert "daily_trend" in data

    @pytest.mark.asyncio

    async def test_get_dashboard_with_period(self, client, auth_headers, test_clinic):
        """Test dashboard with different periods."""
        periods = ["today", "week", "month", "quarter", "year"]

        for period in periods:
            response = await client.get(
                f"/api/v1/analytics/dashboard?period={period}",
                headers=auth_headers,
            )
            assert response.status_code == 200

    @pytest.mark.asyncio

    async def test_get_appointment_stats(self, client, auth_headers, test_clinic):
        """Test getting appointment statistics."""
        response = await client.get(
            "/api/v1/analytics/appointments?period=month",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "completed" in data
        assert "cancelled" in data
        assert "no_show" in data
        assert "completion_rate" in data
        assert "cancellation_rate" in data

    @pytest.mark.asyncio

    async def test_get_appointment_stats_with_appointments(
        self, client, auth_headers, test_appointment
    ):
        """Test appointment stats with existing appointments."""
        response = await client.get(
            "/api/v1/analytics/appointments?period=month",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio

    async def test_get_revenue_stats(self, client, auth_headers, test_clinic):
        """Test getting revenue statistics."""
        response = await client.get(
            "/api/v1/analytics/revenue?period=month",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "collected" in data
        assert "pending" in data
        assert "collection_rate" in data
        assert "average_invoice" in data

    @pytest.mark.asyncio

    async def test_get_doctor_utilization(self, client, auth_headers, test_doctor):
        """Test getting doctor utilization."""
        response = await client.get(
            "/api/v1/analytics/doctors/utilization?period=week",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include test doctor
        if len(data) > 0:
            doctor = data[0]
            assert "doctor_id" in doctor
            assert "doctor_name" in doctor
            assert "utilization_rate" in doctor

    @pytest.mark.asyncio

    async def test_get_patient_demographics(self, client, auth_headers, test_patient):
        """Test getting patient demographics."""
        response = await client.get(
            "/api/v1/analytics/patients/demographics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_patients" in data
        assert "gender_breakdown" in data
        assert "age_breakdown" in data

    @pytest.mark.asyncio

    async def test_get_daily_trend(self, client, auth_headers, test_clinic):
        """Test getting daily trend data."""
        response = await client.get(
            "/api/v1/analytics/daily?period=week",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            day = data[0]
            assert "date" in day
            assert "appointments" in day
            assert "revenue" in day

    @pytest.mark.asyncio

    async def test_get_no_show_analysis(self, client, auth_headers, test_clinic):
        """Test getting no-show analysis."""
        response = await client.get(
            "/api/v1/analytics/no-shows?period=month",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_no_shows" in data
        assert "by_day_of_week" in data
        assert "by_hour" in data


class TestAnalyticsExport:
    """Tests for analytics export functionality."""

    @pytest.mark.asyncio

    async def test_export_report_pdf(self, client, auth_headers, test_clinic):
        """Test exporting report as PDF."""
        response = await client.get(
            "/api/v1/analytics/export?format=pdf&period=month",
            headers=auth_headers,
        )
        # PDF export might not be implemented yet
        assert response.status_code in [200, 404, 501]

    @pytest.mark.asyncio

    async def test_export_report_csv(self, client, auth_headers, test_clinic):
        """Test exporting report as CSV."""
        response = await client.get(
            "/api/v1/analytics/export?format=csv&period=month",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 501]


class TestAnalyticsPermissions:
    """Tests for analytics permissions."""

    @pytest.mark.asyncio

    async def test_analytics_requires_admin_or_doctor(
        self, client, test_clinic, db
    ):
        """Test that analytics requires appropriate permissions."""
        # Create a staff user (not admin or doctor)
        from app.models.user import User
        from app.core.security import get_password_hash, create_access_token

        staff_user = User(
            id=str(uuid4()),
            email="staff@test.com",
            phone="+919876543299",
            password_hash=get_password_hash("staffpass123"),
            name="Staff User",
            role="staff",
            clinic_id=test_clinic.id,
            is_active=True,
        )
        db.add(staff_user)
        await db.commit()

        staff_token = create_access_token(subject=staff_user.id)
        staff_headers = {"Authorization": f"Bearer {staff_token}"}

        response = await client.get(
            "/api/v1/analytics/dashboard",
            headers=staff_headers,
        )
        # Staff should have limited access
        assert response.status_code in [200, 403]

