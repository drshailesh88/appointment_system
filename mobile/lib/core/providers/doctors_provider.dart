import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/doctor.dart';
import '../repositories/doctor_repository.dart';
import 'sync_provider.dart';

/// Doctors state
class DoctorsState {
  final List<Doctor> doctors;
  final Doctor? selectedDoctor;
  final Map<String, dynamic>? schedule;
  final List<Map<String, dynamic>> availableSlots;
  final bool isLoading;
  final String? error;

  const DoctorsState({
    this.doctors = const [],
    this.selectedDoctor,
    this.schedule,
    this.availableSlots = const [],
    this.isLoading = false,
    this.error,
  });

  DoctorsState copyWith({
    List<Doctor>? doctors,
    Doctor? selectedDoctor,
    Map<String, dynamic>? schedule,
    List<Map<String, dynamic>>? availableSlots,
    bool? isLoading,
    String? error,
  }) {
    return DoctorsState(
      doctors: doctors ?? this.doctors,
      selectedDoctor: selectedDoctor ?? this.selectedDoctor,
      schedule: schedule ?? this.schedule,
      availableSlots: availableSlots ?? this.availableSlots,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Doctors notifier
class DoctorsNotifier extends StateNotifier<DoctorsState> {
  final DoctorRepository _repository;

  DoctorsNotifier(this._repository) : super(const DoctorsState());

  Future<void> loadDoctors({
    String? clinicId,
    String? specialization,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final doctors = await _repository.getDoctors(
        clinicId: clinicId,
        specialization: specialization,
      );

      state = state.copyWith(
        doctors: doctors,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadDoctor(String doctorId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final doctor = await _repository.getDoctor(doctorId);

      state = state.copyWith(
        selectedDoctor: doctor,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadDoctorSchedule(String doctorId, {String? date}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final schedule = await _repository.getDoctorSchedule(doctorId, date: date);

      state = state.copyWith(
        schedule: schedule,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadAvailableSlots(
    String doctorId,
    String date, {
    int durationMinutes = 15,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final data = await _repository.getAvailableSlots(
        doctorId: doctorId,
        date: date,
        durationMinutes: durationMinutes,
      );

      final slots = List<Map<String, dynamic>>.from(data['slots'] ?? []);

      state = state.copyWith(
        availableSlots: slots,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  void selectDoctor(Doctor doctor) {
    state = state.copyWith(selectedDoctor: doctor);
  }

  void clearSelection() {
    state = state.copyWith(
      selectedDoctor: null,
      schedule: null,
      availableSlots: [],
    );
  }
}

/// Provider
final doctorsProvider =
    StateNotifierProvider<DoctorsNotifier, DoctorsState>((ref) {
  final repository = ref.watch(doctorRepositoryProvider);
  return DoctorsNotifier(repository);
});
