"""
Tests for patient endpoints.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestPatients:
    """Patient endpoint tests."""

    @pytest.mark.asyncio

    async def test_create_patient(
        self,
        client: AsyncClient,
        auth_headers,
        test_clinic,
    ):
        """Test creating a new patient."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "name": "New Patient",
                "phone": "+919876543299",
                "email": "newpatient@test.com",
                "gender": "female",
                "date_of_birth": "1985-05-20",
                "address": "New Address",
                "city": "Mumbai",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Patient"
        assert data["phone"] == "+919876543299"

    @pytest.mark.asyncio

    async def test_create_patient_duplicate_phone(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
    ):
        """Test creating patient with duplicate phone."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "name": "Duplicate Patient",
                "phone": test_patient.phone,
                "gender": "male",
            },
        )
        assert response.status_code in [400, 409]

    @pytest.mark.asyncio

    async def test_get_patient_by_id(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
    ):
        """Test getting patient by ID."""
        response = await client.get(
            f"/api/v1/patients/{test_patient.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_patient.id)
        assert data["full_name"] == test_patient.full_name

    @pytest.mark.asyncio

    async def test_get_patient_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test getting non-existent patient."""
        response = await client.get(
            f"/api/v1/patients/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_search_patients(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
    ):
        """Test searching patients."""
        response = await client.get(
            f"/api/v1/patients/search?q={test_patient.first_name[:4]}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(p["id"] == str(test_patient.id) for p in data)

    @pytest.mark.asyncio

    async def test_search_patients_by_phone(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
    ):
        """Test searching patients by phone."""
        response = await client.get(
            f"/api/v1/patients/search?q={test_patient.phone[-4:]}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_search_patients_min_length(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test search with query too short."""
        response = await client.get(
            "/api/v1/patients/search?q=a",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio

    async def test_update_patient(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
    ):
        """Test updating patient."""
        response = await client.patch(
            f"/api/v1/patients/{test_patient.id}",
            headers=auth_headers,
            json={
                "address": "Updated Address",
                "blood_group": "A+",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "Updated Address"
        assert data["blood_group"] == "A+"

    @pytest.mark.asyncio

    async def test_get_patient_appointments(
        self,
        client: AsyncClient,
        auth_headers,
        test_patient,
        test_appointment,
    ):
        """Test getting patient's appointment history."""
        response = await client.get(
            f"/api/v1/patients/{test_patient.id}/appointments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPatientValidation:
    """Tests for patient data validation."""

    @pytest.mark.asyncio

    async def test_create_patient_invalid_phone(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test creating patient with invalid phone."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "name": "Invalid Phone Patient",
                "phone": "invalid",
                "gender": "male",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio

    async def test_create_patient_invalid_email(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test creating patient with invalid email."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "name": "Invalid Email Patient",
                "phone": "+919876543288",
                "email": "invalid-email",
                "gender": "male",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio

    async def test_create_patient_missing_name(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test creating patient without name."""
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={
                "phone": "+919876543277",
                "gender": "male",
            },
        )
        assert response.status_code == 422

