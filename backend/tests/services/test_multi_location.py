"""
Tests for Multi-Location Service.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.staff import DEFAULT_PERMISSIONS, StaffAssignment, StaffRole
from app.services.multi_location import MultiLocationService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def service(mock_db):
    """Create a MultiLocationService instance."""
    return MultiLocationService(mock_db)


class TestOrganizationManagement:
    """Tests for organization CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_organization(self, service, mock_db):
        """Test creating an organization."""
        org_id = uuid4()
        owner_id = uuid4()

        # Mock the database query for slug uniqueness
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        org = await service.create_organization(
            name="Apollo Hospitals",
            slug="apollo-hospitals",
            owner_user_id=owner_id,
            subscription_tier="premium",
            max_clinics=10,
            max_users=100,
        )

        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(self, service, mock_db):
        """Test creating organization with duplicate slug fails."""
        owner_id = uuid4()

        # Mock existing organization with same slug
        existing_org = Organization(
            name="Existing Org",
            slug="apollo-hospitals",
            owner_user_id=owner_id,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_org
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already exists"):
            await service.create_organization(
                name="Apollo Hospitals",
                slug="apollo-hospitals",
                owner_user_id=owner_id,
            )

    @pytest.mark.asyncio
    async def test_get_organization(self, service, mock_db):
        """Test getting an organization by ID."""
        org_id = uuid4()

        # This would typically query the database
        # In real tests with a test database, you'd verify the actual query
        org = await service.get_organization(org_id)

        # Verify database query was made
        assert mock_db.execute.called


class TestClinicManagement:
    """Tests for clinic management within organizations."""

    @pytest.mark.asyncio
    async def test_add_clinic_to_organization(self, service, mock_db):
        """Test adding a clinic to an organization."""
        org_id = uuid4()
        clinic_id = uuid4()
        owner_id = uuid4()

        # Mock organization with available slots
        org = Organization(
            id=org_id,
            name="Test Org",
            slug="test-org",
            owner_user_id=owner_id,
            max_clinics=5,
        )
        org.clinics = []  # Empty list = under limit

        # Mock get_organization
        service.get_organization = AsyncMock(return_value=org)

        # Mock clinic
        from app.models.clinic import Clinic

        clinic = Clinic(
            id=clinic_id,
            name="Test Clinic",
            slug="test-clinic",
            phone="9876543210",
            organization_id=None,  # Not assigned yet
        )
        mock_db.get.return_value = clinic

        result = await service.add_clinic_to_organization(org_id, clinic_id)

        assert result is True
        assert clinic.organization_id == org_id
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_add_clinic_exceeds_limit(self, service, mock_db):
        """Test adding clinic when organization is at max limit."""
        org_id = uuid4()
        clinic_id = uuid4()
        owner_id = uuid4()

        # Mock organization at max capacity
        org = Organization(
            id=org_id,
            name="Test Org",
            slug="test-org",
            owner_user_id=owner_id,
            max_clinics=2,
        )
        org.clinics = [MagicMock(), MagicMock()]  # Already at limit

        service.get_organization = AsyncMock(return_value=org)

        with pytest.raises(ValueError, match="maximum clinics limit"):
            await service.add_clinic_to_organization(org_id, clinic_id)


class TestStaffRoleManagement:
    """Tests for staff role operations."""

    @pytest.mark.asyncio
    async def test_create_staff_role(self, service, mock_db):
        """Test creating a staff role."""
        org_id = uuid4()

        # Mock no existing role
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        role = await service.create_staff_role(
            name="Senior Receptionist",
            permissions=["appointments.*", "patients.view"],
            organization_id=org_id,
            description="Senior front desk staff",
        )

        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_db.refresh.called

    @pytest.mark.asyncio
    async def test_create_duplicate_role_fails(self, service, mock_db):
        """Test creating duplicate role in same org fails."""
        org_id = uuid4()

        # Mock existing role
        existing_role = StaffRole(
            name="Receptionist",
            permissions=["appointments.*"],
            organization_id=org_id,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_role
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already exists"):
            await service.create_staff_role(
                name="Receptionist",
                permissions=["appointments.*"],
                organization_id=org_id,
            )

    def test_role_has_permission_exact_match(self):
        """Test role permission checking with exact match."""
        role = StaffRole(
            name="Test Role",
            permissions=["appointments.view", "patients.create"],
            organization_id=None,
        )

        assert role.has_permission("appointments.view") is True
        assert role.has_permission("patients.create") is True
        assert role.has_permission("billing.create") is False

    def test_role_has_permission_wildcard(self):
        """Test role permission checking with wildcards."""
        role = StaffRole(
            name="Test Role",
            permissions=["appointments.*", "patients.view"],
            organization_id=None,
        )

        assert role.has_permission("appointments.view") is True
        assert role.has_permission("appointments.create") is True
        assert role.has_permission("appointments.delete") is True
        assert role.has_permission("patients.view") is True
        assert role.has_permission("patients.create") is False

    def test_role_has_permission_global_admin(self):
        """Test global admin permission."""
        role = StaffRole(
            name="Super Admin",
            permissions=["*"],
            organization_id=None,
        )

        assert role.has_permission("appointments.view") is True
        assert role.has_permission("billing.delete") is True
        assert role.has_permission("anything.anything") is True


class TestStaffAssignmentManagement:
    """Tests for staff assignment operations."""

    @pytest.mark.asyncio
    async def test_assign_staff(self, service, mock_db):
        """Test assigning staff to a clinic."""
        user_id = uuid4()
        clinic_id = uuid4()
        role_id = uuid4()

        # Mock user, clinic, and role exist
        from app.models.user import User
        from app.models.clinic import Clinic

        mock_db.get.side_effect = [
            User(id=user_id, email="test@example.com", phone="1234567890", name="Test User", password_hash="hash"),
            Clinic(id=clinic_id, name="Test Clinic", slug="test-clinic", phone="1234567890"),
            StaffRole(id=role_id, name="Receptionist", permissions=["appointments.*"]),
        ]

        # Mock no existing assignment
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        assignment = await service.assign_staff(
            user_id=user_id,
            clinic_id=clinic_id,
            role_id=role_id,
            is_primary_location=True,
        )

        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_assign_staff_duplicate_fails(self, service, mock_db):
        """Test assigning staff to same clinic twice fails."""
        user_id = uuid4()
        clinic_id = uuid4()
        role_id = uuid4()

        # Mock user, clinic, and role exist
        from app.models.user import User
        from app.models.clinic import Clinic

        mock_db.get.side_effect = [
            User(id=user_id, email="test@example.com", phone="1234567890", name="Test User", password_hash="hash"),
            Clinic(id=clinic_id, name="Test Clinic", slug="test-clinic", phone="1234567890"),
            StaffRole(id=role_id, name="Receptionist", permissions=["appointments.*"]),
        ]

        # Mock existing assignment
        existing = StaffAssignment(
            user_id=user_id,
            clinic_id=clinic_id,
            role_id=role_id,
            is_active=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already has an active assignment"):
            await service.assign_staff(
                user_id=user_id,
                clinic_id=clinic_id,
                role_id=role_id,
            )


class TestPermissionChecking:
    """Tests for permission checking."""

    @pytest.mark.asyncio
    async def test_check_permission_granted(self, service, mock_db):
        """Test permission check when user has permission."""
        user_id = uuid4()
        clinic_id = uuid4()
        role_id = uuid4()

        # Mock assignment with role
        role = StaffRole(
            id=role_id,
            name="Receptionist",
            permissions=["appointments.*", "patients.view"],
        )
        assignment = StaffAssignment(
            user_id=user_id,
            clinic_id=clinic_id,
            role_id=role_id,
            is_active=True,
        )
        assignment.role = role

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        has_perm, matched = await service.check_permission(
            user_id=user_id,
            clinic_id=clinic_id,
            permission="appointments.create",
        )

        assert has_perm is True
        assert matched == "appointments.*"

    @pytest.mark.asyncio
    async def test_check_permission_denied(self, service, mock_db):
        """Test permission check when user lacks permission."""
        user_id = uuid4()
        clinic_id = uuid4()
        role_id = uuid4()

        # Mock assignment with role
        role = StaffRole(
            id=role_id,
            name="Receptionist",
            permissions=["appointments.view"],
        )
        assignment = StaffAssignment(
            user_id=user_id,
            clinic_id=clinic_id,
            role_id=role_id,
            is_active=True,
        )
        assignment.role = role

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment
        mock_db.execute.return_value = mock_result

        has_perm, matched = await service.check_permission(
            user_id=user_id,
            clinic_id=clinic_id,
            permission="billing.create",
        )

        assert has_perm is False
        assert matched is None

    @pytest.mark.asyncio
    async def test_check_permission_no_assignment(self, service, mock_db):
        """Test permission check when user has no assignment."""
        user_id = uuid4()
        clinic_id = uuid4()

        # Mock no assignment
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        has_perm, matched = await service.check_permission(
            user_id=user_id,
            clinic_id=clinic_id,
            permission="appointments.view",
        )

        assert has_perm is False
        assert matched is None


class TestDefaultPermissions:
    """Tests for default permission sets."""

    def test_default_permissions_exist(self):
        """Test that default permissions are defined."""
        assert "super_admin" in DEFAULT_PERMISSIONS
        assert "doctor" in DEFAULT_PERMISSIONS
        assert "receptionist" in DEFAULT_PERMISSIONS
        assert "billing_staff" in DEFAULT_PERMISSIONS

    def test_super_admin_has_all_permissions(self):
        """Test that super_admin has wildcard permission."""
        assert "*" in DEFAULT_PERMISSIONS["super_admin"] or "organizations.*" in DEFAULT_PERMISSIONS["super_admin"]

    def test_doctor_has_patient_permissions(self):
        """Test that doctor role has patient-related permissions."""
        doctor_perms = DEFAULT_PERMISSIONS["doctor"]
        assert any("patients" in perm for perm in doctor_perms)

    def test_receptionist_has_appointment_permissions(self):
        """Test that receptionist has appointment permissions."""
        receptionist_perms = DEFAULT_PERMISSIONS["receptionist"]
        assert any("appointments" in perm for perm in receptionist_perms)


class TestStaffTransfer:
    """Tests for staff transfer between locations."""

    @pytest.mark.asyncio
    async def test_transfer_staff(self, service, mock_db):
        """Test transferring staff from one clinic to another."""
        user_id = uuid4()
        from_clinic_id = uuid4()
        to_clinic_id = uuid4()
        role_id = uuid4()

        # Mock current assignment
        current_assignment = StaffAssignment(
            id=uuid4(),
            user_id=user_id,
            clinic_id=from_clinic_id,
            role_id=role_id,
            is_active=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = current_assignment
        mock_db.execute.return_value = mock_result

        # Mock methods
        service.end_staff_assignment = AsyncMock(return_value=True)
        service.assign_staff = AsyncMock(return_value=StaffAssignment(
            user_id=user_id,
            clinic_id=to_clinic_id,
            role_id=role_id,
            is_active=True,
        ))

        new_assignment = await service.transfer_staff(
            user_id=user_id,
            from_clinic_id=from_clinic_id,
            to_clinic_id=to_clinic_id,
            role_id=role_id,
        )

        assert service.end_staff_assignment.called
        assert service.assign_staff.called
        assert new_assignment.clinic_id == to_clinic_id
