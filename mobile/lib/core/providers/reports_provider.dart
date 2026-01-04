import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../services/report_service.dart';

/// Report model
class Report {
  final String id;
  final String reportType;
  final String format;
  final String filename;
  final DateTime createdAt;
  final String? dateFrom;
  final String? dateTo;
  final int fileSize;
  final String status; // generating, ready, error

  Report({
    required this.id,
    required this.reportType,
    required this.format,
    required this.filename,
    required this.createdAt,
    this.dateFrom,
    this.dateTo,
    required this.fileSize,
    required this.status,
  });

  factory Report.fromJson(Map<String, dynamic> json) {
    return Report(
      id: json['id'] ?? '',
      reportType: json['report_type'] ?? '',
      format: json['format'] ?? 'pdf',
      filename: json['filename'] ?? '',
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      dateFrom: json['date_from'],
      dateTo: json['date_to'],
      fileSize: json['file_size'] ?? 0,
      status: json['status'] ?? 'ready',
    );
  }

  String get displayName {
    switch (reportType) {
      case 'daily':
        return 'Daily Report';
      case 'weekly':
        return 'Weekly Report';
      case 'monthly':
        return 'Monthly Report';
      case 'custom':
        return 'Custom Report';
      case 'appointments':
        return 'Appointments Report';
      case 'revenue':
        return 'Revenue Report';
      case 'doctor_utilization':
        return 'Doctor Utilization Report';
      default:
        return 'Report';
    }
  }

  String get formatIcon {
    switch (format.toLowerCase()) {
      case 'pdf':
        return '📄';
      case 'excel':
      case 'xlsx':
        return '📊';
      case 'csv':
        return '📋';
      default:
        return '📁';
    }
  }
}

/// Scheduled report model
class ScheduledReport {
  final String id;
  final String reportType;
  final String format;
  final String frequency; // daily, weekly, monthly
  final List<String> recipients;
  final bool enabled;
  final DateTime? lastRun;
  final DateTime? nextRun;
  final Map<String, dynamic>? filters;

  ScheduledReport({
    required this.id,
    required this.reportType,
    required this.format,
    required this.frequency,
    required this.recipients,
    required this.enabled,
    this.lastRun,
    this.nextRun,
    this.filters,
  });

  factory ScheduledReport.fromJson(Map<String, dynamic> json) {
    return ScheduledReport(
      id: json['id'] ?? '',
      reportType: json['report_type'] ?? '',
      format: json['format'] ?? 'pdf',
      frequency: json['frequency'] ?? 'monthly',
      recipients: List<String>.from(json['recipients'] ?? []),
      enabled: json['enabled'] ?? true,
      lastRun: json['last_run'] != null ? DateTime.parse(json['last_run']) : null,
      nextRun: json['next_run'] != null ? DateTime.parse(json['next_run']) : null,
      filters: json['filters'] as Map<String, dynamic>?,
    );
  }

  String get displayName {
    final reportName = Report(
      id: '',
      reportType: reportType,
      format: format,
      filename: '',
      createdAt: DateTime.now(),
      fileSize: 0,
      status: 'ready',
    ).displayName;

    return '$frequency $reportName';
  }

  String get frequencyLabel {
    switch (frequency) {
      case 'daily':
        return 'Daily';
      case 'weekly':
        return 'Weekly';
      case 'monthly':
        return 'Monthly';
      default:
        return frequency;
    }
  }
}

/// Reports State
class ReportsState {
  final bool isLoading;
  final String? error;
  final List<Report> recentReports;
  final List<ScheduledReport> scheduledReports;
  final bool isGenerating;
  final double? downloadProgress;
  final String? currentReportId;

  const ReportsState({
    this.isLoading = false,
    this.error,
    this.recentReports = const [],
    this.scheduledReports = const [],
    this.isGenerating = false,
    this.downloadProgress,
    this.currentReportId,
  });

  ReportsState copyWith({
    bool? isLoading,
    String? error,
    List<Report>? recentReports,
    List<ScheduledReport>? scheduledReports,
    bool? isGenerating,
    double? downloadProgress,
    String? currentReportId,
  }) {
    return ReportsState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      recentReports: recentReports ?? this.recentReports,
      scheduledReports: scheduledReports ?? this.scheduledReports,
      isGenerating: isGenerating ?? this.isGenerating,
      downloadProgress: downloadProgress,
      currentReportId: currentReportId ?? this.currentReportId,
    );
  }
}

/// Reports Notifier
class ReportsNotifier extends StateNotifier<ReportsState> {
  final ReportService _reportService;

  ReportsNotifier(this._reportService) : super(const ReportsState());

  /// Load recent reports
  Future<void> loadRecentReports() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final reportsData = await _reportService.getRecentReports();
      final reports = reportsData.map((r) => Report.fromJson(r)).toList();

