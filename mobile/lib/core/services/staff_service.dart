import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/staff_assignment.dart';
import '../models/user.dart';

/// Service for managing staff roles and assignments
class StaffService {
  final ApiClient _apiClient;

  StaffService(this._apiClient);

  /// Get all staff roles
  Future<List<StaffRole>> getRoles({String? organizationId}) async {
    final response = await _apiClient.get(
      '/api/v1/staff/roles',
      queryParameters: {
        if (organizationId != null) 'organization_id': organizationId,
      },
    );
    return (response as List).map((json) => StaffRole.fromJson(json)).toList();
  }

  /// Get role by ID
  Future<StaffRole> getRole(String roleId) async {
    final response = await _apiClient.get('/api/v1/staff/roles/$roleId');
    return StaffRole.fromJson(response);
  }

  /// Create role
  Future<StaffRole> createRole(Map<String, dynamic> data) async {
    final response = await _apiClient.post('/api/v1/staff/roles', data);
    return StaffRole.fromJson(response);
  }

  /// Update role
  Future<StaffRole> updateRole(String roleId, Map<String, dynamic> data) async {
    final response = await _apiClient.put('/api/v1/staff/roles/$roleId', data);
    return StaffRole.fromJson(response);
  }

  /// Delete role
  Future<void> deleteRole(String roleId) async {
    await _apiClient.delete('/api/v1/staff/roles/$roleId');
  }

  /// Get staff assignments
  Future<List<StaffAssignment>> getAssignments({
    String? userId,
    String? clinicId,
    String? roleId,
    bool activeOnly = true,
  }) async {
    final response = await _apiClient.get(
      '/api/v1/staff/assignments',
      queryParameters: {
        if (userId != null) 'user_id': userId,
        if (clinicId != null) 'clinic_id': clinicId,
        if (roleId != null) 'role_id': roleId,
        'active_only': activeOnly,
      },
    );
    return (response as List)
        .map((json) => StaffAssignment.fromJson(json))
        .toList();
  }

  /// Get assignment by ID
  Future<StaffAssignment> getAssignment(String assignmentId) async {
    final response =
        await _apiClient.get('/api/v1/staff/assignments/$assignmentId');
    return StaffAssignment.fromJson(response);
  }

  /// Create staff assignment
  Future<StaffAssignment> createAssignment(Map<String, dynamic> data) async {
    final response = await _apiClient.post('/api/v1/staff/assignments', data);
    return StaffAssignment.fromJson(response);
  }

  /// Update staff assignment
  Future<StaffAssignment> updateAssignment(
    String assignmentId,
    Map<String, dynamic> data,
  ) async {
    final response = await _apiClient.put(
      '/api/v1/staff/assignments/$assignmentId',
      data,
    );
    return StaffAssignment.fromJson(response);
  }

  /// Delete staff assignment
  Future<void> deleteAssignment(String assignmentId) async {
    await _apiClient.delete('/api/v1/staff/assignments/$assignmentId');
  }

  /// Get staff members for a clinic
  Future<List<Map<String, dynamic>>> getClinicStaff(String clinicId) async {
    final assignments = await getAssignments(clinicId: clinicId);

    // Get unique user IDs
    final userIds = assignments.map((a) => a.userId).toSet();

    // Fetch user details (this would need a users API endpoint)
    final staffMembers = <Map<String, dynamic>>[];
    for (final userId in userIds) {
      try {
        final user = await _apiClient.get('/api/v1/users/$userId');
        final userAssignments = assignments.where((a) => a.userId == userId).toList();
        staffMembers.add({
          'user': user,
          'assignments': userAssignments.map((a) => a.toJson()).toList(),
        });
      } catch (e) {
        // Skip users that can't be fetched
        continue;
      }
    }

    return staffMembers;
  }

  /// Get all permissions available in the system
  Future<List<String>> getAvailablePermissions() async {
    final response = await _apiClient.get('/api/v1/staff/permissions');
    return List<String>.from(response);
  }

  /// Get staff performance metrics
  Future<Map<String, dynamic>> getStaffPerformance(
    String userId, {
    String? startDate,
    String? endDate,
    String? clinicId,
  }) async {
    final response = await _apiClient.get(
      '/api/v1/staff/$userId/performance',
      queryParameters: {
        if (startDate != null) 'start_date': startDate,
        if (endDate != null) 'end_date': endDate,
        if (clinicId != null) 'clinic_id': clinicId,
      },
    );
    return response;
  }
}

/// Provider for StaffService
final staffServiceProvider = Provider<StaffService>((ref) {
  // TODO: Inject ApiClient properly
  final apiClient = ApiClient();
  return StaffService(apiClient);
});
