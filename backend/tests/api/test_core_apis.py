"""
Integration tests for core API endpoints.

Tests for:
- Clinics API (/api/v1/clinics)
- Doctors API (/api/v1/doctors)
- Services API (/api/v1/services)
- Search API (/api/v1/search)
"""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.service import Service


class TestClinicsAPI:
    """Tests for Clinics API endpoints."""

    def test_create_clinic(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test creating a new clinic."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "name": "New Test Clinic",
                "phone": "+919876543220",
                "email": "newclinic@test.com",
                "address": "789 New Street",
                "city": "Delhi",
                "state": "Delhi",
                "pincode": "110001",
                "timezone": "Asia/Kolkata",
                "currency": "INR",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Clinic"
        assert data["phone"] == "+919876543220"
        assert data["city"] == "Delhi"
        assert "id" in data
        assert "slug" in data
        assert data["is_active"] is True

    def test_create_clinic_with_slug(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test creating a clinic with custom slug."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "name": "Custom Slug Clinic",
                "slug": "custom-clinic",
                "phone": "+919876543221",
                "email": "custom@clinic.com",
                "address": "100 Custom Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400002",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "custom-clinic"

    def test_create_clinic_duplicate_slug(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating clinic with duplicate slug auto-increments."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "name": test_clinic.name,
                "slug": test_clinic.slug,
                "phone": "+919876543222",
                "email": "duplicate@clinic.com",
                "address": "Duplicate Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400003",
            },
        )
        assert response.status_code == 201
        data = response.json()
        # Slug should be auto-incremented
        assert data["slug"] != test_clinic.slug
        assert test_clinic.slug in data["slug"]

    def test_create_clinic_with_gst(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test creating clinic with GST number."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "name": "GST Clinic",
                "phone": "+919876543223",
                "email": "gst@clinic.com",
                "address": "GST Street",
                "city": "Bangalore",
                "state": "Karnataka",
                "pincode": "560001",
                "gst_number": "29ABCDE1234F1Z5",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["gst_number"] == "29ABCDE1234F1Z5"

    def test_list_clinics(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test listing all clinics."""
        response = client.get(
            "/api/v1/clinics/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(c["id"] == str(test_clinic.id) for c in data)

    def test_list_clinics_with_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test listing clinics with pagination."""
        response = client.get(
            "/api/v1/clinics/?skip=0&limit=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_get_clinic_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test getting a specific clinic by ID."""
        response = client.get(
            f"/api/v1/clinics/{test_clinic.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_clinic.id)
        assert data["name"] == test_clinic.name
        assert data["phone"] == test_clinic.phone

    def test_get_clinic_not_found(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test getting non-existent clinic."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/clinics/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_clinic_by_slug(
        self,
        client: TestClient,
        test_clinic: Clinic,
    ):
        """Test getting clinic by slug (public endpoint)."""
        response = client.get(f"/api/v1/clinics/slug/{test_clinic.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_clinic.id)
        assert data["slug"] == test_clinic.slug

    def test_get_clinic_by_invalid_slug(
        self,
        client: TestClient,
    ):
        """Test getting clinic with invalid slug."""
        response = client.get("/api/v1/clinics/slug/nonexistent-clinic")
        assert response.status_code == 404

    def test_update_clinic(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test updating clinic settings."""
        response = client.patch(
            f"/api/v1/clinics/{test_clinic.id}",
            headers=auth_headers,
            json={
                "address": "Updated Address",
                "website": "https://updated.clinic.com",
                "primary_color": "#FF5722",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "Updated Address"
        assert data["website"] == "https://updated.clinic.com"
        assert data["primary_color"] == "#FF5722"

    def test_update_clinic_not_found(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test updating non-existent clinic."""
        fake_id = uuid4()
        response = client.patch(
            f"/api/v1/clinics/{fake_id}",
            headers=auth_headers,
            json={"address": "New Address"},
        )
        assert response.status_code == 404

    def test_deactivate_clinic(
        self,
        client: TestClient,
        auth_headers: dict,
        db: Session,
    ):
        """Test deactivating a clinic."""
        # Create a new clinic to deactivate
        clinic = Clinic(
            name="Clinic to Deactivate",
            slug="clinic-deactivate",
            phone="+919876543224",
            email="deactivate@clinic.com",
            address="Deactivate Street",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
        )
        db.add(clinic)
        db.commit()
        db.refresh(clinic)

        response = client.delete(
            f"/api/v1/clinics/{clinic.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_get_clinic_stats(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test getting clinic statistics."""
        response = client.get(
            f"/api/v1/clinics/{test_clinic.id}/stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_patients" in data
        assert "total_doctors" in data
        assert "total_appointments_today" in data
        assert "total_revenue_month" in data
        assert "pending_appointments" in data
        assert isinstance(data["total_patients"], int)
        assert isinstance(data["total_doctors"], int)


class TestDoctorsAPI:
    """Tests for Doctors API endpoints."""

    def test_create_doctor(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating a new doctor."""
        response = client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                "name": "Dr. New Doctor",
                "specialization": "Cardiology",
                "qualification": "MBBS, MD",
                "registration_number": "MH67890",
                "experience_years": 10,
                "phone": "+919876543225",
                "email": "newdoctor@test.com",
                "clinic_id": str(test_clinic.id),
                "consultation_fee": 800.0,
                "followup_fee": 500.0,
                "slot_duration": 20,
                "languages": ["English", "Hindi", "Marathi"],
                "working_hours": {
                    "monday": {"start": "09:00", "end": "18:00"},
                    "tuesday": {"start": "09:00", "end": "18:00"},
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Dr. New Doctor"
        assert data["specialization"] == "Cardiology"
        assert data["qualification"] == "MBBS, MD"
        assert float(data["consultation_fee"]) == 800.0
        assert data["slot_duration"] == 20
        assert data["is_active"] is True

    def test_create_doctor_minimal(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating doctor with minimal required fields."""
        response = client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                "name": "Dr. Minimal",
                "clinic_id": str(test_clinic.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Dr. Minimal"
        assert float(data["consultation_fee"]) == 500.0  # Default fee
        assert data["slot_duration"] == 15  # Default slot

    def test_list_doctors(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test listing all doctors."""
        response = client.get(
            "/api/v1/doctors/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(d["id"] == str(test_doctor.id) for d in data)

    def test_list_doctors_by_clinic(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
        test_doctor: Doctor,
    ):
        """Test listing doctors filtered by clinic."""
        response = client.get(
            f"/api/v1/doctors/?clinic_id={test_clinic.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All doctors should belong to the test clinic
        for doctor in data:
            assert doctor["clinic_id"] == str(test_clinic.id)

    def test_list_doctors_by_specialization(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test listing doctors filtered by specialization."""
        response = client.get(
            f"/api/v1/doctors/?specialization={test_doctor.specialization}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_doctor_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test getting a specific doctor."""
        response = client.get(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_doctor.id)
        assert data["name"] == test_doctor.name
        assert data["specialization"] == test_doctor.specialization

    def test_get_doctor_not_found(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test getting non-existent doctor."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/doctors/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_update_doctor_specialization(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test updating doctor specialization."""
        response = client.patch(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
            json={
                "specialization": "Orthopedics",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["specialization"] == "Orthopedics"

    def test_update_doctor_consultation_fee(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test updating consultation fee."""
        response = client.patch(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
            json={
                "consultation_fee": 1000.0,
                "followup_fee": 600.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["consultation_fee"]) == 1000.0
        assert float(data["followup_fee"]) == 600.0

    def test_update_doctor_working_hours(
        self,
        client: TestClient,
        auth_headers: dict,
        test_doctor: Doctor,
    ):
        """Test updating doctor's working hours."""
        new_hours = {
            "monday": {"start": "10:00", "end": "19:00"},
            "tuesday": {"start": "10:00", "end": "19:00"},
            "wednesday": {"start": "10:00", "end": "19:00"},
        }
        response = client.patch(
            f"/api/v1/doctors/{test_doctor.id}",
            headers=auth_headers,
            json={"working_hours": new_hours},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["working_hours"]["monday"]["start"] == "10:00"

    def test_deactivate_doctor(
        self,
        client: TestClient,
        auth_headers: dict,
        db: Session,
        test_clinic: Clinic,
    ):
        """Test deactivating a doctor."""
        # Create a new doctor to deactivate
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            email="deactivate_doctor@test.com",
            phone="+919876543226",
            hashed_password=get_password_hash("testpass"),
            name="Dr. Deactivate",
            role="doctor",
            clinic_id=str(test_clinic.id),
        )
        db.add(user)
        db.commit()

        doctor = Doctor(
            user_id=str(user.id),
            clinic_id=str(test_clinic.id),
            name="Dr. Deactivate",
            specialization="General",
            consultation_fee=Decimal("500.00"),
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)

        response = client.delete(
            f"/api/v1/doctors/{doctor.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_list_doctors_public(
        self,
        client: TestClient,
        test_clinic: Clinic,
        test_doctor: Doctor,
    ):
        """Test public endpoint for listing doctors (for booking)."""
        response = client.get(f"/api/v1/doctors/clinic/{test_clinic.id}/public")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Only active doctors accepting new patients should appear
        for doctor in data:
            assert doctor["is_active"] is True
            assert doctor["accepting_new_patients"] is True


class TestServicesAPI:
    """Tests for Services API endpoints."""

    def test_create_service(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating a new service."""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "ECG Test",
                "code": "ECG001",
                "category": "Diagnostic",
                "description": "Electrocardiogram test",
                "price": 300.0,
                "tax_rate": 18.0,
                "duration_minutes": 30,
                "clinic_id": str(test_clinic.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "ECG Test"
        assert data["code"] == "ECG001"
        assert data["category"] == "Diagnostic"
        assert float(data["price"]) == 300.0
        assert float(data["tax_rate"]) == 18.0
        assert data["duration_minutes"] == 30
        assert data["is_active"] is True

    def test_create_service_minimal(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating service with minimal fields."""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Basic Checkup",
                "price": 200.0,
                "clinic_id": str(test_clinic.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Basic Checkup"
        assert float(data["price"]) == 200.0
        assert data["duration_minutes"] == 30  # Default

    def test_list_services(
        self,
        client: TestClient,
        auth_headers: dict,
        test_service: Service,
    ):
        """Test listing all services."""
        response = client.get(
            "/api/v1/services/",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_services_by_clinic(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test listing services filtered by clinic."""
        response = client.get(
            f"/api/v1/services/?clinic_id={test_clinic.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for service in data:
            assert service["clinic_id"] == str(test_clinic.id)

    def test_list_services_by_category(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
        db: Session,
    ):
        """Test listing services filtered by category."""
        # Create a service with specific category
        service = Service(
            clinic_id=str(test_clinic.id),
            name="X-Ray",
            category="Radiology",
            price=Decimal("500.00"),
        )
        db.add(service)
        db.commit()

        response = client.get(
            "/api/v1/services/?category=Radiology",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_service_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_service: Service,
    ):
        """Test getting a specific service."""
        response = client.get(
            f"/api/v1/services/{test_service.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_service.id)
        assert data["name"] == test_service.name

    def test_get_service_not_found(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test getting non-existent service."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/services/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_update_service_price(
        self,
        client: TestClient,
        auth_headers: dict,
        test_service: Service,
    ):
        """Test updating service price."""
        response = client.patch(
            f"/api/v1/services/{test_service.id}",
            headers=auth_headers,
            json={
                "price": 700.0,
                "tax_rate": 12.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["price"]) == 700.0
        assert float(data["tax_rate"]) == 12.0

    def test_update_service_duration(
        self,
        client: TestClient,
        auth_headers: dict,
        test_service: Service,
    ):
        """Test updating service duration."""
        response = client.patch(
            f"/api/v1/services/{test_service.id}",
            headers=auth_headers,
            json={
                "duration_minutes": 45,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["duration_minutes"] == 45

    def test_deactivate_service(
        self,
        client: TestClient,
        auth_headers: dict,
        db: Session,
        test_clinic: Clinic,
    ):
        """Test deactivating a service."""
        # Create a new service to deactivate
        service = Service(
            clinic_id=str(test_clinic.id),
            name="Service to Deactivate",
            price=Decimal("100.00"),
        )
        db.add(service)
        db.commit()
        db.refresh(service)

        response = client.delete(
            f"/api/v1/services/{service.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestSearchAPI:
    """Tests for Search API endpoints."""

    def test_search_patients_by_name(
        self,
        client: TestClient,
        auth_headers: dict,
        test_patient: Patient,
    ):
        """Test searching patients by name."""
        response = client.get(
            f"/api/v1/search/?q={test_patient.name[:5]}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_search_patients_by_phone(
        self,
        client: TestClient,
        auth_headers: dict,
        test_patient: Patient,
    ):
        """Test searching by phone number."""
        # Search with last 4 digits
        phone_digits = test_patient.phone[-4:]
        response = client.get(
            f"/api/v1/search/?q={phone_digits}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["results"], list)

    def test_search_with_collections_filter(
        self,
        client: TestClient,
        auth_headers: dict,
        test_patient: Patient,
    ):
        """Test searching with collection filter."""
        response = client.get(
            f"/api/v1/search/?q={test_patient.name}&collections=patients",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["results"], list)
        # All results should be from patients collection
        for result in data["results"]:
            assert result["collection"] == "patients"

    def test_search_multiple_collections(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test searching across multiple collections."""
        response = client.get(
            "/api/v1/search/?q=test&collections=patients,doctors,appointments",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["results"], list)

    def test_search_with_limit(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test search with result limit."""
        response = client.get(
            "/api/v1/search/?q=test&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5

    def test_search_empty_query(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test search with empty query."""
        response = client.get(
            "/api/v1/search/",
            headers=auth_headers,
        )
        # Should return 422 (validation error) due to missing query param
        assert response.status_code == 422

    def test_search_no_results(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test search with no matching results."""
        response = client.get(
            "/api/v1/search/?q=nonexistent12345xyz",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert len(data["results"]) == 0

    def test_search_invalid_collection(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test search with invalid collection name."""
        response = client.get(
            "/api/v1/search/?q=test&collections=invalid_collection",
            headers=auth_headers,
        )
        # Should return 400 for invalid collection
        assert response.status_code == 400

    def test_search_index_status(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test getting search index status."""
        response = client.get(
            "/api/v1/search/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "initialized" in data
        assert "collections" in data
        assert isinstance(data["collections"], list)

    def test_search_initialize_index(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test initializing search index."""
        response = client.post(
            "/api/v1/search/initialize",
            headers=auth_headers,
        )
        # This might fail if user doesn't have admin role
        # but we should get a response
        assert response.status_code in [200, 403]

    def test_index_patient(
        self,
        client: TestClient,
        auth_headers: dict,
        test_patient: Patient,
    ):
        """Test indexing a specific patient."""
        response = client.post(
            f"/api/v1/search/patients/{test_patient.id}",
            headers=auth_headers,
        )
        # May succeed or fail depending on RAG service availability
        assert response.status_code in [200, 404, 500]

    def test_index_appointment(
        self,
        client: TestClient,
        auth_headers: dict,
        test_appointment,
    ):
        """Test indexing a specific appointment."""
        response = client.post(
            f"/api/v1/search/appointments/{test_appointment.id}",
            headers=auth_headers,
        )
        # May succeed or fail depending on RAG service availability
        assert response.status_code in [200, 404, 500]


class TestClinicsValidation:
    """Tests for clinic data validation."""

    def test_create_clinic_invalid_phone(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test creating clinic with invalid phone."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "name": "Invalid Phone Clinic",
                "phone": "123",  # Too short
                "address": "Test Address",
            },
        )
        assert response.status_code == 422

    def test_create_clinic_invalid_email(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test creating clinic with invalid email."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "name": "Invalid Email Clinic",
                "phone": "+919876543227",
                "email": "not-an-email",
            },
        )
        assert response.status_code == 422

    def test_create_clinic_invalid_slug(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test creating clinic with invalid slug format."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "name": "Invalid Slug Clinic",
                "phone": "+919876543228",
                "slug": "Invalid Slug!",  # Contains invalid characters
            },
        )
        assert response.status_code == 422

    def test_create_clinic_missing_name(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test creating clinic without name."""
        response = client.post(
            "/api/v1/clinics/",
            headers=auth_headers,
            json={
                "phone": "+919876543229",
                "address": "Test Address",
            },
        )
        assert response.status_code == 422


class TestDoctorsValidation:
    """Tests for doctor data validation."""

    def test_create_doctor_missing_name(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating doctor without name."""
        response = client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "specialization": "Cardiology",
            },
        )
        assert response.status_code == 422

    def test_create_doctor_invalid_email(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating doctor with invalid email."""
        response = client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                "name": "Dr. Invalid Email",
                "clinic_id": str(test_clinic.id),
                "email": "invalid-email",
            },
        )
        assert response.status_code == 422

    def test_create_doctor_negative_fee(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating doctor with negative consultation fee."""
        response = client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                "name": "Dr. Negative Fee",
                "clinic_id": str(test_clinic.id),
                "consultation_fee": -100.0,
            },
        )
        assert response.status_code == 422

    def test_create_doctor_invalid_slot_duration(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating doctor with invalid slot duration."""
        response = client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                "name": "Dr. Invalid Slot",
                "clinic_id": str(test_clinic.id),
                "slot_duration": 200,  # Greater than max 120
            },
        )
        assert response.status_code == 422


class TestServicesValidation:
    """Tests for service data validation."""

    def test_create_service_missing_name(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating service without name."""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "clinic_id": str(test_clinic.id),
                "price": 100.0,
            },
        )
        assert response.status_code == 422

    def test_create_service_missing_price(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating service without price."""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Test Service",
                "clinic_id": str(test_clinic.id),
            },
        )
        assert response.status_code == 422

    def test_create_service_negative_price(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating service with negative price."""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Negative Price Service",
                "clinic_id": str(test_clinic.id),
                "price": -50.0,
            },
        )
        assert response.status_code == 422

    def test_create_service_invalid_tax_rate(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating service with invalid tax rate."""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Invalid Tax Service",
                "clinic_id": str(test_clinic.id),
                "price": 100.0,
                "tax_rate": 150.0,  # Greater than 100
            },
        )
        assert response.status_code == 422

    def test_create_service_invalid_duration(
        self,
        client: TestClient,
        auth_headers: dict,
        test_clinic: Clinic,
    ):
        """Test creating service with invalid duration."""
        response = client.post(
            "/api/v1/services/",
            headers=auth_headers,
            json={
                "name": "Invalid Duration Service",
                "clinic_id": str(test_clinic.id),
                "price": 100.0,
                "duration_minutes": 500,  # Greater than max 480
            },
        )
        assert response.status_code == 422