      state = state.copyWith(
        isLoading: false,
        recentReports: reports,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Load scheduled reports
  Future<void> loadScheduledReports() async {
    try {
      final schedulesData = await _reportService.getScheduledReports();
      final schedules =
          schedulesData.map((s) => ScheduledReport.fromJson(s)).toList();

      state = state.copyWith(scheduledReports: schedules);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Generate a new report
  Future<Report?> generateReport({
    required String reportType,
    required String format,
    String? dateFrom,
    String? dateTo,
    Map<String, dynamic>? filters,
  }) async {
    state = state.copyWith(isGenerating: true, error: null);

    try {
      final result = await _reportService.generateReport(
        reportType: reportType,
        format: format,
        dateFrom: dateFrom,
        dateTo: dateTo,
        filters: filters,
      );

      final report = Report.fromJson(result);

      // Add to recent reports
      state = state.copyWith(
        isGenerating: false,
        recentReports: [report, ...state.recentReports],
      );

      return report;
    } catch (e) {
      state = state.copyWith(
        isGenerating: false,
        error: 'Failed to generate report: $e',
      );
      return null;
    }
  }

  /// Download report to device
  Future<String?> downloadReport(String reportId) async {
    state = state.copyWith(
      currentReportId: reportId,
      downloadProgress: 0.0,
      error: null,
    );

    try {
      final filePath = await _reportService.downloadReport(
        reportId,
        onProgress: (progress) {
          state = state.copyWith(downloadProgress: progress);
        },
      );

      state = state.copyWith(
        downloadProgress: null,
        currentReportId: null,
      );

      return filePath;
    } catch (e) {
      state = state.copyWith(
        downloadProgress: null,
        currentReportId: null,
        error: 'Failed to download report: $e',
      );
      return null;
    }
  }

  /// Share report
  Future<void> shareReport(String filePath, {String? reportName}) async {
    try {
      await _reportService.shareReport(
        filePath,
        text: reportName != null ? 'Sharing $reportName' : null,
      );
    } catch (e) {
      state = state.copyWith(error: 'Failed to share report: $e');
    }
  }

  /// Email report
  Future<void> emailReport({
    required String reportId,
    required List<String> recipients,
    String? subject,
    String? message,
  }) async {
    state = state.copyWith(error: null);

    try {
      await _reportService.emailReport(
        reportId: reportId,
        recipients: recipients,
        subject: subject,
        message: message,
      );
    } catch (e) {
      state = state.copyWith(error: 'Failed to email report: $e');
    }
  }

  /// Create scheduled report
  Future<ScheduledReport?> createScheduledReport({
    required String reportType,
    required String format,
    required String frequency,
    required List<String> recipients,
    bool enabled = true,
    Map<String, dynamic>? filters,
  }) async {
    state = state.copyWith(error: null);

    try {
      final result = await _reportService.createScheduledReport(
        reportType: reportType,
        format: format,
        frequency: frequency,
        recipients: recipients,
        enabled: enabled,
        filters: filters,
      );

      final schedule = ScheduledReport.fromJson(result);

      // Add to scheduled reports
      state = state.copyWith(
        scheduledReports: [...state.scheduledReports, schedule],
      );

      return schedule;
    } catch (e) {
      state = state.copyWith(error: 'Failed to create schedule: $e');
      return null;
    }
  }

  /// Update scheduled report
  Future<void> updateScheduledReport(
    String scheduleId,
    Map<String, dynamic> data,
  ) async {
    try {
      final result = await _reportService.updateScheduledReport(scheduleId, data);
      final updatedSchedule = ScheduledReport.fromJson(result);

      // Update in list
      final updatedList = state.scheduledReports.map((s) {
        return s.id == scheduleId ? updatedSchedule : s;
      }).toList();

      state = state.copyWith(scheduledReports: updatedList);
    } catch (e) {
      state = state.copyWith(error: 'Failed to update schedule: $e');
    }
  }

  /// Delete scheduled report
  Future<void> deleteScheduledReport(String scheduleId) async {
    try {
      await _reportService.deleteScheduledReport(scheduleId);

      // Remove from list
      final updatedList =
          state.scheduledReports.where((s) => s.id != scheduleId).toList();

      state = state.copyWith(scheduledReports: updatedList);
    } catch (e) {
      state = state.copyWith(error: 'Failed to delete schedule: $e');
    }
  }

  /// Toggle scheduled report enabled status
  Future<void> toggleScheduledReport(String scheduleId, bool enabled) async {
    try {
      await _reportService.toggleScheduledReport(scheduleId, enabled);

      // Update in list
      final updatedList = state.scheduledReports.map((s) {
        if (s.id == scheduleId) {
          return ScheduledReport(
            id: s.id,
            reportType: s.reportType,
            format: s.format,
            frequency: s.frequency,
            recipients: s.recipients,
            enabled: enabled,
            lastRun: s.lastRun,
            nextRun: s.nextRun,
            filters: s.filters,
          );
        }
        return s;
      }).toList();

      state = state.copyWith(scheduledReports: updatedList);
    } catch (e) {
      state = state.copyWith(error: 'Failed to toggle schedule: $e');
    }
  }

  /// Delete a report
  Future<void> deleteReport(String reportId) async {
    try {
      await _reportService.deleteReport(reportId);

      // Remove from list
      final updatedList = state.recentReports.where((r) => r.id != reportId).toList();

      state = state.copyWith(recentReports: updatedList);
    } catch (e) {
      state = state.copyWith(error: 'Failed to delete report: $e');
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Report service provider
final reportServiceProvider = Provider<ReportService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ReportService(apiClient);
});

/// Reports provider
final reportsProvider = StateNotifierProvider<ReportsNotifier, ReportsState>((ref) {
  final reportService = ref.watch(reportServiceProvider);
  return ReportsNotifier(reportService);
});
