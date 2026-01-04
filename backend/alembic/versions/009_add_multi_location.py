"""Add multi-location and staff management tables

Revision ID: 009_add_multi_location
Revises: 008_add_insurance_billing
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_add_multi_location'
down_revision: Union[str, None] = '008_add_insurance_billing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Basic info
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # Owner
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),

        # Subscription & Limits
        sa.Column('subscription_tier', sa.String(20), default='free'),
        sa.Column('subscription_expires_at', sa.String(50), nullable=True),
        sa.Column('max_clinics', sa.Integer, default=1),
        sa.Column('max_users', sa.Integer, default=5),

        # Branding
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), default='#1976D2'),

        # Contact
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(15), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),
    )

    # Create indexes
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])
    op.create_index('ix_organizations_owner_user_id', 'organizations', ['owner_user_id'])

    # Add organization_id to clinics table (backward compatible)
    op.add_column(
        'clinics',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_clinics_organization_id',
        'clinics',
        'organizations',
        ['organization_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_clinics_organization_id', 'clinics', ['organization_id'])

    # Create staff_roles table
    op.create_table(
        'staff_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Basic info
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # Permissions (JSON array)
        sa.Column('permissions', postgresql.JSONB, nullable=False, default=[]),

        # Organization (nullable for system-wide roles)
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),

        # System flags
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
    )

    # Create indexes and unique constraint
    op.create_index('ix_staff_roles_organization_id', 'staff_roles', ['organization_id'])
    op.create_index('ix_staff_roles_is_system', 'staff_roles', ['is_system'])

    # Unique constraint: role name must be unique within organization
    # Note: PostgreSQL allows multiple NULLs in unique constraints
    op.execute("""
        CREATE UNIQUE INDEX uq_role_name_org
        ON staff_roles (name, organization_id)
    """)

    # Create staff_assignments table
    op.create_table(
        'staff_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        # Assignment
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clinics.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('staff_roles.id', ondelete='RESTRICT'), nullable=False),

        # Location preference
        sa.Column('is_primary_location', sa.Boolean, default=False),

        # Employment period
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),
    )

    # Create indexes
    op.create_index('ix_staff_assignments_user_id', 'staff_assignments', ['user_id'])
    op.create_index('ix_staff_assignments_clinic_id', 'staff_assignments', ['clinic_id'])
    op.create_index('ix_staff_assignments_role_id', 'staff_assignments', ['role_id'])
    op.create_index('ix_staff_assignments_is_active', 'staff_assignments', ['is_active'])
    op.create_index('ix_staff_assignments_is_primary', 'staff_assignments', ['is_primary_location'])

    # Composite index for finding active assignments
    op.create_index(
        'ix_staff_assignments_active_lookup',
        'staff_assignments',
        ['user_id', 'clinic_id', 'is_active']
    )

    # Unique constraint: user can only have one active assignment per clinic
    # Using partial unique index for PostgreSQL
    op.execute("""
        CREATE UNIQUE INDEX uq_user_clinic_active
        ON staff_assignments (user_id, clinic_id)
        WHERE is_active = true
    """)


def downgrade() -> None:
    # Drop staff_assignments table
    op.execute("DROP INDEX IF EXISTS uq_user_clinic_active")
    op.drop_index('ix_staff_assignments_active_lookup')
    op.drop_index('ix_staff_assignments_is_primary')
    op.drop_index('ix_staff_assignments_is_active')
    op.drop_index('ix_staff_assignments_role_id')
    op.drop_index('ix_staff_assignments_clinic_id')
    op.drop_index('ix_staff_assignments_user_id')
    op.drop_table('staff_assignments')

    # Drop staff_roles table
    op.execute("DROP INDEX IF EXISTS uq_role_name_org")
    op.drop_index('ix_staff_roles_is_system')
    op.drop_index('ix_staff_roles_organization_id')
    op.drop_table('staff_roles')

    # Remove organization_id from clinics
    op.drop_index('ix_clinics_organization_id')
    op.drop_constraint('fk_clinics_organization_id', 'clinics', type_='foreignkey')
    op.drop_column('clinics', 'organization_id')

    # Drop organizations table
    op.drop_index('ix_organizations_owner_user_id')
    op.drop_index('ix_organizations_slug')
    op.drop_table('organizations')
