import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/patient.dart';
import '../repositories/patient_repository.dart';
import 'sync_provider.dart';

/// Patients state
class PatientsState {
  final List<Patient> patients;
  final List<Patient> searchResults;
  final Patient? selectedPatient;
  final bool isLoading;
  final bool isSearching;
  final String? error;

  const PatientsState({
    this.patients = const [],
    this.searchResults = const [],
    this.selectedPatient,
    this.isLoading = false,
    this.isSearching = false,
    this.error,
  });

  PatientsState copyWith({
    List<Patient>? patients,
    List<Patient>? searchResults,
    Patient? selectedPatient,
    bool? isLoading,
    bool? isSearching,
    String? error,
  }) {
    return PatientsState(
      patients: patients ?? this.patients,
      searchResults: searchResults ?? this.searchResults,
      selectedPatient: selectedPatient ?? this.selectedPatient,
      isLoading: isLoading ?? this.isLoading,
      isSearching: isSearching ?? this.isSearching,
      error: error,
    );
  }
}

/// Patients notifier
class PatientsNotifier extends StateNotifier<PatientsState> {
  final PatientRepository _repository;
  final SyncNotifier _syncNotifier;

  PatientsNotifier(this._repository, this._syncNotifier)
      : super(const PatientsState());

  Future<void> searchPatients(String query, {String? clinicId}) async {
    if (query.length < 2) {
      state = state.copyWith(searchResults: []);
      return;
    }

    state = state.copyWith(isSearching: true, error: null);

    try {
      final patients = await _repository.searchPatients(
        query: query,
        clinicId: clinicId,
      );

      state = state.copyWith(
        searchResults: patients,
        isSearching: false,
      );
    } catch (e) {
      state = state.copyWith(
        isSearching: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadPatient(String patientId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final patient = await _repository.getPatient(patientId);

      state = state.copyWith(
        selectedPatient: patient,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<Patient?> createPatient(Map<String, dynamic> data) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final patient = await _repository.createPatient(data);
      _syncNotifier.updatePendingCount();

      state = state.copyWith(isLoading: false);
      return patient;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return null;
    }
  }

  void clearSearch() {
    state = state.copyWith(searchResults: []);
  }

  void clearSelectedPatient() {
    state = state.copyWith(selectedPatient: null);
  }
}

/// Provider
final patientsProvider =
    StateNotifierProvider<PatientsNotifier, PatientsState>((ref) {
  final repository = ref.watch(patientRepositoryProvider);
  final syncNotifier = ref.watch(syncProvider.notifier);
  return PatientsNotifier(repository, syncNotifier);
});
