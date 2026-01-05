import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../services/smart_scheduling_service.dart';

// Provider for SmartSchedulingService
final smartSchedulingServiceProvider = Provider<SmartSchedulingService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SmartSchedulingService(apiClient);
});

// State for smart scheduling
class SmartSchedulingState {
  final bool isLoading;
  final String? error;
  final List<SlotSuggestion> suggestions;
  final List<OptimalWindow> optimalWindows;
  final SchedulingPatterns? patterns;

  const SmartSchedulingState({
    this.isLoading = false,
    this.error,
    this.suggestions = const [],
    this.optimalWindows = const [],
    this.patterns,
  });

  SmartSchedulingState copyWith({
    bool? isLoading,
    String? error,
    List<SlotSuggestion>? suggestions,
    List<OptimalWindow>? optimalWindows,
    SchedulingPatterns? patterns,
  }) {
    return SmartSchedulingState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      suggestions: suggestions ?? this.suggestions,
      optimalWindows: optimalWindows ?? this.optimalWindows,
      patterns: patterns ?? this.patterns,
    );
  }
}

// Data Models
class SlotSuggestion {
  final DateTime slotTime;
  final double score;
  final List<String> reasons;
  final String doctorId;
  final int durationMinutes;

  SlotSuggestion({
    required this.slotTime,
    required this.score,
    required this.reasons,
    required this.doctorId,
    required this.durationMinutes,
  });

  factory SlotSuggestion.fromJson(Map<String, dynamic> json) {
    return SlotSuggestion(
      slotTime: DateTime.parse(json['slot_time']),
      score: (json['score'] as num).toDouble(),
      reasons: (json['reasons'] as List<dynamic>).cast<String>(),
      doctorId: json['doctor_id'],
      durationMinutes: json['duration_minutes'],
    );
  }

  /// Get a short summary of reasons (first 2)
  String get reasonsSummary {
    if (reasons.isEmpty) return 'Recommended slot';
    if (reasons.length == 1) return reasons[0];
    return '${reasons[0]}, ${reasons[1]}';
  }

  /// Get confidence level based on score
  String get confidenceLevel {
    if (score >= 80) return 'Excellent match';
    if (score >= 60) return 'Good match';
    if (score >= 40) return 'Fair match';
    return 'Available slot';
  }
}

class OptimalWindow {
  final int hour;
  final String timeRange;
  final int appointmentCount;
  final double averageWaitMinutes;
  final bool isOptimal;

  OptimalWindow({
    required this.hour,
    required this.timeRange,
    required this.appointmentCount,
    required this.averageWaitMinutes,
    required this.isOptimal,
  });

  factory OptimalWindow.fromJson(Map<String, dynamic> json) {
    return OptimalWindow(
      hour: json['hour'],
      timeRange: json['time_range'],
      appointmentCount: json['appointment_count'],
      averageWaitMinutes: (json['average_wait_minutes'] as num).toDouble(),
      isOptimal: json['is_optimal'],
    );
  }
}

class SchedulingPatterns {
  final String doctorId;
  final Map<String, String> period;
  final int totalAppointments;
  final PatternDetails patterns;
  final List<String> recommendations;

  SchedulingPatterns({
    required this.doctorId,
    required this.period,
    required this.totalAppointments,
    required this.patterns,
    required this.recommendations,
  });

  factory SchedulingPatterns.fromJson(Map<String, dynamic> json) {
    return SchedulingPatterns(
      doctorId: json['doctor_id'],
      period: Map<String, String>.from(json['period']),
      totalAppointments: json['total_appointments'],
      patterns: PatternDetails.fromJson(json['patterns']),
      recommendations: (json['recommendations'] as List<dynamic>).cast<String>(),
    );
  }
}

class PatternDetails {
  final int peakHour;
  final String peakHourRange;
  final String peakDay;
  final int busiestDayCount;
  final Map<String, int> hourlyDistribution;
  final Map<String, int> dailyDistribution;
  final Map<String, int> appointmentTypes;

  PatternDetails({
    required this.peakHour,
    required this.peakHourRange,
    required this.peakDay,
    required this.busiestDayCount,
    required this.hourlyDistribution,
    required this.dailyDistribution,
    required this.appointmentTypes,
  });

