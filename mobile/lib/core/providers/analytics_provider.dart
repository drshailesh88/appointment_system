import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';

// Analytics State
class AnalyticsState {
  final bool isLoading;
  final String? error;
  final AppointmentStats? appointmentStats;
  final RevenueStats? revenueStats;
  final List<DoctorUtilization> doctorUtilization;
  final List<DailyMetric> dailyTrend;

  const AnalyticsState({
    this.isLoading = false,
    this.error,
    this.appointmentStats,
    this.revenueStats,
    this.doctorUtilization = const [],
    this.dailyTrend = const [],
  });

  AnalyticsState copyWith({
    bool? isLoading,
    String? error,
    AppointmentStats? appointmentStats,
    RevenueStats? revenueStats,
    List<DoctorUtilization>? doctorUtilization,
    List<DailyMetric>? dailyTrend,
  }) {
    return AnalyticsState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      appointmentStats: appointmentStats ?? this.appointmentStats,
      revenueStats: revenueStats ?? this.revenueStats,
      doctorUtilization: doctorUtilization ?? this.doctorUtilization,
      dailyTrend: dailyTrend ?? this.dailyTrend,
    );
  }
}

// Data Models
class AppointmentStats {
  final int total;
  final int completed;
  final int cancelled;
  final int noShow;
  final int scheduled;
  final double completionRate;
  final double cancellationRate;
  final double noShowRate;

  AppointmentStats({
    required this.total,
    required this.completed,
    required this.cancelled,
    required this.noShow,
    required this.scheduled,
    required this.completionRate,
    required this.cancellationRate,
    required this.noShowRate,
  });

  factory AppointmentStats.fromJson(Map<String, dynamic> json) {
    return AppointmentStats(
      total: json['total'] ?? 0,
      completed: json['completed'] ?? 0,
      cancelled: json['cancelled'] ?? 0,
      noShow: json['no_show'] ?? 0,
      scheduled: json['scheduled'] ?? 0,
      completionRate: (json['completion_rate'] ?? 0).toDouble(),
      cancellationRate: (json['cancellation_rate'] ?? 0).toDouble(),
      noShowRate: (json['no_show_rate'] ?? 0).toDouble(),
    );
  }
}

class RevenueStats {
  final double totalRevenue;
  final double collected;
  final double pending;
  final double refunded;
  final double collectionRate;
  final double averageInvoice;

  RevenueStats({
    required this.totalRevenue,
    required this.collected,
    required this.pending,
    required this.refunded,
    required this.collectionRate,
    required this.averageInvoice,
  });

  factory RevenueStats.fromJson(Map<String, dynamic> json) {
    return RevenueStats(
      totalRevenue: (json['total_revenue'] ?? 0).toDouble(),
      collected: (json['collected'] ?? 0).toDouble(),
      pending: (json['pending'] ?? 0).toDouble(),
      refunded: (json['refunded'] ?? 0).toDouble(),
      collectionRate: (json['collection_rate'] ?? 0).toDouble(),
      averageInvoice: (json['average_invoice'] ?? 0).toDouble(),
    );
  }
}

class DoctorUtilization {
  final String doctorId;
  final String doctorName;
  final int totalSlots;
  final int bookedSlots;
  final int completedAppointments;
  final double utilizationRate;
  final double averageDuration;
  final double revenueGenerated;

  DoctorUtilization({
    required this.doctorId,
    required this.doctorName,
    required this.totalSlots,
    required this.bookedSlots,
    required this.completedAppointments,
    required this.utilizationRate,
    required this.averageDuration,
    required this.revenueGenerated,
  });

  factory DoctorUtilization.fromJson(Map<String, dynamic> json) {
    return DoctorUtilization(
      doctorId: json['doctor_id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      totalSlots: json['total_slots'] ?? 0,
      bookedSlots: json['booked_slots'] ?? 0,
      completedAppointments: json['completed_appointments'] ?? 0,
      utilizationRate: (json['utilization_rate'] ?? 0).toDouble(),
      averageDuration: (json['average_duration_minutes'] ?? 0).toDouble(),
      revenueGenerated: (json['revenue_generated'] ?? 0).toDouble(),
    );
  }
}

class DailyMetric {
  final DateTime date;
  final int appointments;
  final double revenue;
  final int newPatients;

  DailyMetric({
    required this.date,
    required this.appointments,
    required this.revenue,
    required this.newPatients,
  });

  factory DailyMetric.fromJson(Map<String, dynamic> json) {
    return DailyMetric(
      date: DateTime.parse(json['date']),
      appointments: json['appointments'] ?? 0,
      revenue: (json['revenue'] ?? 0).toDouble(),
      newPatients: json['new_patients'] ?? 0,
    );
  }
}

// Analytics Notifier
class AnalyticsNotifier extends StateNotifier<AnalyticsState> {
  final ApiClient _apiClient;

  AnalyticsNotifier(this._apiClient) : super(const AnalyticsState());

  Future<void> loadDashboard(String period) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _apiClient.get('/analytics/dashboard?period=$period');

      if (response != null) {
        final appointments = response['appointments'] != null
            ? AppointmentStats.fromJson(response['appointments'])
            : null;

        final revenue = response['revenue'] != null
            ? RevenueStats.fromJson(response['revenue'])
            : null;

        final doctors = (response['top_doctors'] as List<dynamic>?)
                ?.map((d) => DoctorUtilization.fromJson(d))
                .toList() ??
            [];

        final daily = (response['daily_trend'] as List<dynamic>?)
                ?.map((d) => DailyMetric.fromJson(d))
                .toList() ??
            [];

        state = state.copyWith(
          isLoading: false,
          appointmentStats: appointments,
          revenueStats: revenue,
          doctorUtilization: doctors,
          dailyTrend: daily,
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadAppointmentStats(String period) async {
    try {
      final response = await _apiClient.get('/analytics/appointments?period=$period');
      if (response != null) {
        state = state.copyWith(
          appointmentStats: AppointmentStats.fromJson(response),
        );
      }
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> loadRevenueStats(String period) async {
    try {
      final response = await _apiClient.get('/analytics/revenue?period=$period');
      if (response != null) {
        state = state.copyWith(
          revenueStats: RevenueStats.fromJson(response),
        );
      }
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> loadDoctorUtilization(String period) async {
    try {
      final response = await _apiClient.get('/analytics/doctors/utilization?period=$period');
      if (response != null) {
        final doctors = (response as List<dynamic>)
            .map((d) => DoctorUtilization.fromJson(d))
            .toList();
        state = state.copyWith(doctorUtilization: doctors);
      }
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }
}

// Provider
final analyticsProvider =
    StateNotifierProvider<AnalyticsNotifier, AnalyticsState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AnalyticsNotifier(apiClient);
});
