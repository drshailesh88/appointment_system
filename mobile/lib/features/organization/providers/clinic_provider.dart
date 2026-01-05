import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/models/clinic.dart';
import '../../../core/services/organization_service.dart';
import 'organization_provider.dart';

/// Clinic state
class ClinicState {
  final List<Clinic> clinics;
  final Clinic? selectedClinic;
  final bool isLoading;
  final String? error;

  const ClinicState({
    this.clinics = const [],
    this.selectedClinic,
    this.isLoading = false,
    this.error,
  });

  ClinicState copyWith({
    List<Clinic>? clinics,
    Clinic? selectedClinic,
    bool? isLoading,
    String? error,
  }) {
    return ClinicState(
      clinics: clinics ?? this.clinics,
      selectedClinic: selectedClinic ?? this.selectedClinic,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Clinic notifier
class ClinicNotifier extends StateNotifier<ClinicState> {
  final OrganizationService _service;
  final Ref _ref;

  ClinicNotifier(this._service, this._ref) : super(const ClinicState());

  /// Load clinics for current organization
  Future<void> loadClinics() async {
    final orgState = _ref.read(organizationProvider);
    if (orgState.selectedOrganization == null) {
      state = state.copyWith(
        clinics: [],
        error: 'No organization selected',
      );
      return;
    }

    state = state.copyWith(isLoading: true, error: null);

    try {
      final clinics = await _service.getClinics(
        orgState.selectedOrganization!.id,
      );

      state = state.copyWith(
        clinics: clinics,
        isLoading: false,
      );

      // Auto-select first clinic if none selected
      if (state.selectedClinic == null && clinics.isNotEmpty) {
        state = state.copyWith(selectedClinic: clinics.first);
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Select a clinic
  void selectClinic(Clinic clinic) {
    state = state.copyWith(selectedClinic: clinic);
  }

  /// Get clinic by ID
  Future<Clinic?> getClinic(String clinicId) async {
    final orgState = _ref.read(organizationProvider);
    if (orgState.selectedOrganization == null) return null;

    try {
      final clinic = await _service.getClinic(
        orgState.selectedOrganization!.id,
        clinicId,
      );

      // Update in list if present
      final updatedClinics = state.clinics.map((c) {
        return c.id == clinicId ? clinic : c;
      }).toList();

      state = state.copyWith(clinics: updatedClinics);

      return clinic;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Create clinic
  Future<Clinic?> createClinic(Map<String, dynamic> data) async {
    final orgState = _ref.read(organizationProvider);
    if (orgState.selectedOrganization == null) return null;

    try {
      final clinic = await _service.createClinic(
        orgState.selectedOrganization!.id,
        data,
      );

      state = state.copyWith(
        clinics: [...state.clinics, clinic],
      );

      return clinic;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Update clinic
  Future<bool> updateClinic(
    String clinicId,
    Map<String, dynamic> data,
  ) async {
    final orgState = _ref.read(organizationProvider);
    if (orgState.selectedOrganization == null) return false;

    try {
      final clinic = await _service.updateClinic(
        orgState.selectedOrganization!.id,
        clinicId,
        data,
      );

      final updatedClinics = state.clinics.map((c) {
        return c.id == clinicId ? clinic : c;
      }).toList();

      state = state.copyWith(
        clinics: updatedClinics,
        selectedClinic: state.selectedClinic?.id == clinicId
            ? clinic
            : state.selectedClinic,
      );

      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Delete clinic
  Future<bool> deleteClinic(String clinicId) async {
    final orgState = _ref.read(organizationProvider);
    if (orgState.selectedOrganization == null) return false;

    try {
      await _service.deleteClinic(
        orgState.selectedOrganization!.id,
        clinicId,
      );

      final updatedClinics = state.clinics
          .where((c) => c.id != clinicId)
          .toList();

      state = state.copyWith(
        clinics: updatedClinics,
        selectedClinic: state.selectedClinic?.id == clinicId
            ? null
            : state.selectedClinic,
      );

      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }
}

/// Provider
final clinicProvider =
    StateNotifierProvider<ClinicNotifier, ClinicState>((ref) {
  final service = ref.watch(organizationServiceProvider);
  return ClinicNotifier(service, ref);
});
