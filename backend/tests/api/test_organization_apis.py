"""
Integration tests for Organization, Staff, EMR, and Public API endpoints.

Tests cover:
- Organizations API (/api/v1/organizations)
- Staff API (/api/v1/staff)
- EMR API (/api/v1/emr)
- Public API (/api/v1/public)
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.staff import StaffAssignment, StaffRole
from app.models.user import User
from app.core.security import get_password_hash, create_access_token


# ==================== Fixtures ====================


@pytest.fixture
@pytest.mark.asyncio
async def test_organization(db: AsyncSession, test_user: User) -> Organization:
    """Create a test organization."""
    org = Organization(
        id=uuid4(),
        name="Test Hospital Chain",
        slug="test-hospital-chain",
        owner_user_id=test_user.id,
        description="A test healthcare organization",
        email="contact@testhospital.com",
        phone="+919876543200",
        website="https://testhospital.com",
        subscription_tier="premium",
        max_clinics=10,
        max_users=100,
        primary_color="#1976D2",
        is_active=True,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest.fixture
@pytest.mark.asyncio
async def test_staff_role(db: AsyncSession, test_organization: Organization) -> StaffRole:
    """Create a test staff role."""
    role = StaffRole(
        id=uuid4(),
        name="Receptionist",
        description="Front desk staff",
        permissions=["appointments.view", "appointments.create", "patients.view"],
        organization_id=test_organization.id,
        is_system=False,
        is_active=True,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


@pytest.fixture
@pytest.mark.asyncio
async def test_staff_user(db: AsyncSession, test_clinic: Clinic) -> User:
    """Create a test staff user."""
    user = User(
        id=uuid4(),
        email="staff@test.com",
        phone="+919876543213",
        password_hash=get_password_hash("staffpass123"),
        name="Test Staff",
        role="staff",
        clinic_id=test_clinic.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
@pytest.mark.asyncio
async def test_staff_assignment(
    db: AsyncSession,
    test_staff_user: User,
    test_clinic: Clinic,
    test_staff_role: StaffRole,
) -> StaffAssignment:
    """Create a test staff assignment."""
    assignment = StaffAssignment(
        id=uuid4(),
        user_id=test_staff_user.id,
        clinic_id=test_clinic.id,
        role_id=test_staff_role.id,
        is_primary_location=True,
        start_date=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@pytest.fixture
def staff_auth_headers(test_staff_user: User) -> dict:
    """Generate authentication headers for staff user."""
    token = create_access_token(subject=str(test_staff_user.id))
    return {"Authorization": f"Bearer {token}"}


# ==================== Organization API Tests ====================


class TestOrganizationsAPI:
    """Tests for /api/v1/organizations endpoints."""

    @pytest.mark.asyncio

    async def test_create_organization(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test creating a new organization."""
        response = await client.post(
            "/api/v1/organizations/",
            headers=auth_headers,
            json={
                "name": "New Medical Group",
                "slug": "new-medical-group",
                "owner_user_id": str(test_user.id),
                "description": "A new healthcare organization",
                "email": "info@newmedical.com",
                "phone": "+919876543299",
                "subscription_tier": "basic",
                "max_clinics": 5,
                "max_users": 50,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Medical Group"
        assert data["slug"] == "new-medical-group"
        assert data["subscription_tier"] == "basic"
        assert data["max_clinics"] == 5
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio

    async def test_create_organization_auto_slug(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test creating organization with auto-generated slug."""
        response = await client.post(
            "/api/v1/organizations/",
            headers=auth_headers,
            json={
                "name": "Apollo Hospitals",
                "owner_user_id": str(test_user.id),
                "subscription_tier": "premium",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Apollo Hospitals"
        assert data["slug"] == "apollo-hospitals"

    @pytest.mark.asyncio

    async def test_create_organization_requires_admin(
        self,
        client: AsyncClient,
        staff_auth_headers: dict,
        test_user: User,
    ):
        """Test that creating organization requires admin role."""
        response = await client.post(
            "/api/v1/organizations/",
            headers=staff_auth_headers,
            json={
                "name": "Test Org",
                "owner_user_id": str(test_user.id),
                "subscription_tier": "free",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio

    async def test_list_organizations(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test listing all organizations."""
        response = await client.get(
            "/api/v1/organizations/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == test_organization.name

    @pytest.mark.asyncio

    async def test_list_organizations_with_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test listing organizations with pagination."""
        response = await client.get(
            "/api/v1/organizations/?skip=0&limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio

    async def test_list_organizations_filter_active(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test filtering organizations by active status."""
        response = await client.get(
            "/api/v1/organizations/?is_active=true",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(org["is_active"] for org in data)

    @pytest.mark.asyncio

    async def test_get_organization_by_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test getting organization by ID."""
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_organization.id)
        assert data["name"] == test_organization.name
        assert data["clinic_count"] >= 0

    @pytest.mark.asyncio

    async def test_get_organization_by_slug(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test getting organization by slug."""
        response = await client.get(
            f"/api/v1/organizations/slug/{test_organization.slug}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == test_organization.slug
        assert data["name"] == test_organization.name

    @pytest.mark.asyncio

    async def test_get_organization_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting non-existent organization."""
        response = await client.get(
            f"/api/v1/organizations/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_update_organization(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test updating organization details."""
        response = await client.patch(
            f"/api/v1/organizations/{test_organization.id}",
            headers=auth_headers,
            json={
                "name": "Updated Hospital Chain",
                "description": "Updated description",
                "max_clinics": 20,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Hospital Chain"
        assert data["description"] == "Updated description"
        assert data["max_clinics"] == 20

    @pytest.mark.asyncio

    async def test_add_clinic_to_organization(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
        test_clinic: Clinic,
    ):
        """Test adding a clinic to an organization."""
        response = await client.post(
            f"/api/v1/organizations/{test_organization.id}/clinics",
            headers=auth_headers,
            json={"clinic_id": str(test_clinic.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Clinic added successfully"
        assert data["clinic_id"] == str(test_clinic.id)

    @pytest.mark.asyncio

    async def test_remove_clinic_from_organization(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
        test_clinic: Clinic,
        db: AsyncSession,
    ):
        """Test removing a clinic from an organization."""
        # First add the clinic
        test_clinic.organization_id = test_organization.id
        await db.commit()

        response = await client.delete(
            f"/api/v1/organizations/{test_organization.id}/clinics/{test_clinic.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Clinic removed successfully"

    @pytest.mark.asyncio

    async def test_get_organization_clinics(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
        test_clinic: Clinic,
        db: AsyncSession,
    ):
        """Test getting all clinics in an organization."""
        # Add clinic to organization
        test_clinic.organization_id = test_organization.id
        await db.commit()

        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/clinics",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_get_organization_analytics(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test getting organization-level analytics."""
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/analytics",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_clinics" in data
        assert "total_users" in data
        assert "total_patients" in data
        assert "total_revenue_month" in data


# ==================== Staff API Tests ====================


class TestStaffAPI:
    """Tests for /api/v1/staff endpoints."""

    # Staff Roles Tests

    @pytest.mark.asyncio

    async def test_create_staff_role(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test creating a staff role."""
        response = await client.post(
            "/api/v1/staff/roles",
            headers=auth_headers,
            json={
                "name": "Nurse",
                "description": "Nursing staff",
                "permissions": ["patients.view", "appointments.view", "vitals.create"],
                "organization_id": str(test_organization.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Nurse"
        assert "patients.view" in data["permissions"]
        assert data["is_active"] is True

    @pytest.mark.asyncio

    async def test_create_staff_role_invalid_permissions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test creating staff role with invalid permission format."""
        response = await client.post(
            "/api/v1/staff/roles",
            headers=auth_headers,
            json={
                "name": "Invalid Role",
                "permissions": ["invalid-permission-format"],
                "organization_id": str(test_organization.id),
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio

    async def test_list_staff_roles(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_role: StaffRole,
    ):
        """Test listing staff roles."""
        response = await client.get(
            "/api/v1/staff/roles",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_list_staff_roles_by_organization(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_role: StaffRole,
        test_organization: Organization,
    ):
        """Test listing staff roles filtered by organization."""
        response = await client.get(
            f"/api/v1/staff/roles?organization_id={str(test_organization.id)}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_get_staff_role(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_role: StaffRole,
    ):
        """Test getting a specific staff role."""
        response = await client.get(
            f"/api/v1/staff/roles/{test_staff_role.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_staff_role.id)
        assert data["name"] == test_staff_role.name

    @pytest.mark.asyncio

    async def test_update_staff_role(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_role: StaffRole,
    ):
        """Test updating a staff role."""
        response = await client.patch(
            f"/api/v1/staff/roles/{test_staff_role.id}",
            headers=auth_headers,
            json={
                "description": "Updated description",
                "permissions": ["appointments.*", "patients.view"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert "appointments.*" in data["permissions"]

    @pytest.mark.asyncio

    async def test_delete_staff_role(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession,
        test_organization: Organization,
    ):
        """Test deleting a staff role."""
        # Create a role that's not in use
        role = StaffRole(
            id=uuid4(),
            name="Temp Role",
            permissions=["temp.view"],
            organization_id=test_organization.id,
            is_active=True,
        )
        db.add(role)
        await db.commit()

        response = await client.delete(
            f"/api/v1/staff/roles/{role.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    @pytest.mark.asyncio

    async def test_seed_default_roles(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_organization: Organization,
    ):
        """Test seeding default staff roles."""
        response = await client.post(
            f"/api/v1/staff/roles/seed?organization_id={str(test_organization.id)}",
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "roles" in data
        assert len(data["roles"]) > 0

    # Staff Assignments Tests

    @pytest.mark.asyncio

    async def test_create_staff_assignment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_user: User,
        test_clinic: Clinic,
        test_staff_role: StaffRole,
    ):
        """Test assigning staff to a clinic."""
        response = await client.post(
            "/api/v1/staff/assignments",
            headers=auth_headers,
            json={
                "user_id": str(test_staff_user.id),
                "clinic_id": str(test_clinic.id),
                "role_id": str(test_staff_role.id),
                "is_primary_location": True,
                "notes": "Primary assignment",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(test_staff_user.id)
        assert data["clinic_id"] == str(test_clinic.id)
        assert data["is_primary_location"] is True

    @pytest.mark.asyncio

    async def test_get_staff_assignment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_assignment: StaffAssignment,
    ):
        """Test getting a specific staff assignment."""
        response = await client.get(
            f"/api/v1/staff/assignments/{test_staff_assignment.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_staff_assignment.id)

    @pytest.mark.asyncio

    async def test_update_staff_assignment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_assignment: StaffAssignment,
    ):
        """Test updating a staff assignment."""
        response = await client.patch(
            f"/api/v1/staff/assignments/{test_staff_assignment.id}",
            headers=auth_headers,
            json={
                "is_primary_location": False,
                "notes": "Updated notes",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_primary_location"] is False
        assert data["notes"] == "Updated notes"

    @pytest.mark.asyncio

    async def test_end_staff_assignment(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_assignment: StaffAssignment,
    ):
        """Test ending a staff assignment."""
        response = await client.delete(
            f"/api/v1/staff/assignments/{test_staff_assignment.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "ended successfully" in response.json()["message"]

    @pytest.mark.asyncio

    async def test_get_user_assignments(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_user: User,
        test_staff_assignment: StaffAssignment,
    ):
        """Test getting all assignments for a user."""
        response = await client.get(
            f"/api/v1/staff/users/{test_staff_user.id}/assignments",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio

    async def test_get_user_assignments_access_control(
        self,
        client: AsyncClient,
        staff_auth_headers: dict,
        test_user: User,
    ):
        """Test that staff can only view their own assignments."""
        response = await client.get(
            f"/api/v1/staff/users/{test_user.id}/assignments",
            headers=staff_auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio

    async def test_get_clinic_staff(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic: Clinic,
        test_staff_assignment: StaffAssignment,
    ):
        """Test getting all staff at a clinic."""
        response = await client.get(
            f"/api/v1/staff/clinics/{test_clinic.id}/staff",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_transfer_staff(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_user: User,
        test_clinic: Clinic,
        test_staff_role: StaffRole,
        db: AsyncSession,
    ):
        """Test transferring staff between clinics."""
        # Create second clinic
        clinic2 = Clinic(
            id=uuid4(),
            name="Second Clinic",
            slug="second-clinic",
            address="456 Second Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            phone="+919876543220",
        )
        db.add(clinic2)
        await db.commit()

        response = await client.post(
            "/api/v1/staff/transfer",
            headers=auth_headers,
            json={
                "user_id": str(test_staff_user.id),
                "from_clinic_id": str(test_clinic.id),
                "to_clinic_id": str(clinic2.id),
                "role_id": str(test_staff_role.id),
                "make_primary": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["clinic_id"] == str(clinic2.id)

    # Permission Tests

    @pytest.mark.asyncio

    async def test_check_permission(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_staff_user: User,
        test_clinic: Clinic,
        test_staff_assignment: StaffAssignment,
    ):
        """Test checking user permissions."""
        response = await client.post(
            "/api/v1/staff/permissions/check",
            headers=auth_headers,
            json={
                "user_id": str(test_staff_user.id),
                "clinic_id": str(test_clinic.id),
                "permission": "appointments.view",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "has_permission" in data
        assert isinstance(data["has_permission"], bool)

    @pytest.mark.asyncio

    async def test_check_permission_access_control(
        self,
        client: AsyncClient,
        staff_auth_headers: dict,
        test_user: User,
        test_clinic: Clinic,
    ):
        """Test that users can only check their own permissions."""
        response = await client.post(
            "/api/v1/staff/permissions/check",
            headers=staff_auth_headers,
            json={
                "user_id": str(test_user.id),
                "clinic_id": str(test_clinic.id),
                "permission": "appointments.view",
            },
        )

        assert response.status_code == 403


# ==================== EMR API Tests ====================


class TestEMRAPI:
    """Tests for /api/v1/emr endpoints."""

    @pytest.mark.asyncio

    async def test_get_emr_sync_status(self, client: AsyncClient, auth_headers: dict):
        """Test getting EMR sync status."""
        response = await client.get(
            "/api/v1/emr/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_available" in data
        assert "last_sync" in data or data.get("is_available") is False

    @patch("app.services.emr_sync_service.get_emr_sync_service")
    @pytest.mark.asyncio
    async def test_trigger_manual_sync(
        self,
        mock_service,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test triggering manual EMR sync."""
        # Mock the service
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.full_sync = AsyncMock(return_value={
            "patients_synced": 10,
            "appointments_synced": 5,
        })
        mock_service.return_value = mock_instance

        response = await client.post(
            "/api/v1/emr/sync",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.services.emr_sync_service.get_emr_sync_service")
    @pytest.mark.asyncio
    async def test_trigger_manual_sync_unavailable(
        self,
        mock_service,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test manual sync when EMR is unavailable."""
        # Mock unavailable service
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = False
        mock_service.return_value = mock_instance

        response = await client.post(
            "/api/v1/emr/sync",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @patch("app.services.emr_sync_service.get_emr_sync_service")
    @pytest.mark.asyncio
    async def test_get_emr_patient(
        self,
        mock_service,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting patient from EMR."""
        # Mock EMR patient data
        mock_patient = MagicMock()
        mock_patient.id = "EMR123"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.phone = "+919876543210"
        mock_patient.email = "john@example.com"
        mock_patient.date_of_birth = "1990-01-01"
        mock_patient.gender = "male"
        mock_patient.blood_group = "O+"
        mock_patient.allergies = None
        mock_patient.address = "123 Street"
        mock_patient.created_at = datetime.now(timezone.utc)
        mock_patient.updated_at = datetime.now(timezone.utc)

        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.emr_async.get_patient = AsyncMock(return_value=mock_patient)
        mock_service.return_value = mock_instance

        response = await client.get(
            "/api/v1/emr/patients/EMR123",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "EMR123"
        assert data["first_name"] == "John"

    @patch("app.services.emr_sync_service.get_emr_sync_service")
    @pytest.mark.asyncio
    async def test_get_patient_visits(
        self,
        mock_service,
        client: AsyncClient,
        auth_headers: dict,
        test_patient: Patient,
        db: AsyncSession,
    ):
        """Test getting patient visit history from EMR."""
        # Set EMR ID on patient
        test_patient.emr_patient_id = "EMR123"
        await db.commit()

        # Mock EMR visit data
        mock_visit = MagicMock()
        mock_visit.id = "VISIT1"
        mock_visit.patient_id = "EMR123"
        mock_visit.doctor_name = "Dr. Smith"
        mock_visit.visit_date = "2024-01-01T10:00:00Z"
        mock_visit.chief_complaint = "Headache"
        mock_visit.diagnosis = "Migraine"
        mock_visit.notes = "Prescribed medication"
        mock_visit.vitals = {"bp": "120/80"}
        mock_visit.prescriptions = ["Paracetamol 500mg"]
        mock_visit.created_at = datetime.now(timezone.utc)

        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.emr_async.get_patient_visits = AsyncMock(return_value=[mock_visit])
        mock_service.return_value = mock_instance

        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/visits",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @patch("app.services.emr_sync_service.get_emr_sync_service")
    @pytest.mark.asyncio
    async def test_get_patient_prescriptions(
        self,
        mock_service,
        client: AsyncClient,
        auth_headers: dict,
        test_patient: Patient,
        db: AsyncSession,
    ):
        """Test getting patient prescription history."""
        # Set EMR ID on patient
        test_patient.emr_patient_id = "EMR123"
        await db.commit()

        # Mock EMR visit data with prescriptions
        mock_visit = MagicMock()
        mock_visit.id = "VISIT1"
        mock_visit.patient_id = "EMR123"
        mock_visit.doctor_name = "Dr. Smith"
        mock_visit.visit_date = "2024-01-01T10:00:00Z"
        mock_visit.chief_complaint = "Headache"
        mock_visit.diagnosis = "Migraine"
        mock_visit.notes = "Take with food"
        mock_visit.vitals = {}
        mock_visit.prescriptions = ["Paracetamol 500mg", "Ibuprofen 400mg"]
        mock_visit.created_at = datetime.now(timezone.utc)

        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.emr_async.get_patient_visits = AsyncMock(return_value=[mock_visit])
        mock_service.return_value = mock_instance

        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/prescriptions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("app.services.emr_sync_service.get_emr_sync_service")
    @pytest.mark.asyncio
    async def test_get_patient_timeline(
        self,
        mock_service,
        client: AsyncClient,
        auth_headers: dict,
        test_patient: Patient,
        test_appointment,
        db: AsyncSession,
    ):
        """Test getting unified patient timeline."""
        # Set EMR ID on patient
        test_patient.emr_patient_id = "EMR123"
        await db.commit()

        # Mock EMR service
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.emr_async.get_patient_visits = AsyncMock(return_value=[])
        mock_service.return_value = mock_instance

        response = await client.get(
            f"/api/v1/emr/patients/{test_patient.id}/timeline",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total_events" in data
        assert data["patient_id"] == str(test_patient.id)

    @patch("app.services.emr_sync_service.get_emr_sync_service")
    @pytest.mark.asyncio
    async def test_link_appointment_to_visit(
        self,
        mock_service,
        client: AsyncClient,
        auth_headers: dict,
        test_appointment,
    ):
        """Test linking appointment to EMR visit."""
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.link_appointment_to_visit = AsyncMock(return_value=True)
        mock_service.return_value = mock_instance

        response = await client.post(
            f"/api/v1/emr/appointments/{test_appointment.id}/link-visit/VISIT123",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["appointment_id"] == str(test_appointment.id)


# ==================== Public API Tests ====================


class TestPublicAPI:
    """Tests for /api/v1/public endpoints (no auth required)."""

    # OTP Tests

    @patch("app.services.otp_service.OTPService.send_otp")
    @pytest.mark.asyncio
    async def test_send_otp(self, mock_send, client: AsyncClient):
        """Test sending OTP to phone number."""
        mock_send.return_value = "123456"

        response = await client.post(
            "/api/v1/public/otp/send",
            json={"phone": "+919876543210"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "expires_in_seconds" in data

    @patch("app.services.otp_service.OTPService.verify_otp")
    @pytest.mark.asyncio
    async def test_verify_otp(self, mock_verify, client: AsyncClient):
        """Test verifying OTP."""
        mock_verify.return_value = "mock-token-12345"

        response = await client.post(
            "/api/v1/public/otp/verify",
            json={
                "phone": "+919876543210",
                "otp_code": "123456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @patch("app.services.otp_service.OTPService.verify_otp")
    @pytest.mark.asyncio
    async def test_verify_otp_invalid(self, mock_verify, client: AsyncClient):
        """Test verifying invalid OTP."""
        mock_verify.return_value = None

        response = await client.post(
            "/api/v1/public/otp/verify",
            json={
                "phone": "+919876543210",
                "otp_code": "000000",
            },
        )

        assert response.status_code == 400

    # Doctor Discovery Tests

    @pytest.mark.asyncio

    async def test_list_doctors_public(
        self,
        client: AsyncClient,
        test_doctor: Doctor,
        db: AsyncSession,
    ):
        """Test listing doctors without authentication."""
        # Ensure doctor is accepting patients
        test_doctor.accepting_new_patients = True
        await db.commit()

        response = await client.get("/api/v1/public/doctors")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_list_doctors_filter_specialization(
        self,
        client: AsyncClient,
        test_doctor: Doctor,
        db: AsyncSession,
    ):
        """Test filtering doctors by specialization."""
        test_doctor.accepting_new_patients = True
        await db.commit()

        response = await client.get(
            "/api/v1/public/doctors?specialization=General"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_list_doctors_filter_city(
        self,
        client: AsyncClient,
        test_doctor: Doctor,
        db: AsyncSession,
    ):
        """Test filtering doctors by city."""
        test_doctor.accepting_new_patients = True
        await db.commit()

        response = await client.get("/api/v1/public/doctors?city=Mumbai")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio

    async def test_get_doctor_public(
        self,
        client: AsyncClient,
        test_doctor: Doctor,
    ):
        """Test getting doctor details without authentication."""
        response = await client.get(f"/api/v1/public/doctors/{test_doctor.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_doctor.id)
        assert data["name"] == test_doctor.name
        assert "bio" in data

    @pytest.mark.asyncio

    async def test_get_doctor_public_not_found(self, client: AsyncClient):
        """Test getting non-existent doctor."""
        response = await client.get(f"/api/v1/public/doctors/{uuid4()}")

        assert response.status_code == 404

    # Slot Availability Tests

    @pytest.mark.asyncio

    async def test_get_doctor_slots(
        self,
        client: AsyncClient,
        test_doctor: Doctor,
        db: AsyncSession,
    ):
        """Test getting available slots for a doctor."""
        # Set working hours
        test_doctor.working_hours = {
            "monday": [{"start": "09:00", "end": "17:00"}],
            "tuesday": [{"start": "09:00", "end": "17:00"}],
            "wednesday": [{"start": "09:00", "end": "17:00"}],
            "thursday": [{"start": "09:00", "end": "17:00"}],
            "friday": [{"start": "09:00", "end": "17:00"}],
        }
        await db.commit()

        tomorrow = (datetime.now() + timedelta(days=1)).date()

        response = await client.get(
            f"/api/v1/public/doctors/{test_doctor.id}/slots?date_param={tomorrow}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
        assert data["doctor_id"] == str(test_doctor.id)

    # Appointment Booking Tests (require OTP token)

    @patch("app.services.otp_service.OTPService.decode_token")
    @pytest.mark.asyncio
    async def test_book_appointment_public(
        self,
        mock_decode,
        client: AsyncClient,
        test_doctor: Doctor,
    ):
        """Test booking appointment with OTP token."""
        mock_decode.return_value = "+919876543210"

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = await client.post(
            "/api/v1/public/appointments",
            headers={"Authorization": "Bearer mock-token"},
            json={
                "doctor_id": str(test_doctor.id),
                "scheduled_start": start_time.isoformat(),
                "duration_minutes": 15,
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "chief_complaint": "General checkup",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["doctor_id"] == str(test_doctor.id)
        assert "id" in data

    @pytest.mark.asyncio

    async def test_book_appointment_without_token(
        self,
        client: AsyncClient,
        test_doctor: Doctor,
    ):
        """Test that booking requires authentication."""
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        response = await client.post(
            "/api/v1/public/appointments",
            json={
                "doctor_id": str(test_doctor.id),
                "scheduled_start": start_time.isoformat(),
                "duration_minutes": 15,
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        assert response.status_code == 401

    @patch("app.services.otp_service.OTPService.decode_token")
    @pytest.mark.asyncio
    async def test_book_appointment_conflict(
        self,
        mock_decode,
        client: AsyncClient,
        test_doctor: Doctor,
        test_appointment,
    ):
        """Test booking appointment with time conflict."""
        mock_decode.return_value = "+919876543210"

        # Try to book at same time as existing appointment
        response = await client.post(
            "/api/v1/public/appointments",
            headers={"Authorization": "Bearer mock-token"},
            json={
                "doctor_id": str(test_doctor.id),
                "scheduled_start": test_appointment.start_time.isoformat(),
                "duration_minutes": 15,
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        assert response.status_code == 409

    @patch("app.services.otp_service.OTPService.decode_token")
    @pytest.mark.asyncio
    async def test_get_patient_appointments(
        self,
        mock_decode,
        client: AsyncClient,
        test_patient: Patient,
        test_appointment,
    ):
        """Test getting patient's appointments."""
        mock_decode.return_value = test_patient.phone

        response = await client.get(
            "/api/v1/public/appointments",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("app.services.otp_service.OTPService.decode_token")
    @pytest.mark.asyncio
    async def test_get_appointment_detail(
        self,
        mock_decode,
        client: AsyncClient,
        test_patient: Patient,
        test_appointment,
    ):
        """Test getting appointment details."""
        mock_decode.return_value = test_patient.phone

        response = await client.get(
            f"/api/v1/public/appointments/{test_appointment.id}",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_appointment.id)

    @patch("app.services.otp_service.OTPService.decode_token")
    @pytest.mark.asyncio
    async def test_cancel_appointment_public(
        self,
        mock_decode,
        client: AsyncClient,
        test_patient: Patient,
        test_appointment,
    ):
        """Test cancelling appointment via public API."""
        mock_decode.return_value = test_patient.phone

        response = await client.delete(
            f"/api/v1/public/appointments/{test_appointment.id}",
            headers={
                "Authorization": "Bearer mock-token",
                "Content-Type": "application/json",
            },
            content=json.dumps({"reason": "Changed my mind"}),
        )

        assert response.status_code == 200
        data = response.json()
        assert "cancelled successfully" in data["message"]

    @patch("app.services.otp_service.OTPService.decode_token")
    @pytest.mark.asyncio
    async def test_cancel_appointment_not_owned(
        self,
        mock_decode,
        client: AsyncClient,
        test_appointment,
    ):
        """Test that patients can only cancel their own appointments."""
        mock_decode.return_value = "+919999999999"  # Different phone

        response = await client.delete(
            f"/api/v1/public/appointments/{test_appointment.id}",
            headers={
                "Authorization": "Bearer mock-token",
                "Content-Type": "application/json",
            },
            content=json.dumps({"reason": "Test"}),
        )

        assert response.status_code == 404

