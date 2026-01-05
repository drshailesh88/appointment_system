import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../services/slot_optimizer_service.dart';

// Slot Optimizer State
class SlotOptimizerState {
  final bool isLoading;
  final String? error;
  final List<OptimalSlot> recommendedSlots;
  final ScheduleAnalysis? scheduleAnalysis;
  final UtilizationMetrics? utilizationMetrics;
  final ScheduleOptimizationSuggestions? optimizationSuggestions;
  final GapIdentification? gapIdentification;
  final double currentUtilization;
  final double potentialUtilization;

  const SlotOptimizerState({
    this.isLoading = false,
    this.error,
    this.recommendedSlots = const [],
    this.scheduleAnalysis,
    this.utilizationMetrics,
    this.optimizationSuggestions,
    this.gapIdentification,
    this.currentUtilization = 0.0,
    this.potentialUtilization = 0.0,
  });

  SlotOptimizerState copyWith({
    bool? isLoading,
    String? error,
    List<OptimalSlot>? recommendedSlots,
    ScheduleAnalysis? scheduleAnalysis,
    UtilizationMetrics? utilizationMetrics,
    ScheduleOptimizationSuggestions? optimizationSuggestions,
    GapIdentification? gapIdentification,
    double? currentUtilization,
    double? potentialUtilization,
  }) {
    return SlotOptimizerState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      recommendedSlots: recommendedSlots ?? this.recommendedSlots,
      scheduleAnalysis: scheduleAnalysis ?? this.scheduleAnalysis,
      utilizationMetrics: utilizationMetrics ?? this.utilizationMetrics,
      optimizationSuggestions: optimizationSuggestions ?? this.optimizationSuggestions,
      gapIdentification: gapIdentification ?? this.gapIdentification,
      currentUtilization: currentUtilization ?? this.currentUtilization,
      potentialUtilization: potentialUtilization ?? this.potentialUtilization,
    );
  }
}

// Data Models
class OptimalSlot {
  final DateTime slotTime;
  final double score;
  final List<String> reasons;
  final String efficiencyImpact;
  final double utilizationImprovement;
  final int gapReduction;
  final List<String> nearbyAppointmentTypes;

  OptimalSlot({
    required this.slotTime,
    required this.score,
    required this.reasons,
    required this.efficiencyImpact,
    required this.utilizationImprovement,
    required this.gapReduction,
    required this.nearbyAppointmentTypes,
  });

  factory OptimalSlot.fromJson(Map<String, dynamic> json) {
    return OptimalSlot(
      slotTime: DateTime.parse(json['slot_time']),
      score: (json['score'] ?? 0).toDouble(),
      reasons: List<String>.from(json['reasons'] ?? []),
      efficiencyImpact: json['efficiency_impact'] ?? '',
      utilizationImprovement: (json['utilization_improvement'] ?? 0).toDouble(),
      gapReduction: json['gap_reduction'] ?? 0,
      nearbyAppointmentTypes: List<String>.from(json['nearby_appointment_types'] ?? []),
    );
  }
}

class ScheduleAnalysis {
  final String doctorId;
  final String doctorName;
  final DateTime date;
  final double utilizationRate;
  final int gapCount;
  final int totalGapMinutes;
  final int longestGapMinutes;
  final int appointmentCount;
  final int workingHours;
  final List<String> suggestions;
  final double efficiencyScore;
  final List<ScheduleGap> gaps;

  ScheduleAnalysis({
    required this.doctorId,
    required this.doctorName,
    required this.date,
    required this.utilizationRate,
    required this.gapCount,
    required this.totalGapMinutes,
    required this.longestGapMinutes,
    required this.appointmentCount,
    required this.workingHours,
    required this.suggestions,
    required this.efficiencyScore,
    required this.gaps,
  });

  factory ScheduleAnalysis.fromJson(Map<String, dynamic> json) {
    return ScheduleAnalysis(
      doctorId: json['doctor_id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      date: DateTime.parse(json['date']),
      utilizationRate: (json['utilization_rate'] ?? 0).toDouble(),
      gapCount: json['gap_count'] ?? 0,
      totalGapMinutes: json['total_gap_minutes'] ?? 0,
      longestGapMinutes: json['longest_gap_minutes'] ?? 0,
      appointmentCount: json['appointment_count'] ?? 0,
      workingHours: json['working_hours'] ?? 0,
      suggestions: List<String>.from(json['suggestions'] ?? []),
      efficiencyScore: (json['efficiency_score'] ?? 0).toDouble(),
      gaps: (json['gaps'] as List<dynamic>?)
              ?.map((g) => ScheduleGap.fromJson(g))
              .toList() ??
          [],
    );
  }
}

class ScheduleGap {
  final DateTime gapStart;
  final DateTime gapEnd;
  final int durationMinutes;
  final bool isFillable;
  final String reason;
  final String recommendedAction;

