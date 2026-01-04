import 'dart:io';
import '../api/api_client.dart';
import '../models/lab_result.dart';

/// Lab service for managing lab orders and results
class LabService {
  final ApiClient _apiClient;

  LabService(this._apiClient);

  // ==================
  // Lab Orders
  // ==================

  /// Create a new lab order
  Future<LabOrder> createOrder({
    required String patientId,
    required String doctorId,
    required List<String> testsOrdered,
    String? appointmentId,
    String priority = 'routine',
    String? clinicalNotes,
    List<String>? diagnosisCodes,
    DateTime? expectedCompletion,
    String? labProvider,
  }) async {
    final response = await _apiClient.post('/labs/orders', {
      'patient_id': patientId,
      'doctor_id': doctorId,
      'tests_ordered': testsOrdered,
      if (appointmentId != null) 'appointment_id': appointmentId,
      'priority': priority,
      if (clinicalNotes != null) 'clinical_notes': clinicalNotes,
      if (diagnosisCodes != null) 'diagnosis_codes': diagnosisCodes,
      if (expectedCompletion != null)
        'expected_completion': expectedCompletion.toIso8601String(),
      if (labProvider != null) 'lab_provider': labProvider,
    });

    return LabOrder.fromJson(response as Map<String, dynamic>);
  }

  /// Get a specific lab order
  Future<LabOrder> getOrder(String orderId) async {
    final response = await _apiClient.get('/labs/orders/$orderId');
    return LabOrder.fromJson(response as Map<String, dynamic>);
  }

  /// Get all lab orders for a patient
  Future<List<LabOrder>> getPatientOrders(
    String patientId, {
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.get(
      '/labs/patient/$patientId/orders',
      queryParameters: {
        if (status != null) 'status': status,
        'limit': limit,
        'offset': offset,
      },
    );

    final data = response as Map<String, dynamic>;
    final orders = data['orders'] as List;
    return orders
        .map((json) => LabOrder.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  /// Update a lab order
  Future<LabOrder> updateOrder(
    String orderId,
    Map<String, dynamic> updates,
  ) async {
    final response = await _apiClient.patch('/labs/orders/$orderId', updates);
    return LabOrder.fromJson(response as Map<String, dynamic>);
  }

  // ==================
  // Lab Results
  // ==================

  /// Get a specific lab result
  Future<LabResult> getResult(String resultId) async {
    final response = await _apiClient.get('/labs/results/$resultId');
    return LabResult.fromJson(response as Map<String, dynamic>);
  }

  /// Get all lab results for a patient
  Future<List<LabResult>> getPatientResults(
    String patientId, {
    String? testName,
    String? testCategory,
    bool? isAbnormal,
    int limit = 100,
  }) async {
    final response = await _apiClient.get(
      '/labs/patient/$patientId/results',
      queryParameters: {
        if (testName != null) 'test_name': testName,
        if (testCategory != null) 'test_category': testCategory,
        if (isAbnormal != null) 'is_abnormal': isAbnormal,
        'limit': limit,
      },
    );

    final results = response as List;
    return results
        .map((json) => LabResult.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  /// Get historical trend data for a specific test
  Future<LabResultTrend> getResultTrends(
    String resultId, {
    int months = 12,
  }) async {
    final response = await _apiClient.get(
      '/labs/results/$resultId/trends',
      queryParameters: {
        'months': months,
      },
    );

    return LabResultTrend.fromJson(response as Map<String, dynamic>);
  }

  // ==================
  // Lab Reports
  // ==================

  /// Upload lab results (PDF or HL7)
  Future<Map<String, dynamic>> uploadResults({
    required String orderId,
    required File file,
    void Function(double progress)? onProgress,
  }) async {
    final response = await _apiClient.uploadFile(
      '/labs/results/upload',
      file: file,
      queryParameters: {'order_id': orderId},
      onProgress: onProgress,
    );

    return response as Map<String, dynamic>;
  }

  /// Get all reports for a lab order
  Future<List<LabReport>> getOrderReports(String orderId) async {
    final response = await _apiClient.get('/labs/orders/$orderId/reports');

    final reports = response as List;
    return reports
        .map((json) => LabReport.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  // ==================
  // Statistics
  // ==================

  /// Get lab statistics
  Future<LabStatistics> getStatistics({
    String? doctorId,
  }) async {
    final response = await _apiClient.get(
      '/labs/statistics',
      queryParameters: {
        if (doctorId != null) 'doctor_id': doctorId,
      },
    );

    return LabStatistics.fromJson(response as Map<String, dynamic>);
  }

  // ==================
  // Helper Methods
  // ==================

  /// Get results grouped by category for a lab order
  Future<Map<String, List<LabResult>>> getOrderResultsByCategory(
    String orderId,
  ) async {
    final order = await getOrder(orderId);
    final results = await getPatientResults(order.patientId);

    // Filter results for this order
    final orderResults = results.where((r) => r.orderId == orderId).toList();

    // Group by category
    final grouped = <String, List<LabResult>>{};
    for (final result in orderResults) {
      final category = result.testCategory ?? 'Other';
      grouped.putIfAbsent(category, () => []).add(result);
    }

    return grouped;
  }

  /// Get abnormal results for a patient
  Future<List<LabResult>> getAbnormalResults(
    String patientId, {
    int limit = 50,
  }) async {
    return getPatientResults(
      patientId,
      isAbnormal: true,
      limit: limit,
    );
  }

  /// Check if patient has any pending lab orders
  Future<bool> hasPendingOrders(String patientId) async {
    final orders = await getPatientOrders(patientId, limit: 1);
    return orders.any((order) => order.isPending);
  }
}
