import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/appointment.dart';
import '../repositories/appointment_repository.dart';
import '../services/websocket_service.dart';
import 'sync_provider.dart';
import 'realtime_provider.dart';

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
  final Ref _ref;

  AppointmentsNotifier(this._repository, this._syncNotifier, this._ref)
      : super(const AppointmentsState()) {
    _listenToRealtimeUpdates();
  }

  /// Listen to real-time WebSocket events
  void _listenToRealtimeUpdates() {
    _ref.listen<AsyncValue<WebSocketEvent>>(
      appointmentEventsProvider,
      (previous, next) {
        next.whenData((event) {
          _handleRealtimeEvent(event);
        });
      },
    );
  }

  /// Handle real-time appointment events
  void _handleRealtimeEvent(WebSocketEvent event) {
    switch (event.type) {
      case WebSocketEventType.appointmentCreated:
      case WebSocketEventType.appointmentUpdated:
        _mergeAppointmentUpdate(event.data);
        break;

      case WebSocketEventType.appointmentCancelled:
        _removeAppointment(event.data['id'] as String?);
        break;

      default:
        break;
    }
  }

  /// Merge real-time appointment update into state
  void _mergeAppointmentUpdate(Map<String, dynamic> data) {
    try {
      final updatedAppointment = Appointment.fromJson(data);

      // Update in today's appointments if present
      final todayIndex = state.todayAppointments.indexWhere(
        (a) => a.id == updatedAppointment.id,
      );
      if (todayIndex != -1) {
        final updatedToday = List<Appointment>.from(state.todayAppointments);
        updatedToday[todayIndex] = updatedAppointment;
        state = state.copyWith(todayAppointments: updatedToday);
      } else {
        // Check if it's a today appointment that needs to be added
        final today = DateTime.now();
        final appointmentDate = updatedAppointment.scheduledStart;
        if (appointmentDate.year == today.year &&
            appointmentDate.month == today.month &&
            appointmentDate.day == today.day) {
          final updatedToday = [...state.todayAppointments, updatedAppointment];
          state = state.copyWith(todayAppointments: updatedToday);
        }
      }

      // Update in general appointments list if present
      final allIndex = state.appointments.indexWhere(
        (a) => a.id == updatedAppointment.id,
      );
      if (allIndex != -1) {
        final updatedAll = List<Appointment>.from(state.appointments);
        updatedAll[allIndex] = updatedAppointment;
        state = state.copyWith(appointments: updatedAll);
      }
    } catch (e) {
      // Silently handle parse errors - just refresh
      loadTodayAppointments();
    }
  }

  /// Remove appointment from state
  void _removeAppointment(String? appointmentId) {
    if (appointmentId == null) return;

    final updatedToday = state.todayAppointments
        .where((a) => a.id != appointmentId)
        .toList();
    final updatedAll = state.appointments
        .where((a) => a.id != appointmentId)
        .toList();

    state = state.copyWith(
      todayAppointments: updatedToday,
      appointments: updatedAll,
    );
  }

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
  return AppointmentsNotifier(repository, syncNotifier, ref);
});