  factory PatternDetails.fromJson(Map<String, dynamic> json) {
    return PatternDetails(
      peakHour: json['peak_hour'],
      peakHourRange: json['peak_hour_range'],
      peakDay: json['peak_day'],
      busiestDayCount: json['busiest_day_count'],
      hourlyDistribution: Map<String, int>.from(
        (json['hourly_distribution'] as Map).map(
          (k, v) => MapEntry(k.toString(), v as int),
        ),
      ),
      dailyDistribution: Map<String, int>.from(json['daily_distribution']),
      appointmentTypes: Map<String, int>.from(json['appointment_types']),
    );
  }
}

// StateNotifier for smart scheduling
class SmartSchedulingNotifier extends StateNotifier<SmartSchedulingState> {
  final SmartSchedulingService _service;

  SmartSchedulingNotifier(this._service) : super(const SmartSchedulingState());

  /// Load slot suggestions for a patient
  Future<void> loadSuggestions({
    required String patientId,
    required String doctorId,
    String appointmentType = 'new_consultation',
    String? preferredDate,
    int durationMinutes = 15,
    int maxSuggestions = 5,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _service.getSlotSuggestions(
        patientId: patientId,
        doctorId: doctorId,
        appointmentType: appointmentType,
        preferredDate: preferredDate,
        durationMinutes: durationMinutes,
        maxSuggestions: maxSuggestions,
      );

      final suggestions = (response['suggestions'] as List<dynamic>)
          .map((json) => SlotSuggestion.fromJson(json))
          .toList();

      state = state.copyWith(
        isLoading: false,
        suggestions: suggestions,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load suggestions: $e',
      );
    }
  }

  /// Load optimal booking times for a doctor
  Future<void> loadOptimalTimes({
    required String doctorId,
    int days = 30,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _service.getOptimalBookingTimes(
        doctorId: doctorId,
        days: days,
      );

      final windows = (response['optimal_windows'] as List<dynamic>)
          .map((json) => OptimalWindow.fromJson(json))
          .toList();

      state = state.copyWith(
        isLoading: false,
        optimalWindows: windows,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load optimal times: $e',
      );
    }
  }

  /// Load scheduling patterns for a doctor
  Future<void> loadPatterns({
    required String doctorId,
    String period = 'month',
    String? startDate,
    String? endDate,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _service.getSchedulingPatterns(
        doctorId: doctorId,
        period: period,
        startDate: startDate,
        endDate: endDate,
      );

      final patterns = SchedulingPatterns.fromJson(response);

      state = state.copyWith(
        isLoading: false,
        patterns: patterns,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load patterns: $e',
      );
    }
  }

  /// Submit feedback on a suggestion
  Future<void> submitFeedback({
    required String patientId,
    required String doctorId,
    required DateTime suggestedSlot,
    required bool wasAccepted,
    DateTime? actualSlot,
    String? feedbackNotes,
  }) async {
    try {
      await _service.submitSuggestionFeedback(
        patientId: patientId,
        doctorId: doctorId,
        suggestedSlot: suggestedSlot.toIso8601String(),
        wasAccepted: wasAccepted,
        actualSlot: actualSlot?.toIso8601String(),
        feedbackNotes: feedbackNotes,
      );
    } catch (e) {
      // Log error but don't update state - feedback is non-critical
      print('Failed to submit suggestion feedback: $e');
    }
  }

  /// Clear suggestions
  void clearSuggestions() {
    state = state.copyWith(
      suggestions: [],
      error: null,
    );
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

// Provider for smart scheduling state
final smartSchedulingProvider =
    StateNotifierProvider<SmartSchedulingNotifier, SmartSchedulingState>((ref) {
  final service = ref.watch(smartSchedulingServiceProvider);
  return SmartSchedulingNotifier(service);
});

// Convenience provider to auto-load suggestions when patient is selected
final autoSuggestionsProvider = FutureProvider.family<List<SlotSuggestion>, Map<String, String>>(
  (ref, params) async {
    final service = ref.watch(smartSchedulingServiceProvider);

    final response = await service.getSlotSuggestions(
      patientId: params['patientId']!,
      doctorId: params['doctorId']!,
      appointmentType: params['appointmentType'] ?? 'new_consultation',
      durationMinutes: int.tryParse(params['durationMinutes'] ?? '15') ?? 15,
      maxSuggestions: int.tryParse(params['maxSuggestions'] ?? '5') ?? 5,
    );

    return (response['suggestions'] as List<dynamic>)
        .map((json) => SlotSuggestion.fromJson(json))
        .toList();
  },
);
