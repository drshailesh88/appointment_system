import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/staff_assignment.dart';
import '../../../core/services/staff_service.dart';

/// Staff state
class StaffState {
  final List<StaffRole> roles;
  final List<StaffAssignment> assignments;
  final List<Map<String, dynamic>> clinicStaff;
  final bool isLoading;
  final String? error;

  const StaffState({
    this.roles = const [],
    this.assignments = const [],
    this.clinicStaff = const [],
    this.isLoading = false,
    this.error,
  });

  StaffState copyWith({
    List<StaffRole>? roles,
    List<StaffAssignment>? assignments,
    List<Map<String, dynamic>>? clinicStaff,
    bool? isLoading,
    String? error,
  }) {
    return StaffState(
      roles: roles ?? this.roles,
      assignments: assignments ?? this.assignments,
      clinicStaff: clinicStaff ?? this.clinicStaff,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Staff notifier
class StaffNotifier extends StateNotifier<StaffState> {
  final StaffService _service;

  StaffNotifier(this._service) : super(const StaffState());

  /// Load all roles
  Future<void> loadRoles({String? organizationId}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final roles = await _service.getRoles(organizationId: organizationId);
      state = state.copyWith(
        roles: roles,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Create role
  Future<StaffRole?> createRole(Map<String, dynamic> data) async {
    try {
      final role = await _service.createRole(data);
      state = state.copyWith(
        roles: [...state.roles, role],
      );
      return role;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Update role
  Future<bool> updateRole(String roleId, Map<String, dynamic> data) async {
    try {
      final role = await _service.updateRole(roleId, data);

      final updatedRoles = state.roles.map((r) {
        return r.id == roleId ? role : r;
      }).toList();

      state = state.copyWith(roles: updatedRoles);
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Delete role
  Future<bool> deleteRole(String roleId) async {
    try {
      await _service.deleteRole(roleId);

      final updatedRoles = state.roles.where((r) => r.id != roleId).toList();
      state = state.copyWith(roles: updatedRoles);

      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Load assignments
  Future<void> loadAssignments({
    String? userId,
    String? clinicId,
    String? roleId,
    bool activeOnly = true,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final assignments = await _service.getAssignments(
        userId: userId,
        clinicId: clinicId,
        roleId: roleId,
        activeOnly: activeOnly,
      );

      state = state.copyWith(
        assignments: assignments,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Create assignment
  Future<StaffAssignment?> createAssignment(Map<String, dynamic> data) async {
    try {
      final assignment = await _service.createAssignment(data);
      state = state.copyWith(
        assignments: [...state.assignments, assignment],
      );
      return assignment;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Update assignment
  Future<bool> updateAssignment(
    String assignmentId,
    Map<String, dynamic> data,
  ) async {
    try {
      final assignment = await _service.updateAssignment(assignmentId, data);

      final updatedAssignments = state.assignments.map((a) {
        return a.id == assignmentId ? assignment : a;
      }).toList();

      state = state.copyWith(assignments: updatedAssignments);
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Delete assignment
  Future<bool> deleteAssignment(String assignmentId) async {
    try {
      await _service.deleteAssignment(assignmentId);

      final updatedAssignments = state.assignments
          .where((a) => a.id != assignmentId)
          .toList();

      state = state.copyWith(assignments: updatedAssignments);
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Load clinic staff
  Future<void> loadClinicStaff(String clinicId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final staff = await _service.getClinicStaff(clinicId);
      state = state.copyWith(
        clinicStaff: staff,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Get staff performance
  Future<Map<String, dynamic>?> getStaffPerformance(
    String userId, {
    String? startDate,
    String? endDate,
    String? clinicId,
  }) async {
    try {
      return await _service.getStaffPerformance(
        userId,
        startDate: startDate,
        endDate: endDate,
        clinicId: clinicId,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }
}

/// Provider
final staffProvider = StateNotifierProvider<StaffNotifier, StaffState>((ref) {
  final service = ref.watch(staffServiceProvider);
  return StaffNotifier(service);
});
