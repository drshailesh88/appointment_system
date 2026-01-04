import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../api/api_client.dart';
import '../../config/app_config.dart';

/// Report service for generating, downloading, and sharing reports
class ReportService {
  final ApiClient _apiClient;

  ReportService(this._apiClient);

  /// Generate a report
  ///
  /// [reportType] - Type of report (daily, weekly, monthly, custom)
  /// [format] - Export format (pdf, excel, csv)
  /// [dateFrom] - Start date for custom reports
  /// [dateTo] - End date for custom reports
  /// [filters] - Additional filters (doctor_id, etc.)
  Future<Map<String, dynamic>> generateReport({
    required String reportType,
    required String format,
    String? dateFrom,
    String? dateTo,
    Map<String, dynamic>? filters,
  }) async {
    final response = await _apiClient.post('/reports/generate', {
      'report_type': reportType,
      'format': format,
      if (dateFrom != null) 'date_from': dateFrom,
      if (dateTo != null) 'date_to': dateTo,
      if (filters != null) ...filters,
    });

    return response as Map<String, dynamic>;
  }

  /// Download report file to device
  ///
  /// [reportId] - ID of the generated report
  /// [onProgress] - Progress callback (receives value between 0.0 and 1.0)
  /// Returns the local file path
  Future<String> downloadReport(
    String reportId, {
    void Function(double progress)? onProgress,
  }) async {
    try {
      // Get app directory
      final dir = await getApplicationDocumentsDirectory();
      final reportsDir = Directory('${dir.path}/reports');

      // Create reports directory if it doesn't exist
      if (!await reportsDir.exists()) {
        await reportsDir.create(recursive: true);
      }

      // Get report details first to know the filename
      final reportDetails = await _apiClient.get('/reports/$reportId');
      final filename = reportDetails['filename'] ?? 'report_$reportId.pdf';
      final filePath = '${reportsDir.path}/$filename';

      // Download the file using Dio
      final dio = Dio();
      await dio.download(
        '${AppConfig.baseUrl}/reports/$reportId/download',
        filePath,
        onReceiveProgress: (received, total) {
          if (total != -1 && onProgress != null) {
            onProgress(received / total);
          }
        },
      );

      return filePath;
    } catch (e) {
      throw Exception('Failed to download report: $e');
    }
  }

  /// Share report file
  ///
  /// [filePath] - Path to the local report file
  /// [subject] - Email subject (optional)
  /// [text] - Share message text (optional)
  Future<void> shareReport(
    String filePath, {
    String? subject,
    String? text,
  }) async {
    try {
      await Share.shareXFiles(
        [XFile(filePath)],
        subject: subject ?? 'Report from DocAssist Practice Manager',
        text: text,
      );
    } catch (e) {
      throw Exception('Failed to share report: $e');
    }
  }

  /// Email report to recipients
  ///
  /// [reportId] - ID of the generated report
  /// [recipients] - List of email addresses
  /// [subject] - Email subject
  /// [message] - Email body message
  Future<void> emailReport({
    required String reportId,
    required List<String> recipients,
    String? subject,
    String? message,
  }) async {
    await _apiClient.post('/reports/$reportId/email', {
      'recipients': recipients,
      if (subject != null) 'subject': subject,
      if (message != null) 'message': message,
    });
  }

  /// Get list of recent reports
  ///
  /// [limit] - Number of reports to fetch
  Future<List<Map<String, dynamic>>> getRecentReports({int limit = 20}) async {
    final response = await _apiClient.get('/reports/recent?limit=$limit');
    return List<Map<String, dynamic>>.from(response as List);
  }

  /// Get list of scheduled reports
  Future<List<Map<String, dynamic>>> getScheduledReports() async {
    final response = await _apiClient.get('/reports/scheduled');
    return List<Map<String, dynamic>>.from(response as List);
  }

  /// Create a scheduled report
  ///
  /// [reportType] - Type of report
  /// [format] - Export format
  /// [frequency] - Schedule frequency (daily, weekly, monthly)
  /// [recipients] - List of email addresses to send to
  /// [enabled] - Whether the schedule is active
  Future<Map<String, dynamic>> createScheduledReport({
    required String reportType,
    required String format,
    required String frequency,
    required List<String> recipients,
    bool enabled = true,
    Map<String, dynamic>? filters,
  }) async {
    final response = await _apiClient.post('/reports/scheduled', {
      'report_type': reportType,
      'format': format,
      'frequency': frequency,
      'recipients': recipients,
      'enabled': enabled,
      if (filters != null) ...filters,
    });

    return response as Map<String, dynamic>;
  }

  /// Update a scheduled report
  Future<Map<String, dynamic>> updateScheduledReport(
    String scheduleId,
    Map<String, dynamic> data,
  ) async {
    final response = await _apiClient.put('/reports/scheduled/$scheduleId', data);
    return response as Map<String, dynamic>;
  }

  /// Delete a scheduled report
  Future<void> deleteScheduledReport(String scheduleId) async {
    await _apiClient.delete('/reports/scheduled/$scheduleId');
  }

  /// Toggle scheduled report enabled status
  Future<void> toggleScheduledReport(String scheduleId, bool enabled) async {
    await _apiClient.patch('/reports/scheduled/$scheduleId', {
      'enabled': enabled,
    });
  }

  /// Get report by ID
  Future<Map<String, dynamic>> getReport(String reportId) async {
    final response = await _apiClient.get('/reports/$reportId');
    return response as Map<String, dynamic>;
  }

  /// Delete a report
  Future<void> deleteReport(String reportId) async {
    await _apiClient.delete('/reports/$reportId');
  }

  /// Check if a local report file exists
  Future<bool> reportFileExists(String reportId) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final reportsDir = Directory('${dir.path}/reports');

      if (!await reportsDir.exists()) {
        return false;
      }

      final files = await reportsDir.list().toList();
      return files.any((file) => file.path.contains(reportId));
    } catch (e) {
      return false;
    }
  }

  /// Get local report file path if it exists
  Future<String?> getLocalReportPath(String reportId) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final reportsDir = Directory('${dir.path}/reports');

      if (!await reportsDir.exists()) {
        return null;
      }

      final files = await reportsDir.list().toList();
      final file = files.firstWhere(
        (file) => file.path.contains(reportId),
        orElse: () => throw Exception('Not found'),
      );

      return file.path;
    } catch (e) {
      return null;
    }
  }
}
