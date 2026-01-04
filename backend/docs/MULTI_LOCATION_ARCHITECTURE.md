# Multi-Location & Staff Management Architecture

**Phase 15 Implementation for DocAssist Practice Manager**

## Overview

This document describes the multi-location and staff management architecture that enables DocAssist Practice Manager to scale from single-clinic operations to hospital chains and multi-location practices.

## Architecture Hierarchy

```
Organization (e.g., "Apollo Hospitals")
    ├── Clinic 1 (e.g., "Apollo Chennai")
    ├── Clinic 2 (e.g., "Apollo Bangalore")
    └── Clinic 3 (e.g., "Apollo Delhi")

Staff Members
    ├── Can work at multiple clinics
    ├── Have different roles at each location
    └── One clinic marked as "primary location"

Patients
    ├── Visible across all clinics in organization
    └── Can book appointments at any location
```

## Database Schema

### 1. Organizations Table

**Purpose:** Parent entity for multi-location practice groups

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Basic Info
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,

    -- Owner
    owner_user_id UUID REFERENCES users(id),

    -- Subscription & Limits
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_expires_at VARCHAR(50),
    max_clinics INTEGER DEFAULT 1,
    max_users INTEGER DEFAULT 5,

    -- Branding
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#1976D2',

    -- Contact
    email VARCHAR(255),
    phone VARCHAR(15),
    website VARCHAR(255),

    -- Status
    is_active BOOLEAN DEFAULT TRUE
);
```

### 2. Clinics Table (Updated)

**Changes:** Added `organization_id` field (nullable for backward compatibility)

```sql
ALTER TABLE clinics
ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

CREATE INDEX ix_clinics_organization_id ON clinics(organization_id);
```

### 3. Staff Roles Table

**Purpose:** Define custom roles with granular permissions

```sql
CREATE TABLE staff_roles (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Basic Info
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Permissions (JSONB array)
    permissions JSONB NOT NULL DEFAULT '[]',

    -- Organization (NULL = system-wide role)
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Flags
    is_system BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,

    CONSTRAINT uq_role_name_org UNIQUE (name, organization_id)
);
```

**Permission Format:**
- `appointments.view` - View appointments
- `appointments.create` - Create appointments
- `appointments.*` - All appointment permissions
- `*` - Global admin (all permissions)

### 4. Staff Assignments Table

**Purpose:** Assign staff to clinics with specific roles

```sql
CREATE TABLE staff_assignments (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Assignment
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    clinic_id UUID REFERENCES clinics(id) ON DELETE CASCADE,
    role_id UUID REFERENCES staff_roles(id) ON DELETE RESTRICT,

    -- Location Preference
    is_primary_location BOOLEAN DEFAULT FALSE,

    -- Employment Period
    start_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    end_date TIMESTAMP WITH TIME ZONE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,

    CONSTRAINT uq_user_clinic_active UNIQUE (user_id, clinic_id)
    WHERE is_active = TRUE
);
```

## API Endpoints

### Organizations API (`/api/v1/organizations`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/` | Create organization | Admin |
| GET | `/` | List all organizations | Admin |
| GET | `/{id}` | Get organization details | User (own org) |
| GET | `/slug/{slug}` | Get organization by slug | User |
| PATCH | `/{id}` | Update organization | Admin |
| POST | `/{id}/clinics` | Add clinic to org | Admin |
| DELETE | `/{id}/clinics/{clinic_id}` | Remove clinic from org | Admin |
| GET | `/{id}/clinics` | List org clinics | User (own org) |
| GET | `/{id}/analytics` | Org-wide analytics | User (own org) |

### Staff Management API (`/api/v1/staff`)

#### Roles

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/roles` | Create staff role | Admin |
| GET | `/roles` | List roles | User |
| GET | `/roles/{id}` | Get role details | User |
| PATCH | `/roles/{id}` | Update role | Admin |
| DELETE | `/roles/{id}` | Delete role | Admin |
| POST | `/roles/seed` | Seed default roles | Admin |

#### Assignments

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/assignments` | Assign staff to clinic | Admin |
| GET | `/assignments/{id}` | Get assignment details | User |
| PATCH | `/assignments/{id}` | Update assignment | Admin |
| DELETE | `/assignments/{id}` | End assignment | Admin |
| GET | `/users/{id}/assignments` | Get user's assignments | User (self) / Admin |
| GET | `/clinics/{id}/staff` | Get clinic staff | User (clinic) / Admin |
| POST | `/transfer` | Transfer staff between locations | Admin |

