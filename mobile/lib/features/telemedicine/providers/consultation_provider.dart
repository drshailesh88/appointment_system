import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/consultation.dart';
import '../../../core/providers/telemedicine_provider.dart';

/// Consultation list state
class ConsultationListState {
  final List<Consultation> consultations;
  final bool isLoading;
  final String? error;

  const ConsultationListState({
    this.consultations = const [],
    this.isLoading = false,
    this.error,
  });

  ConsultationListState copyWith({
    List<Consultation>? consultations,
    bool? isLoading,
    String? error,
  }) {
    return ConsultationListState(
      consultations: consultations ?? this.consultations,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Consultation list provider
class ConsultationListNotifier extends StateNotifier<ConsultationListState> {
  final TelemedicineNotifier _telemedicineNotifier;

  ConsultationListNotifier(this._telemedicineNotifier)
      : super(const ConsultationListState());

  /// Refresh consultations list (placeholder - implement with actual API)
  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      // TODO: Implement actual API call to fetch consultations list
      // For now, we'll just use the active consultation from telemedicine provider
      await Future.delayed(const Duration(milliseconds: 500));

      state = state.copyWith(
        consultations: [],
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Create consultation for appointment
  Future<Consultation?> createConsultation(String appointmentId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final consultation =
          await _telemedicineNotifier.createConsultation(appointmentId);

      if (consultation != null) {
        // Add to list
        final updatedList = [...state.consultations, consultation];
        state = state.copyWith(
          consultations: updatedList,
          isLoading: false,
        );
      } else {
        state = state.copyWith(
          isLoading: false,
          error: _telemedicineNotifier.state.error,
        );
      }

      return consultation;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return null;
    }
  }
}

/// Consultation list provider
final consultationListProvider =
    StateNotifierProvider<ConsultationListNotifier, ConsultationListState>((ref) {
  final telemedicineNotifier = ref.watch(telemedicineProvider.notifier);
  return ConsultationListNotifier(telemedicineNotifier);
});
