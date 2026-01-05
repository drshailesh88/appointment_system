import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/noshow_prediction.dart';
import '../services/noshow_service.dart';

/// No-show prediction state
class NoShowState {
  final Map<String, NoShowPrediction> predictions;
  final List<HighRiskAppointment> highRiskAppointments;
  final ModelStats? modelStats;
  final bool isLoading;
  final bool isLoadingHighRisk;
  final bool isLoadingStats;
  final String? error;

  const NoShowState({
    this.predictions = const {},
    this.highRiskAppointments = const [],
    this.modelStats,
    this.isLoading = false,
    this.isLoadingHighRisk = false,
    this.isLoadingStats = false,
    this.error,
  });

  NoShowState copyWith({
    Map<String, NoShowPrediction>? predictions,
    List<HighRiskAppointment>? highRiskAppointments,
    ModelStats? modelStats,
    bool? isLoading,
    bool? isLoadingHighRisk,
    bool? isLoadingStats,
    String? error,
  }) {
    return NoShowState(
      predictions: predictions ?? this.predictions,
      highRiskAppointments: highRiskAppointments ?? this.highRiskAppointments,
      modelStats: modelStats ?? this.modelStats,
      isLoading: isLoading ?? this.isLoading,
      isLoadingHighRisk: isLoadingHighRisk ?? this.isLoadingHighRisk,
      isLoadingStats: isLoadingStats ?? this.isLoadingStats,
      error: error,
    );
  }

  /// Get prediction for a specific appointment
  NoShowPrediction? getPrediction(String appointmentId) {
    return predictions[appointmentId];
  }

  /// Check if appointment is high-risk
  bool isHighRisk(String appointmentId) {
    final prediction = predictions[appointmentId];
    return prediction?.isHighRisk ?? false;
  }

  /// Check if appointment is medium-risk
  bool isMediumRisk(String appointmentId) {
    final prediction = predictions[appointmentId];
    return prediction?.isMediumRisk ?? false;
  }

  /// Check if appointment is low-risk
  bool isLowRisk(String appointmentId) {
    final prediction = predictions[appointmentId];
    return prediction?.isLowRisk ?? false;
  }

  /// Get total number of high-risk appointments
  int get highRiskCount => highRiskAppointments.length;

  /// Check if prediction exists for appointment
  bool hasPrediction(String appointmentId) {
    return predictions.containsKey(appointmentId);
  }
}

/// No-show prediction notifier
class NoShowNotifier extends StateNotifier<NoShowState> {
  final NoShowService _noShowService;

  NoShowNotifier(this._noShowService) : super(const NoShowState());

  /// Predict no-show for a single appointment
  ///
  /// [appointmentId] - Appointment UUID
  /// [force] - Force new prediction even if cached
  Future<NoShowPrediction?> predictNoShow(
    String appointmentId, {
    bool force = false,
  }) async {
    // Return cached prediction if available and not forcing
    if (!force && state.predictions.containsKey(appointmentId)) {
      return state.predictions[appointmentId];
    }

    state = state.copyWith(isLoading: true, error: null);

    try {
      final prediction = await _noShowService.predictNoShow(appointmentId);

      if (prediction != null) {
        // Update predictions map
        final updatedPredictions = Map<String, NoShowPrediction>.from(state.predictions);
        updatedPredictions[appointmentId] = prediction;

        state = state.copyWith(
          predictions: updatedPredictions,
          isLoading: false,
        );

        return prediction;
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Failed to get prediction',
        );
        return null;
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return null;
    }
  }