  ScheduleGap({
    required this.gapStart,
    required this.gapEnd,
    required this.durationMinutes,
    required this.isFillable,
    required this.reason,
    required this.recommendedAction,
  });

  factory ScheduleGap.fromJson(Map<String, dynamic> json) {
    return ScheduleGap(
      gapStart: DateTime.parse(json['gap_start']),
      gapEnd: DateTime.parse(json['gap_end']),
      durationMinutes: json['duration_minutes'] ?? 0,
      isFillable: json['is_fillable'] ?? false,
      reason: json['reason'] ?? '',
      recommendedAction: json['recommended_action'] ?? '',
    );
  }
}

class UtilizationMetric {
  final String label;
  final double utilizationRate;
  final int bookedSlots;
  final int availableSlots;
  final int gapMinutes;

  UtilizationMetric({
    required this.label,
    required this.utilizationRate,
    required this.bookedSlots,
    required this.availableSlots,
    required this.gapMinutes,
  });

  factory UtilizationMetric.fromJson(Map<String, dynamic> json) {
    return UtilizationMetric(
      label: json['label'] ?? '',
      utilizationRate: (json['utilization_rate'] ?? 0).toDouble(),
      bookedSlots: json['booked_slots'] ?? 0,
      availableSlots: json['available_slots'] ?? 0,
      gapMinutes: json['gap_minutes'] ?? 0,
    );
  }
}

class UtilizationMetrics {
  final String doctorId;
  final String doctorName;
  final DateTime dateRangeStart;
  final DateTime dateRangeEnd;
  final List<UtilizationMetric> byHour;
  final List<UtilizationMetric> byDay;
  final double overallUtilization;
  final List<int> peakHours;
  final List<int> lowHours;
  final Map<String, dynamic> trends;

  UtilizationMetrics({
    required this.doctorId,
    required this.doctorName,
    required this.dateRangeStart,
    required this.dateRangeEnd,
    required this.byHour,
    required this.byDay,
    required this.overallUtilization,
    required this.peakHours,
    required this.lowHours,
    required this.trends,
  });

  factory UtilizationMetrics.fromJson(Map<String, dynamic> json) {
    return UtilizationMetrics(
      doctorId: json['doctor_id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      dateRangeStart: DateTime.parse(json['date_range_start']),
      dateRangeEnd: DateTime.parse(json['date_range_end']),
      byHour: (json['by_hour'] as List<dynamic>?)
              ?.map((m) => UtilizationMetric.fromJson(m))
              .toList() ??
          [],
      byDay: (json['by_day'] as List<dynamic>?)
              ?.map((m) => UtilizationMetric.fromJson(m))
              .toList() ??
          [],
      overallUtilization: (json['overall_utilization'] ?? 0).toDouble(),
      peakHours: List<int>.from(json['peak_hours'] ?? []),
      lowHours: List<int>.from(json['low_hours'] ?? []),
      trends: json['trends'] ?? {},
    );
  }
}

class ScheduleAdjustment {
  final String adjustmentType;
  final dynamic currentValue;
  final dynamic suggestedValue;
  final String reason;
  final double expectedImprovement;
  final String priority;

  ScheduleAdjustment({
    required this.adjustmentType,
    required this.currentValue,
    required this.suggestedValue,
    required this.reason,
    required this.expectedImprovement,
    required this.priority,
  });

  factory ScheduleAdjustment.fromJson(Map<String, dynamic> json) {
    return ScheduleAdjustment(
      adjustmentType: json['adjustment_type'] ?? '',
      currentValue: json['current_value'],
      suggestedValue: json['suggested_value'],
      reason: json['reason'] ?? '',
      expectedImprovement: (json['expected_improvement'] ?? 0).toDouble(),
      priority: json['priority'] ?? '',
    );
  }
}

class ScheduleOptimizationSuggestions {
  final String doctorId;
  final String doctorName;
  final double currentEfficiencyScore;
  final double potentialEfficiencyScore;
  final List<ScheduleAdjustment> adjustments;
  final String summary;
  final Map<String, dynamic> estimatedImpact;

  ScheduleOptimizationSuggestions({
    required this.doctorId,
    required this.doctorName,
    required this.currentEfficiencyScore,
    required this.potentialEfficiencyScore,
    required this.adjustments,
    required this.summary,
    required this.estimatedImpact,
  });

