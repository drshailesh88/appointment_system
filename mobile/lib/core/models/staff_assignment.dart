/// Staff assignment model for multi-location access
///
/// Represents a user's assignment to a clinic with a specific role.
class StaffAssignment {
  final String id;
  final String userId;
  final String clinicId;
  final String roleId;
  final bool isPrimaryLocation;
  final DateTime startDate;
  final DateTime? endDate;
  final bool isActive;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Nested data
  final String? userName;
  final String? clinicName;
  final String? roleName;

  StaffAssignment({
    required this.id,
    required this.userId,
    required this.clinicId,
    required this.roleId,
    required this.isPrimaryLocation,
    required this.startDate,
    this.endDate,
    required this.isActive,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
    this.userName,
    this.clinicName,
    this.roleName,
  });

  factory StaffAssignment.fromJson(Map<String, dynamic> json) {
    return StaffAssignment(
      id: json['id'],
      userId: json['user_id'],
      clinicId: json['clinic_id'],
      roleId: json['role_id'],
      isPrimaryLocation: json['is_primary_location'],
      startDate: DateTime.parse(json['start_date']),
      endDate: json['end_date'] != null ? DateTime.parse(json['end_date']) : null,
      isActive: json['is_active'],
      notes: json['notes'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      userName: json['user_name'],
      clinicName: json['clinic_name'],
      roleName: json['role_name'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'clinic_id': clinicId,
      'role_id': roleId,
      'is_primary_location': isPrimaryLocation,
      'start_date': startDate.toIso8601String(),
      'end_date': endDate?.toIso8601String(),
      'is_active': isActive,
      'notes': notes,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'user_name': userName,
      'clinic_name': clinicName,
      'role_name': roleName,
    };
  }
}

/// Staff role with permissions
class StaffRole {
  final String id;
  final String name;
  final String? description;
  final List<String> permissions;
  final String? organizationId;
  final bool isSystem;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;

  StaffRole({
    required this.id,
    required this.name,
    this.description,
    required this.permissions,
    this.organizationId,
    required this.isSystem,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  factory StaffRole.fromJson(Map<String, dynamic> json) {
    return StaffRole(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      permissions: List<String>.from(json['permissions'] ?? []),
      organizationId: json['organization_id'],
      isSystem: json['is_system'],
      isActive: json['is_active'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'permissions': permissions,
      'organization_id': organizationId,
      'is_system': isSystem,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// Check if role has a specific permission
  bool hasPermission(String permission) {
    // Check for exact match
    if (permissions.contains(permission)) {
      return true;
    }

    // Check for wildcard (e.g., "appointments.*" matches "appointments.view")
    for (final perm in permissions) {
      if (perm == '*') {
        return true; // Global admin
      }
      if (perm.endsWith('.*')) {
        final prefix = perm.substring(0, perm.length - 2);
        if (permission.startsWith('$prefix.')) {
          return true;
        }
      }
    }

    return false;
  }
}
