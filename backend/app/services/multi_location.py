"""
Multi-Location Service for Organization and Staff Management.

Provides comprehensive multi-location support:
- Organization CRUD operations
- Clinic management under organizations
- Staff role management with permissions
- Staff assignments to locations
- Cross-location patient access
- Consolidated analytics
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.staff import DEFAULT_PERMISSIONS, StaffAssignment, StaffRole
from app.models.user import User
from app.schemas.organization import OrganizationStats

logger = logging.getLogger(__name__)


class MultiLocationService:
    """
    Service for multi-location practice management.

    Handles organization-level operations, staff management,
    and cross-location data access.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    # ==================== Organization Management ====================

    async def create_organization(
        self,
        name: str,
        slug: str,
        owner_user_id: UUID,
        **kwargs,
    ) -> Organization:
        """
        Create a new organization.

        Args:
            name: Organization name
            slug: URL-friendly unique identifier
            owner_user_id: User ID of the owner
            **kwargs: Additional organization fields

        Returns:
            Created organization

        Raises:
            ValueError: If slug already exists
        """
        # Check slug uniqueness
        existing = await self.db.execute(select(Organization).where(Organization.slug == slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Organization with slug '{slug}' already exists")

        org = Organization(
            name=name,
            slug=slug,
            owner_user_id=owner_user_id,
            **kwargs,
        )
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)

        logger.info(f"Created organization: {org.name} (ID: {org.id})")
        return org

    async def get_organization(self, org_id: UUID) -> Optional[Organization]:
        """Get organization by ID with relationships loaded."""
        result = await self.db.execute(
            select(Organization)
            .where(Organization.id == org_id)
            .options(selectinload(Organization.clinics), selectinload(Organization.staff_roles))
        )
        return result.scalar_one_or_none()

    async def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        result = await self.db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def update_organization(self, org_id: UUID, **updates) -> Optional[Organization]:
        """Update organization fields."""
        org = await self.get_organization(org_id)
        if not org:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(org, key):
                setattr(org, key, value)

        await self.db.commit()
        await self.db.refresh(org)
        logger.info(f"Updated organization: {org.name}")
        return org

    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> list[Organization]:
        """List all organizations with pagination."""
        query = select(Organization)

        if is_active is not None:
            query = query.where(Organization.is_active == is_active)

        query = query.offset(skip).limit(limit).order_by(Organization.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Clinic Management ====================

    async def add_clinic_to_organization(self, org_id: UUID, clinic_id: UUID) -> bool:
        """
        Add a clinic to an organization.

        Args:
            org_id: Organization ID
            clinic_id: Clinic ID

        Returns:
            True if successful

        Raises:
            ValueError: If limits exceeded or clinic already assigned
        """
        org = await self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        # Check clinic limit
        if len(org.clinics) >= org.max_clinics:
            raise ValueError(f"Organization has reached maximum clinics limit ({org.max_clinics})")

        # Get clinic
        clinic = await self.db.get(Clinic, clinic_id)
        if not clinic:
            raise ValueError("Clinic not found")

        if clinic.organization_id:
            raise ValueError("Clinic is already part of an organization")

        clinic.organization_id = org_id
        await self.db.commit()

        logger.info(f"Added clinic {clinic.name} to organization {org.name}")
        return True

    async def remove_clinic_from_organization(self, org_id: UUID, clinic_id: UUID) -> bool:
        """
        Remove a clinic from an organization.

        Args:
            org_id: Organization ID
            clinic_id: Clinic ID

        Returns:
            True if successful
        """
        clinic = await self.db.get(Clinic, clinic_id)
        if not clinic or clinic.organization_id != org_id:
            raise ValueError("Clinic not found in this organization")

        clinic.organization_id = None
        await self.db.commit()

        logger.info(f"Removed clinic {clinic.name} from organization")
        return True

    async def get_organization_clinics(self, org_id: UUID) -> list[Clinic]:
        """Get all clinics belonging to an organization."""
        result = await self.db.execute(
            select(Clinic).where(Clinic.organization_id == org_id, Clinic.is_active == True)
        )
        return list(result.scalars().all())

    # ==================== Staff Role Management ====================

    async def create_staff_role(
        self,
        name: str,
        permissions: list[str],
        organization_id: Optional[UUID] = None,
        description: Optional[str] = None,
        is_system: bool = False,
    ) -> StaffRole:
        """
        Create a new staff role.

        Args:
            name: Role name
            permissions: List of permission strings
            organization_id: Organization ID (None for system-wide)
            description: Role description
            is_system: Whether this is a system role

        Returns:
            Created role
        """
        # Check uniqueness
        existing = await self.db.execute(
            select(StaffRole).where(
                StaffRole.name == name, StaffRole.organization_id == organization_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(
                f"Role '{name}' already exists in this organization"
            )

        role = StaffRole(
            name=name,
            description=description,
            permissions=permissions,  # Store as list in JSONB
            organization_id=organization_id,
            is_system=is_system,
        )
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)

        logger.info(f"Created staff role: {role.name}")
        return role

    async def get_staff_role(self, role_id: UUID) -> Optional[StaffRole]:
        """Get staff role by ID."""
        return await self.db.get(StaffRole, role_id)

    async def update_staff_role(self, role_id: UUID, **updates) -> Optional[StaffRole]:
        """Update staff role."""
        role = await self.get_staff_role(role_id)
        if not role:
            return None

        if role.is_system:
            raise ValueError("Cannot modify system roles")

        for key, value in updates.items():
            if value is not None and hasattr(role, key):
                setattr(role, key, value)

        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def list_staff_roles(
        self,
        organization_id: Optional[UUID] = None,
        include_system: bool = True,
    ) -> list[StaffRole]:
        """
        List staff roles.

        Args:
            organization_id: Filter by organization (None for system roles)
            include_system: Whether to include system roles

        Returns:
            List of roles
        """
        conditions = [StaffRole.is_active == True]

        if organization_id:
            if include_system:
                conditions.append(
                    or_(
                        StaffRole.organization_id == organization_id,
                        StaffRole.organization_id.is_(None),
                    )
                )
            else:
                conditions.append(StaffRole.organization_id == organization_id)
        else:
            conditions.append(StaffRole.organization_id.is_(None))

        result = await self.db.execute(select(StaffRole).where(and_(*conditions)))
        return list(result.scalars().all())

    async def delete_staff_role(self, role_id: UUID) -> bool:
        """Delete a staff role (soft delete)."""
        role = await self.get_staff_role(role_id)
        if not role:
            return False

        if role.is_system:
            raise ValueError("Cannot delete system roles")

        # Check if role is in use
        result = await self.db.execute(
            select(func.count(StaffAssignment.id)).where(
                StaffAssignment.role_id == role_id, StaffAssignment.is_active == True
            )
        )
        if result.scalar() > 0:
            raise ValueError("Cannot delete role that is currently assigned to staff")

        role.is_active = False
        await self.db.commit()
        return True

    # ==================== Staff Assignment Management ====================

    async def assign_staff(
        self,
        user_id: UUID,
        clinic_id: UUID,
        role_id: UUID,
        is_primary_location: bool = False,
        start_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> StaffAssignment:
        """
        Assign a staff member to a clinic with a role.

        Args:
            user_id: User/staff ID
            clinic_id: Clinic ID
            role_id: Role ID
            is_primary_location: Whether this is primary location
            start_date: Assignment start date (defaults to now)
            notes: Additional notes

        Returns:
            Created assignment

        Raises:
            ValueError: If validation fails
        """
        # Validate user, clinic, and role exist
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        clinic = await self.db.get(Clinic, clinic_id)
        if not clinic:
            raise ValueError("Clinic not found")

        role = await self.db.get(StaffRole, role_id)
        if not role:
            raise ValueError("Role not found")

        # Check if user already has active assignment at this clinic
        existing = await self.db.execute(
            select(StaffAssignment).where(
                StaffAssignment.user_id == user_id,
                StaffAssignment.clinic_id == clinic_id,
                StaffAssignment.is_active == True,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("User already has an active assignment at this clinic")

        # If this is primary location, unset other primary assignments
        if is_primary_location:
            await self.db.execute(
                select(StaffAssignment)
                .where(
                    StaffAssignment.user_id == user_id,
                    StaffAssignment.is_primary_location == True,
                )
            )
            # Note: We'll need to update these in a loop
            result = await self.db.execute(
                select(StaffAssignment).where(
                    StaffAssignment.user_id == user_id,
                    StaffAssignment.is_primary_location == True,
                )
            )
            for assignment in result.scalars().all():
                assignment.is_primary_location = False

        assignment = StaffAssignment(
            user_id=user_id,
            clinic_id=clinic_id,
            role_id=role_id,
            is_primary_location=is_primary_location,
            start_date=start_date or datetime.utcnow(),
            notes=notes,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)

        logger.info(f"Assigned user {user_id} to clinic {clinic_id} with role {role_id}")
        return assignment

    async def get_staff_assignment(self, assignment_id: UUID) -> Optional[StaffAssignment]:
        """Get staff assignment by ID with relationships."""
        result = await self.db.execute(
            select(StaffAssignment)
            .where(StaffAssignment.id == assignment_id)
            .options(
                joinedload(StaffAssignment.user),
                joinedload(StaffAssignment.clinic),
                joinedload(StaffAssignment.role),
            )
        )
        return result.scalar_one_or_none()

    async def update_staff_assignment(
        self,
        assignment_id: UUID,
        **updates,
    ) -> Optional[StaffAssignment]:
        """Update staff assignment."""
        assignment = await self.get_staff_assignment(assignment_id)
        if not assignment:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(assignment, key):
                setattr(assignment, key, value)

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def end_staff_assignment(self, assignment_id: UUID, end_date: Optional[datetime] = None) -> bool:
        """End a staff assignment."""
        assignment = await self.get_staff_assignment(assignment_id)
        if not assignment:
            return False

        assignment.end_date = end_date or datetime.utcnow()
        assignment.is_active = False
        await self.db.commit()

        logger.info(f"Ended staff assignment {assignment_id}")
        return True

    async def get_user_assignments(
        self,
        user_id: UUID,
        active_only: bool = True,
    ) -> list[StaffAssignment]:
        """Get all assignments for a user."""
        query = select(StaffAssignment).where(StaffAssignment.user_id == user_id)

        if active_only:
            query = query.where(StaffAssignment.is_active == True)

        query = query.options(
            joinedload(StaffAssignment.clinic),
            joinedload(StaffAssignment.role),
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_clinic_staff(
        self,
        clinic_id: UUID,
        active_only: bool = True,
    ) -> list[StaffAssignment]:
        """Get all staff assigned to a clinic."""
        query = select(StaffAssignment).where(StaffAssignment.clinic_id == clinic_id)

        if active_only:
            query = query.where(StaffAssignment.is_active == True)

        query = query.options(
            joinedload(StaffAssignment.user),
            joinedload(StaffAssignment.role),
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def transfer_staff(
        self,
        user_id: UUID,
        from_clinic_id: UUID,
        to_clinic_id: UUID,
        role_id: Optional[UUID] = None,
        make_primary: bool = False,
        transfer_date: Optional[datetime] = None,
    ) -> StaffAssignment:
        """
        Transfer a staff member from one clinic to another.

        Ends the current assignment and creates a new one.

        Args:
            user_id: User ID
            from_clinic_id: Current clinic ID
            to_clinic_id: New clinic ID
            role_id: New role ID (None to keep same role)
            make_primary: Make new location primary
            transfer_date: Transfer date (defaults to now)

        Returns:
            New assignment
        """
        # Get current assignment
        current = await self.db.execute(
            select(StaffAssignment).where(
                StaffAssignment.user_id == user_id,
                StaffAssignment.clinic_id == from_clinic_id,
                StaffAssignment.is_active == True,
            )
        )
        current_assignment = current.scalar_one_or_none()
        if not current_assignment:
            raise ValueError("No active assignment found at source clinic")

        # End current assignment
        transfer_dt = transfer_date or datetime.utcnow()
        await self.end_staff_assignment(current_assignment.id, transfer_dt)

        # Create new assignment
        new_role_id = role_id or current_assignment.role_id
        new_assignment = await self.assign_staff(
            user_id=user_id,
            clinic_id=to_clinic_id,
            role_id=new_role_id,
            is_primary_location=make_primary,
            start_date=transfer_dt,
            notes=f"Transferred from clinic {from_clinic_id}",
        )

        logger.info(f"Transferred user {user_id} from clinic {from_clinic_id} to {to_clinic_id}")
        return new_assignment

    # ==================== Permission Checking ====================

    async def check_permission(
        self,
        user_id: UUID,
        clinic_id: UUID,
        permission: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a user has a specific permission at a clinic.

        Args:
            user_id: User ID
            clinic_id: Clinic ID
            permission: Permission string (e.g., "appointments.create")

        Returns:
            Tuple of (has_permission, matched_permission_rule)
        """
        # Get user's assignment at this clinic
        result = await self.db.execute(
            select(StaffAssignment)
            .where(
                StaffAssignment.user_id == user_id,
                StaffAssignment.clinic_id == clinic_id,
                StaffAssignment.is_active == True,
            )
            .options(joinedload(StaffAssignment.role))
        )
        assignment = result.scalar_one_or_none()

        if not assignment or not assignment.role:
            return (False, None)

        # Check role permission
        role = assignment.role
        if role.has_permission(permission):
            # Find which permission matched
            for perm in role.permissions:
                if perm == permission or perm == "*":
                    return (True, perm)
                if perm.endswith(".*"):
                    prefix = perm[:-2]
                    if permission.startswith(f"{prefix}."):
                        return (True, perm)

        return (False, None)

    # ==================== Consolidated Analytics ====================

    async def get_organization_stats(
        self,
        org_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> OrganizationStats:
        """
        Get consolidated statistics for an organization.

        Args:
            org_id: Organization ID
            start_date: Start date for metrics
            end_date: End date for metrics

        Returns:
            Organization statistics
        """
        # Get all clinics in organization
        clinics = await self.get_organization_clinics(org_id)
        clinic_ids = [c.id for c in clinics]

        if not clinic_ids:
            return OrganizationStats(
                total_clinics=0,
                total_users=0,
                total_patients=0,
                total_appointments_today=0,
                total_revenue_month=0.0,
                revenue_by_clinic={},
                appointments_by_clinic={},
                top_performing_clinic=None,
            )

        # Total users across all clinics
        user_count_result = await self.db.execute(
            select(func.count(func.distinct(User.id))).where(User.clinic_id.in_(clinic_ids))
        )
        total_users = user_count_result.scalar() or 0

        # Total patients across all clinics
        patient_count_result = await self.db.execute(
            select(func.count(Patient.id)).where(Patient.clinic_id.in_(clinic_ids))
        )
        total_patients = patient_count_result.scalar() or 0

        # Appointments today
        from datetime import date as date_type

        today = date_type.today()
        appt_today_result = await self.db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.clinic_id.in_(clinic_ids),
                func.date(Appointment.scheduled_at) == today,
            )
        )
        total_appointments_today = appt_today_result.scalar() or 0

        # Revenue by clinic (this month)
        # Note: Simplified - you may want to join with payments
        revenue_by_clinic = {}
        appointments_by_clinic = {}

        for clinic in clinics:
            # Count appointments
            appt_result = await self.db.execute(
                select(func.count(Appointment.id)).where(
                    Appointment.clinic_id == clinic.id,
                    func.date(Appointment.scheduled_at) == today,
                )
            )
            appt_count = appt_result.scalar() or 0
            appointments_by_clinic[str(clinic.id)] = appt_count

            # For revenue, you'd typically join with invoices/payments
            # Simplified placeholder
            revenue_by_clinic[str(clinic.id)] = 0.0

        total_revenue_month = sum(revenue_by_clinic.values())

        # Find top performing clinic
        top_clinic = max(revenue_by_clinic.items(), key=lambda x: x[1])[0] if revenue_by_clinic else None

        return OrganizationStats(
            total_clinics=len(clinics),
            total_users=total_users,
            total_patients=total_patients,
            total_appointments_today=total_appointments_today,
            total_revenue_month=total_revenue_month,
            revenue_by_clinic=revenue_by_clinic,
            appointments_by_clinic=appointments_by_clinic,
            top_performing_clinic=top_clinic,
        )

    # ==================== Seed Default Roles ====================

    async def seed_default_roles(self, organization_id: Optional[UUID] = None) -> list[StaffRole]:
        """
        Seed default staff roles for an organization.

        Args:
            organization_id: Organization ID (None for system-wide)

        Returns:
            List of created roles
        """
        roles = []
        for role_name, permissions in DEFAULT_PERMISSIONS.items():
            try:
                role = await self.create_staff_role(
                    name=role_name,
                    permissions=permissions,
                    organization_id=organization_id,
                    description=f"Default {role_name} role",
                    is_system=(organization_id is None),
                )
                roles.append(role)
            except ValueError as e:
                # Role might already exist
                logger.warning(f"Could not create role {role_name}: {e}")
                continue

        logger.info(f"Seeded {len(roles)} default roles")
        return roles