  factory ScheduleOptimizationSuggestions.fromJson(Map<String, dynamic> json) {
    return ScheduleOptimizationSuggestions(
      doctorId: json['doctor_id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      currentEfficiencyScore: (json['current_efficiency_score'] ?? 0).toDouble(),
      potentialEfficiencyScore: (json['potential_efficiency_score'] ?? 0).toDouble(),
      adjustments: (json['adjustments'] as List<dynamic>?)
              ?.map((a) => ScheduleAdjustment.fromJson(a))
              .toList() ??
          [],
      summary: json['summary'] ?? '',
      estimatedImpact: json['estimated_impact'] ?? {},
    );
  }
}

class GapIdentification {
  final String doctorId;
  final String doctorName;
  final DateTime date;
  final List<ScheduleGap> gaps;
  final int totalGapMinutes;
  final int fillableGapCount;
  final List<String> recommendations;

  GapIdentification({
    required this.doctorId,
    required this.doctorName,
    required this.date,
    required this.gaps,
    required this.totalGapMinutes,
    required this.fillableGapCount,
    required this.recommendations,
  });

  factory GapIdentification.fromJson(Map<String, dynamic> json) {
    return GapIdentification(
      doctorId: json['doctor_id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      date: DateTime.parse(json['date']),
      gaps: (json['gaps'] as List<dynamic>?)
              ?.map((g) => ScheduleGap.fromJson(g))
              .toList() ??
          [],
      totalGapMinutes: json['total_gap_minutes'] ?? 0,
      fillableGapCount: json['fillable_gap_count'] ?? 0,
      recommendations: List<String>.from(json['recommendations'] ?? []),
    );
  }
}

// Slot Optimizer Notifier
class SlotOptimizerNotifier extends StateNotifier<SlotOptimizerState> {
  final SlotOptimizerService _service;

  SlotOptimizerNotifier(this._service) : super(const SlotOptimizerState());

  Future<void> loadOptimalSlots({
    required String doctorId,
    required DateTime dateFrom,
    required DateTime dateTo,
    int durationMinutes = 15,
    String? appointmentType,
    String? patientId,
    int maxRecommendations = 5,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final dateFormat = DateFormat('yyyy-MM-dd');
      final response = await _service.getOptimalSlots(
        doctorId: doctorId,
        dateFrom: dateFormat.format(dateFrom),
        dateTo: dateFormat.format(dateTo),
        durationMinutes: durationMinutes,
        appointmentType: appointmentType,
        patientId: patientId,
        maxRecommendations: maxRecommendations,
      );

      final slots = (response['recommended_slots'] as List<dynamic>?)
              ?.map((s) => OptimalSlot.fromJson(s))
              .toList() ??
          [];

      state = state.copyWith(
        isLoading: false,
        recommendedSlots: slots,
        currentUtilization: (response['current_utilization'] ?? 0).toDouble(),
        potentialUtilization: (response['potential_utilization'] ?? 0).toDouble(),
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> analyzeSchedule({
    required String doctorId,
    required DateTime targetDate,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final dateFormat = DateFormat('yyyy-MM-dd');
      final response = await _service.analyzeSchedule(
        doctorId: doctorId,
        targetDate: dateFormat.format(targetDate),
      );

      final analysis = ScheduleAnalysis.fromJson(response);

      state = state.copyWith(
        isLoading: false,
        scheduleAnalysis: analysis,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadUtilizationMetrics({
    required String doctorId,
    required DateTime dateFrom,
    required DateTime dateTo,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final dateFormat = DateFormat('yyyy-MM-dd');
      final response = await _service.getUtilizationMetrics(
        doctorId: doctorId,
        dateFrom: dateFormat.format(dateFrom),
        dateTo: dateFormat.format(dateTo),
      );

      final metrics = UtilizationMetrics.fromJson(response);

      state = state.copyWith(
        isLoading: false,
        utilizationMetrics: metrics,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> identifyGaps({
    required String doctorId,
    required DateTime targetDate,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final dateFormat = DateFormat('yyyy-MM-dd');
      final response = await _service.identifyGaps(
        doctorId: doctorId,
        targetDate: dateFormat.format(targetDate),
      );

      final gaps = GapIdentification.fromJson(response);

      state = state.copyWith(
        isLoading: false,
        gapIdentification: gaps,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadOptimizationSuggestions({
    required String doctorId,
    required DateTime dateFrom,
    required DateTime dateTo,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final dateFormat = DateFormat('yyyy-MM-dd');
      final response = await _service.suggestAdjustments(
        doctorId: doctorId,
        dateFrom: dateFormat.format(dateFrom),
        dateTo: dateFormat.format(dateTo),
      );

      final suggestions = ScheduleOptimizationSuggestions.fromJson(response);

      state = state.copyWith(
        isLoading: false,
        optimizationSuggestions: suggestions,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }
}

// Provider
final slotOptimizerServiceProvider = Provider<SlotOptimizerService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SlotOptimizerService(apiClient);
});

final slotOptimizerProvider =
    StateNotifierProvider<SlotOptimizerNotifier, SlotOptimizerState>((ref) {
  final service = ref.watch(slotOptimizerServiceProvider);
  return SlotOptimizerNotifier(service);
});
