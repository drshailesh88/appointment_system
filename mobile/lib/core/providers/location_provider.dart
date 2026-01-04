import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/organization.dart';
import '../models/staff_assignment.dart';
import '../api/api_client.dart';

/// Provider for managing user's location/clinic selection
///
/// Handles:
/// - User's assignments across multiple locations
/// - Current selected clinic
/// - Organization information
/// - Location switching
class LocationState {
  final List<StaffAssignment> assignments;
  final StaffAssignment? currentAssignment;
  final Organization? organization;
  final bool isLoading;
  final String? error;

  LocationState({
    this.assignments = const [],
    this.currentAssignment,
    this.organization,
    this.isLoading = false,
    this.error,
  });

  LocationState copyWith({
    List<StaffAssignment>? assignments,
    StaffAssignment? currentAssignment,
    Organization? organization,
    bool? isLoading,
    String? error,
  }) {
    return LocationState(
      assignments: assignments ?? this.assignments,
      currentAssignment: currentAssignment ?? this.currentAssignment,
      organization: organization ?? this.organization,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }

  /// Get the current clinic ID
  String? get currentClinicId => currentAssignment?.clinicId;

  /// Get the current clinic name
  String? get currentClinicName => currentAssignment?.clinicName;

  /// Check if user has access to multiple locations
  bool get hasMultipleLocations => assignments.length > 1;

  /// Get primary assignment
  StaffAssignment? get primaryAssignment {
    try {
      return assignments.firstWhere((a) => a.isPrimaryLocation);
    } catch (e) {
      return assignments.isNotEmpty ? assignments.first : null;
    }
  }
}

class LocationNotifier extends StateNotifier<LocationState> {
  final ApiClient _apiClient;
  final SharedPreferences _prefs;

  LocationNotifier(this._apiClient, this._prefs) : super(LocationState()) {
    _loadSavedLocation();
  }

  static const _selectedClinicKey = 'selected_clinic_id';

  /// Load user's assignments
  Future<void> loadAssignments(String userId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _apiClient.get('/api/v1/staff/users/$userId/assignments');

      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        final assignments = data.map((json) => StaffAssignment.fromJson(json)).toList();

        // Try to restore saved clinic selection
        final savedClinicId = _prefs.getString(_selectedClinicKey);
        StaffAssignment? current;

        if (savedClinicId != null) {
          try {
            current = assignments.firstWhere((a) => a.clinicId == savedClinicId);
          } catch (e) {
            // Saved clinic not found, use primary
            current = _getPrimaryOrFirst(assignments);
          }
        } else {
          current = _getPrimaryOrFirst(assignments);
        }

        state = state.copyWith(
          assignments: assignments,
          currentAssignment: current,
          isLoading: false,
        );

        // Load organization if available
        if (current != null) {
          await _loadOrganization(current.clinicId);
        }
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Failed to load assignments',
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Switch to a different location
  Future<void> switchLocation(StaffAssignment assignment) async {
    state = state.copyWith(currentAssignment: assignment);

    // Save selection
    await _prefs.setString(_selectedClinicKey, assignment.clinicId);

    // Load organization for new location
    await _loadOrganization(assignment.clinicId);
  }

  /// Load saved location preference
  Future<void> _loadSavedLocation() async {
    final savedClinicId = _prefs.getString(_selectedClinicKey);
    if (savedClinicId != null && state.assignments.isNotEmpty) {
      try {
        final assignment = state.assignments.firstWhere(
          (a) => a.clinicId == savedClinicId,
        );
        state = state.copyWith(currentAssignment: assignment);
      } catch (e) {
        // Saved clinic not found, keep current
      }
    }
  }

  /// Load organization information
  Future<void> _loadOrganization(String clinicId) async {
    try {
      // Get clinic details first
      final clinicResponse = await _apiClient.get('/api/v1/clinics/$clinicId');

      if (clinicResponse.statusCode == 200) {
        final clinicData = clinicResponse.data;
        final orgId = clinicData['organization_id'];

        if (orgId != null) {
          final orgResponse = await _apiClient.get('/api/v1/organizations/$orgId');

          if (orgResponse.statusCode == 200) {
            final org = Organization.fromJson(orgResponse.data);
            state = state.copyWith(organization: org);
          }
        }
      }
    } catch (e) {
      // Organization loading failed, but don't block location switch
      print('Failed to load organization: $e');
    }
  }

  /// Get primary assignment or first available
  StaffAssignment? _getPrimaryOrFirst(List<StaffAssignment> assignments) {
    if (assignments.isEmpty) return null;

    try {
      return assignments.firstWhere((a) => a.isPrimaryLocation);
    } catch (e) {
      return assignments.first;
    }
  }

  /// Clear location data (on logout)
  Future<void> clear() async {
    await _prefs.remove(_selectedClinicKey);
    state = LocationState();
  }
}

/// Provider for location management
final locationProvider = StateNotifierProvider<LocationNotifier, LocationState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  return LocationNotifier(apiClient, prefs);
});

/// Provider for current clinic ID (convenience)
final currentClinicIdProvider = Provider<String?>((ref) {
  return ref.watch(locationProvider).currentClinicId;
});

/// Provider for checking if user has multiple locations
final hasMultipleLocationsProvider = Provider<bool>((ref) {
  return ref.watch(locationProvider).hasMultipleLocations;
});

// Note: These providers (apiClientProvider, sharedPreferencesProvider) should be
// defined in your existing provider setup. This is a reference implementation.