#### Permissions

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/permissions/check` | Check user permission | User (self) / Admin |

## Permission System

### Default Roles

```python
DEFAULT_PERMISSIONS = {
    "super_admin": ["*"],
    "clinic_admin": [
        "appointments.*",
        "patients.*",
        "billing.*",
        "reports.view",
        "staff.view",
        "settings.view",
    ],
    "doctor": [
        "appointments.view",
        "appointments.update",
        "appointments.complete",
        "patients.view",
        "patients.create",
        "patients.update",
        "procedures.*",
        "documents.*",
    ],
    "receptionist": [
        "appointments.*",
        "patients.view",
        "patients.create",
        "patients.update",
        "billing.create",
        "billing.view",
        "waitlist.*",
    ],
    "billing_staff": [
        "billing.*",
        "patients.view",
        "invoices.*",
        "payments.*",
        "reports.billing",
    ],
}
```

### Permission Checking

```python
# Check if user has permission at a clinic
has_permission, matched_rule = await service.check_permission(
    user_id=user_id,
    clinic_id=clinic_id,
    permission="appointments.create"
)

if has_permission:
    # Allow action
    pass
```

## Service Layer

### MultiLocationService

**Location:** `/home/user/appointment_system/backend/app/services/multi_location.py`

**Key Methods:**

```python
class MultiLocationService:
    # Organization Management
    async def create_organization(...)
    async def get_organization(org_id)
    async def update_organization(org_id, **updates)
    async def list_organizations(skip, limit, is_active)

    # Clinic Management
    async def add_clinic_to_organization(org_id, clinic_id)
    async def remove_clinic_from_organization(org_id, clinic_id)
    async def get_organization_clinics(org_id)

    # Staff Role Management
    async def create_staff_role(name, permissions, ...)
    async def update_staff_role(role_id, **updates)
    async def list_staff_roles(organization_id, include_system)
    async def delete_staff_role(role_id)

    # Staff Assignment Management
    async def assign_staff(user_id, clinic_id, role_id, ...)
    async def update_staff_assignment(assignment_id, **updates)
    async def end_staff_assignment(assignment_id, end_date)
    async def get_user_assignments(user_id, active_only)
    async def get_clinic_staff(clinic_id, active_only)
    async def transfer_staff(user_id, from_clinic_id, to_clinic_id, ...)

    # Permission Checking
    async def check_permission(user_id, clinic_id, permission)

    # Analytics
    async def get_organization_stats(org_id, start_date, end_date)

    # Setup
    async def seed_default_roles(organization_id)
```

## Mobile Integration

### Models

**Location:** `/home/user/appointment_system/mobile/lib/core/models/`

- `organization.dart` - Organization model
- `staff_assignment.dart` - Staff assignment and role models

### Providers

**Location:** `/home/user/appointment_system/mobile/lib/core/providers/location_provider.dart`

```dart
// Location state management
final locationProvider = StateNotifierProvider<LocationNotifier, LocationState>((ref) {
  return LocationNotifier(apiClient, prefs);
});

// Current clinic ID
final currentClinicIdProvider = Provider<String?>((ref) {
  return ref.watch(locationProvider).currentClinicId;
});

// Check if user has multiple locations
final hasMultipleLocationsProvider = Provider<bool>((ref) {
  return ref.watch(locationProvider).hasMultipleLocations;
});
```

### UI Components

**Location:** `/home/user/appointment_system/mobile/lib/core/widgets/location_selector.dart`

- `LocationSelector` - Compact dropdown in app bar
- `LocationSelectorDialog` - Full-screen location picker

**Usage:**

```dart
// In app bar
AppBar(
  title: Text('Dashboard'),
  actions: [
    LocationSelector(),
    IconButton(icon: Icon(Icons.settings), onPressed: ...),
  ],
)

// Show full dialog
ElevatedButton(
  onPressed: () => LocationSelectorDialog.show(context),
  child: Text('Switch Location'),
)
```

## Migration Guide

### Running the Migration

```bash
cd backend

# Apply migration
alembic upgrade head

# Verify migration
alembic current

# If needed, rollback
alembic downgrade 007_add_emr_sync_fields
```

### Data Migration for Existing Clinics

Existing standalone clinics continue to work without changes:
- `organization_id` is nullable
- All existing functionality preserved
- Can be added to organization later

To migrate existing clinics to an organization:

```python
# 1. Create organization
org = await multi_location_service.create_organization(
    name="My Practice Group",
    slug="my-practice-group",
    owner_user_id=admin_user_id,
)

# 2. Add clinics
await multi_location_service.add_clinic_to_organization(
    org_id=org.id,
    clinic_id=existing_clinic_id,
)

# 3. Assign existing users
for user in clinic_users:
    await multi_location_service.assign_staff(
        user_id=user.id,
        clinic_id=clinic.id,
        role_id=appropriate_role_id,
        is_primary_location=True,
    )