  /// Predict no-show for multiple appointments
  ///
  /// [appointmentIds] - List of appointment UUIDs
  Future<void> batchPredict(List<String> appointmentIds) async {
    if (appointmentIds.isEmpty) return;

    state = state.copyWith(isLoading: true, error: null);

    try {
      final predictions = await _noShowService.batchPredict(appointmentIds);

      // Update predictions map
      final updatedPredictions = Map<String, NoShowPrediction>.from(state.predictions);
      for (final prediction in predictions) {
        updatedPredictions[prediction.appointmentId] = prediction;
      }

      state = state.copyWith(
        predictions: updatedPredictions,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Load high-risk appointments
  ///
  /// [startDate] - Start of date range
  /// [endDate] - End of date range
  Future<void> loadHighRiskAppointments({
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    state = state.copyWith(isLoadingHighRisk: true, error: null);

    try {
      final appointments = await _noShowService.getHighRiskAppointments(
        startDate: startDate,
        endDate: endDate,
      );

      state = state.copyWith(
        highRiskAppointments: appointments,
        isLoadingHighRisk: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingHighRisk: false,
        error: e.toString(),
      );
    }
  }

  /// Load model statistics
  Future<void> loadModelStats() async {
    state = state.copyWith(isLoadingStats: true, error: null);

    try {
      final stats = await _noShowService.getModelStats();

      state = state.copyWith(
        modelStats: stats,
        isLoadingStats: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingStats: false,
        error: e.toString(),
      );
    }
  }

  /// Submit feedback for an appointment outcome
  ///
  /// [appointmentId] - Appointment UUID
  /// [actualStatus] - Actual outcome: 'completed', 'no_show', or 'cancelled'
  Future<bool> submitFeedback({
    required String appointmentId,
    required String actualStatus,
  }) async {
    try {
      final success = await _noShowService.submitFeedback(
        appointmentId: appointmentId,
        actualStatus: actualStatus,
      );

      if (success) {
        // Reload prediction to get updated accuracy
        await predictNoShow(appointmentId, force: true);
      }

      return success;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Trigger model retraining (admin only)
  ///
  /// [minSamples] - Minimum samples needed for training
  Future<Map<String, dynamic>?> retrainModel({int minSamples = 100}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final result = await _noShowService.retrainModel(
        minSamples: minSamples,
      );

      state = state.copyWith(isLoading: false);

      // Reload stats if training successful
      if (result?['success'] == true) {
        await loadModelStats();
      }

      return result;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return null;
    }
  }

  /// Clear cached prediction for an appointment
  void clearPrediction(String appointmentId) {
    final updatedPredictions = Map<String, NoShowPrediction>.from(state.predictions);
    updatedPredictions.remove(appointmentId);

    state = state.copyWith(predictions: updatedPredictions);
  }

  /// Clear all cached predictions
  void clearAllPredictions() {
    state = state.copyWith(predictions: {});
  }

  /// Clear error message
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Refresh high-risk appointments
  Future<void> refreshHighRisk() async {
    await loadHighRiskAppointments();
  }
}

/// Provider for NoShowService
final noShowServiceProvider = Provider<NoShowService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return NoShowService(apiClient);
});

/// Provider for NoShowNotifier and NoShowState
final noShowProvider = StateNotifierProvider<NoShowNotifier, NoShowState>((ref) {
  final noShowService = ref.watch(noShowServiceProvider);
  return NoShowNotifier(noShowService);
});

/// Provider for getting prediction for a specific appointment
final appointmentPredictionProvider =
    Provider.family<NoShowPrediction?, String>((ref, appointmentId) {
  final state = ref.watch(noShowProvider);
  return state.getPrediction(appointmentId);
});

/// Provider for checking if appointment is high-risk
final isHighRiskProvider = Provider.family<bool, String>((ref, appointmentId) {
  final state = ref.watch(noShowProvider);
  return state.isHighRisk(appointmentId);
});

/// Provider for high-risk appointments count
final highRiskCountProvider = Provider<int>((ref) {
  final state = ref.watch(noShowProvider);
  return state.highRiskCount;
});

/// Provider for auto-loading prediction when needed
///
/// Call this provider with an appointment ID to trigger prediction if not cached
final autoPredict = FutureProvider.family<NoShowPrediction?, String>(
  (ref, appointmentId) async {
    final notifier = ref.watch(noShowProvider.notifier);
    return await notifier.predictNoShow(appointmentId);
  },
);
