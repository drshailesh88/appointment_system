import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/appointment.dart';
import '../repositories/appointment_repository.dart';
import 'sync_provider.dart';

/// Appointments state
class AppointmentsState {
  final List<Appointment> appointments;
  final List<Appointment> todayAppointments;
  final bool isLoading;
  final String? error;

  const AppointmentsState({
    this.appointments = const [],
    this.todayAppointments = const [],
    this.isLoading = false,
    this.error,
  });

  AppointmentsState copyWith({
    List<Appointment>? appointments,
    List<Appointment>? todayAppointments,
    bool? isLoading,
    String? error,
  }) {
    return AppointmentsState(
      appointments: appointments ?? this.appointments,
      todayAppointments: todayAppointments ?? this.todayAppointments,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }

  // Stats
  int get scheduledCount =>
      todayAppointments.where((a) => a.status == 'scheduled').length;
  int get checkedInCount =>
      todayAppointments.where((a) => a.status == 'checked_in').length;
  int get completedCount =>
      todayAppointments.where((a) => a.status == 'completed').length;
  int get cancelledCount =>
      todayAppointments.where((a) => a.status == 'cancelled').length;
}

/// Appointments notifier
class AppointmentsNotifier extends StateNotifier<AppointmentsState> {
  final AppointmentRepository _repository;
  final SyncNotifier _syncNotifier;

  AppointmentsNotifier(this._repository, this._syncNotifier)
      : super(const AppointmentsState());

  Future<void> loadTodayAppointments({String? doctorId}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final appointments =
          await _repository.getTodayAppointments(doctorId: doctorId);

      state = state.copyWith(
        todayAppointments: appointments,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadAppointments({
    String? doctorId,
    String? patientId,
    String? dateFrom,
    String? dateTo,
    String? status,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final appointments = await _repository.getAppointments(
        doctorId: doctorId,
        patientId: patientId,
        dateFrom: dateFrom,
        dateTo: dateTo,
        status: status,
      );

      state = state.copyWith(
        appointments: appointments,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<Appointment?> createAppointment(Map<String, dynamic> data) async {
    try {
      final appointment = await _repository.createAppointment(data);
      _syncNotifier.updatePendingCount();

      // Refresh lists
      await loadTodayAppointments();

      return appointment;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  Future<bool> checkInPatient(String appointmentId, {int? tokenNumber}) async {
    try {
      await _repository.checkInPatient(appointmentId, tokenNumber: tokenNumber);
      _syncNotifier.updatePendingCount();
      await loadTodayAppointments();
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  int get pendingSyncCount => _repository.getPendingSyncCount();
}

/// Provider
final appointmentsProvider =
    StateNotifierProvider<AppointmentsNotifier, AppointmentsState>((ref) {
  final repository = ref.watch(appointmentRepositoryProvider);
  final syncNotifier = ref.watch(syncProvider.notifier);
  return AppointmentsNotifier(repository, syncNotifier);
});