```

## Testing

**Location:** `/home/user/appointment_system/backend/tests/services/test_multi_location.py`

**Coverage:**
- Organization CRUD operations
- Clinic association management
- Staff role creation and permissions
- Staff assignment workflows
- Permission checking logic
- Staff transfer between locations

**Run Tests:**

```bash
cd backend
pytest tests/services/test_multi_location.py -v
```

## Usage Examples

### 1. Create Hospital Chain

```python
# Create organization
org = await service.create_organization(
    name="Apollo Hospitals",
    slug="apollo-hospitals",
    owner_user_id=admin_id,
    subscription_tier="enterprise",
    max_clinics=50,
    max_users=500,
)

# Seed default roles
await service.seed_default_roles(organization_id=org.id)

# Add clinics
await service.add_clinic_to_organization(org.id, apollo_chennai_id)
await service.add_clinic_to_organization(org.id, apollo_bangalore_id)
await service.add_clinic_to_organization(org.id, apollo_delhi_id)
```

### 2. Assign Doctor to Multiple Locations

```python
# Get doctor role
doctor_role = await service.list_staff_roles(organization_id=org.id)
doctor_role_id = next(r.id for r in roles if r.name == "doctor")

# Assign to Chennai (primary)
await service.assign_staff(
    user_id=dr_sharma_id,
    clinic_id=apollo_chennai_id,
    role_id=doctor_role_id,
    is_primary_location=True,
)

# Assign to Bangalore (secondary)
await service.assign_staff(
    user_id=dr_sharma_id,
    clinic_id=apollo_bangalore_id,
    role_id=doctor_role_id,
    is_primary_location=False,
)
```

### 3. Transfer Staff

```python
# Transfer receptionist from Chennai to Delhi
await service.transfer_staff(
    user_id=receptionist_id,
    from_clinic_id=apollo_chennai_id,
    to_clinic_id=apollo_delhi_id,
    make_primary=True,
    transfer_date=datetime.now(),
)
```

### 4. Check Permissions

```python
# Check if user can create appointments at a clinic
can_create, matched_perm = await service.check_permission(
    user_id=user_id,
    clinic_id=clinic_id,
    permission="appointments.create",
)

if can_create:
    # Proceed with appointment creation
    pass
else:
    raise HTTPException(403, "Permission denied")
```

## Files Created

### Backend

1. **Models**
   - `/home/user/appointment_system/backend/app/models/organization.py`
   - `/home/user/appointment_system/backend/app/models/staff.py`
   - Updated: `/home/user/appointment_system/backend/app/models/clinic.py`
   - Updated: `/home/user/appointment_system/backend/app/models/__init__.py`

2. **Schemas**
   - `/home/user/appointment_system/backend/app/schemas/organization.py`
   - `/home/user/appointment_system/backend/app/schemas/staff.py`
   - Updated: `/home/user/appointment_system/backend/app/schemas/__init__.py`

3. **Services**
   - `/home/user/appointment_system/backend/app/services/multi_location.py`

4. **API Endpoints**
   - `/home/user/appointment_system/backend/app/api/v1/organizations.py`
   - `/home/user/appointment_system/backend/app/api/v1/staff.py`
   - Updated: `/home/user/appointment_system/backend/app/api/v1/__init__.py`

5. **Migrations**
   - `/home/user/appointment_system/backend/alembic/versions/008_add_multi_location.py`

6. **Tests**
   - `/home/user/appointment_system/backend/tests/services/test_multi_location.py`

### Mobile

1. **Models**
   - `/home/user/appointment_system/mobile/lib/core/models/organization.dart`
   - `/home/user/appointment_system/mobile/lib/core/models/staff_assignment.dart`

2. **Providers**
   - `/home/user/appointment_system/mobile/lib/core/providers/location_provider.dart`

3. **Widgets**
   - `/home/user/appointment_system/mobile/lib/core/widgets/location_selector.dart`

### Documentation

1. **Architecture Guide**
   - `/home/user/appointment_system/backend/docs/MULTI_LOCATION_ARCHITECTURE.md` (this file)

## Next Steps

1. **Run Migration**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Seed Default Roles**
   ```bash
   # Via API or Python script
   POST /api/v1/staff/roles/seed
   ```

3. **Test in Development**
   - Create test organization
   - Add clinics
   - Assign staff
   - Test location switching in mobile app

4. **Mobile App Integration**
   - Add location selector to app bar
   - Update API calls to use current clinic context
   - Add organization branding support

5. **Future Enhancements**
   - Staff performance metrics per location
   - Cross-location reporting
   - Organization-wide patient search
   - Consolidated billing across locations
   - Branch comparison dashboards

## Support

For questions or issues:
- Review this documentation
- Check test files for examples
- See API endpoint documentation in FastAPI `/docs`
- Refer to CLAUDE.md for development guidelines

---

**Last Updated:** 2026-01-04
**Version:** 1.0
**Phase:** 15 - Multi-Location & Staff Management
