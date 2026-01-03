"""
Tests for patient endpoints.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


class TestPatients:
    """Patient endpoint tests."""

    def test_create_patient(
        self,
        client: TestClient,
        auth_headers,
        test_clinic,
    ):
        """Test creating a new patient."""
        response = client.post(
            "/api/v1/patients",
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

    def test_create_patient_duplicate_phone(
        self,
        client: TestClient,
        auth_headers,
        test_patient,
    ):
        """Test creating patient with duplicate phone."""
        response = client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "name": "Duplicate Patient",
                "phone": test_patient.phone,
                "gender": "male",
            },
        )
        assert response.status_code in [400, 409]

    def test_get_patient_by_id(
        self,
        client: TestClient,
        auth_headers,
        test_patient,
    ):
        """Test getting patient by ID."""
        response = client.get(
            f"/api/v1/patients/{test_patient.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_patient.id
        assert data["name"] == test_patient.name

    def test_get_patient_not_found(
        self,
        client: TestClient,
        auth_headers,
    ):
        """Test getting non-existent patient."""
        response = client.get(
            f"/api/v1/patients/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_search_patients(
        self,
        client: TestClient,
        auth_headers,
        test_patient,
    ):
        """Test searching patients."""
        response = client.get(
            f"/api/v1/patients/search?q={test_patient.name[:4]}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(p["id"] == test_patient.id for p in data)

    def test_search_patients_by_phone(
        self,
        client: TestClient,
        auth_headers,
        test_patient,
    ):
        """Test searching patients by phone."""
        response = client.get(
            f"/api/v1/patients/search?q={test_patient.phone[-4:]}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_patients_min_length(
        self,
        client: TestClient,
        auth_headers,
    ):
        """Test search with query too short."""
        response = client.get(
            "/api/v1/patients/search?q=a",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_update_patient(
        self,
        client: TestClient,
        auth_headers,
        test_patient,
    ):
        """Test updating patient."""
        response = client.patch(
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

    def test_get_patient_appointments(
        self,
        client: TestClient,
        auth_headers,
        test_patient,
        test_appointment,
    ):
        """Test getting patient's appointment history."""
        response = client.get(
            f"/api/v1/patients/{test_patient.id}/appointments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPatientValidation:
    """Tests for patient data validation."""

    def test_create_patient_invalid_phone(
        self,
        client: TestClient,
        auth_headers,
    ):
        """Test creating patient with invalid phone."""
        response = client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "name": "Invalid Phone Patient",
                "phone": "invalid",
                "gender": "male",
            },
        )
        assert response.status_code == 422

    def test_create_patient_invalid_email(
        self,
        client: TestClient,
        auth_headers,
    ):
        """Test creating patient with invalid email."""
        response = client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "name": "Invalid Email Patient",
                "phone": "+919876543288",
                "email": "invalid-email",
                "gender": "male",
            },
        )
        assert response.status_code == 422

    def test_create_patient_missing_name(
        self,
        client: TestClient,
        auth_headers,
    ):
        """Test creating patient without name."""
        response = client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "phone": "+919876543277",
                "gender": "male",
            },
        )
        assert response.status_code == 422
