import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/organization.dart';
import '../../../core/services/organization_service.dart';

/// Organization state
class OrganizationState {
  final List<Organization> organizations;
  final Organization? selectedOrganization;
  final bool isLoading;
  final String? error;

  const OrganizationState({
    this.organizations = const [],
    this.selectedOrganization,
    this.isLoading = false,
    this.error,
  });

  OrganizationState copyWith({
    List<Organization>? organizations,
    Organization? selectedOrganization,
    bool? isLoading,
    String? error,
  }) {
    return OrganizationState(
      organizations: organizations ?? this.organizations,
      selectedOrganization: selectedOrganization ?? this.selectedOrganization,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Organization notifier
class OrganizationNotifier extends StateNotifier<OrganizationState> {
  final OrganizationService _service;

  OrganizationNotifier(this._service) : super(const OrganizationState());

  /// Load all organizations
  Future<void> loadOrganizations() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final organizations = await _service.getOrganizations();
      state = state.copyWith(
        organizations: organizations,
        isLoading: false,
      );

      // Auto-select first organization if none selected
      if (state.selectedOrganization == null && organizations.isNotEmpty) {
        state = state.copyWith(selectedOrganization: organizations.first);
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Select an organization
  void selectOrganization(Organization organization) {
    state = state.copyWith(selectedOrganization: organization);
  }

  /// Get organization by ID
  Future<Organization?> getOrganization(String organizationId) async {
    try {
      final organization = await _service.getOrganization(organizationId);

      // Update in list if present
      final updatedOrgs = state.organizations.map((org) {
        return org.id == organizationId ? organization : org;
      }).toList();

      state = state.copyWith(organizations: updatedOrgs);

      return organization;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Create organization
  Future<Organization?> createOrganization(Map<String, dynamic> data) async {
    try {
      final organization = await _service.createOrganization(data);

      state = state.copyWith(
        organizations: [...state.organizations, organization],
      );

      return organization;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Update organization
  Future<bool> updateOrganization(
    String organizationId,
    Map<String, dynamic> data,
  ) async {
    try {
      final organization = await _service.updateOrganization(organizationId, data);

      final updatedOrgs = state.organizations.map((org) {
        return org.id == organizationId ? organization : org;
      }).toList();

      state = state.copyWith(
        organizations: updatedOrgs,
        selectedOrganization: state.selectedOrganization?.id == organizationId
            ? organization
            : state.selectedOrganization,
      );

      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Delete organization
  Future<bool> deleteOrganization(String organizationId) async {
    try {
      await _service.deleteOrganization(organizationId);

      final updatedOrgs = state.organizations
          .where((org) => org.id != organizationId)
          .toList();

      state = state.copyWith(
        organizations: updatedOrgs,
        selectedOrganization: state.selectedOrganization?.id == organizationId
            ? null
            : state.selectedOrganization,
      );

      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Get consolidated analytics
  Future<Map<String, dynamic>?> getConsolidatedAnalytics({
    String? startDate,
    String? endDate,
  }) async {
    if (state.selectedOrganization == null) return null;

    try {
      return await _service.getConsolidatedAnalytics(
        state.selectedOrganization!.id,
        startDate: startDate,
        endDate: endDate,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }
}

/// Provider
final organizationProvider =
    StateNotifierProvider<OrganizationNotifier, OrganizationState>((ref) {
  final service = ref.watch(organizationServiceProvider);
  return OrganizationNotifier(service);
});
