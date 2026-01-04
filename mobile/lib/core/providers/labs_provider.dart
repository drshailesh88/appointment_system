import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/lab_result.dart';
import '../services/lab_service.dart';

// ==================
// Services
// ==================

final labServiceProvider = Provider<LabService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return LabService(apiClient);
});

// ==================
// State
// ==================

/// Lab orders state for a specific patient
class LabOrdersState {
  final List<LabOrder> orders;
  final bool isLoading;
  final String? error;

  const LabOrdersState({
    this.orders = const [],
    this.isLoading = false,
    this.error,
  });

  LabOrdersState copyWith({
    List<LabOrder>? orders,
    bool? isLoading,
    String? error,
  }) {
    return LabOrdersState(
      orders: orders ?? this.orders,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }

  List<LabOrder> get pendingOrders =>
      orders.where((order) => order.isPending).toList();

  List<LabOrder> get completedOrders =>
      orders.where((order) => order.isCompleted).toList();

  int get abnormalCount =>
      orders.fold(0, (sum, order) => sum + order.abnormalCount);
}

/// Lab orders state notifier
class LabOrdersNotifier extends StateNotifier<LabOrdersState> {
  final LabService _service;
  String? _currentPatientId;

  LabOrdersNotifier(this._service) : super(const LabOrdersState());

  /// Load lab orders for a patient
  Future<void> loadPatientOrders(
    String patientId, {
    String? status,
  }) async {
    _currentPatientId = patientId;
    state = state.copyWith(isLoading: true, error: null);

    try {
      final orders = await _service.getPatientOrders(
        patientId,
        status: status,
      );
      state = state.copyWith(orders: orders, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Refresh orders
  Future<void> refresh() async {
    if (_currentPatientId != null) {
      await loadPatientOrders(_currentPatientId!);
    }
  }

  /// Create new lab order
  Future<LabOrder?> createOrder({
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
    try {
      final order = await _service.createOrder(
        patientId: patientId,
        doctorId: doctorId,
        testsOrdered: testsOrdered,
        appointmentId: appointmentId,
        priority: priority,
        clinicalNotes: clinicalNotes,
        diagnosisCodes: diagnosisCodes,
        expectedCompletion: expectedCompletion,
        labProvider: labProvider,
      );

      // Add to current list
      state = state.copyWith(
        orders: [order, ...state.orders],
      );

      return order;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Update order status
  Future<void> updateOrder(
    String orderId,
    Map<String, dynamic> updates,
  ) async {
    try {
      final updatedOrder = await _service.updateOrder(orderId, updates);

      // Update in list
      final updatedOrders = state.orders.map((order) {
        return order.id == orderId ? updatedOrder : order;
      }).toList();

      state = state.copyWith(orders: updatedOrders);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }
}

/// Lab orders provider
final labOrdersProvider =
    StateNotifierProvider<LabOrdersNotifier, LabOrdersState>((ref) {
  final service = ref.watch(labServiceProvider);
  return LabOrdersNotifier(service);
});

// ==================
// Lab Results State
// ==================

/// Lab results state for a specific order
class LabResultsState {
  final List<LabResult> results;
  final Map<String, List<LabResult>> resultsByCategory;
  final bool isLoading;
  final String? error;

  const LabResultsState({
    this.results = const [],
    this.resultsByCategory = const {},
    this.isLoading = false,
    this.error,
  });

  LabResultsState copyWith({
    List<LabResult>? results,
    Map<String, List<LabResult>>? resultsByCategory,
    bool? isLoading,
    String? error,
  }) {
    return LabResultsState(
      results: results ?? this.results,
      resultsByCategory: resultsByCategory ?? this.resultsByCategory,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }

  List<LabResult> get abnormalResults =>
      results.where((result) => result.isAbnormal).toList();

  List<LabResult> get criticalResults =>
      results.where((result) => result.isCritical).toList();

  int get totalTests => results.length;
  int get abnormalCount => abnormalResults.length;
  int get criticalCount => criticalResults.length;
}

/// Lab results state notifier
class LabResultsNotifier extends StateNotifier<LabResultsState> {
  final LabService _service;

  LabResultsNotifier(this._service) : super(const LabResultsState());

  /// Load results for a patient
  Future<void> loadPatientResults(
    String patientId, {
    String? testName,
    String? testCategory,
    bool? isAbnormal,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final results = await _service.getPatientResults(
        patientId,
        testName: testName,
        testCategory: testCategory,
        isAbnormal: isAbnormal,
      );

      // Group by category
      final grouped = <String, List<LabResult>>{};
      for (final result in results) {
        final category = result.testCategory ?? 'Other';
        grouped.putIfAbsent(category, () => []).add(result);
      }

      state = state.copyWith(
        results: results,
        resultsByCategory: grouped,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Load results for a specific order
  Future<void> loadOrderResults(String orderId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final resultsByCategory =
          await _service.getOrderResultsByCategory(orderId);

      // Flatten results
      final results = resultsByCategory.values.expand((list) => list).toList();

      state = state.copyWith(
        results: results,
        resultsByCategory: resultsByCategory,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Clear results
  void clear() {
    state = const LabResultsState();
  }
}

/// Lab results provider (for current order/patient)
final labResultsProvider =
    StateNotifierProvider<LabResultsNotifier, LabResultsState>((ref) {
  final service = ref.watch(labServiceProvider);
  return LabResultsNotifier(service);
});

// ==================
// Individual Lab Result Provider
// ==================

/// Provider for a single lab result with trends
final labResultWithTrendsProvider =
    FutureProvider.family<LabResultWithTrends, String>((ref, resultId) async {
  final service = ref.watch(labServiceProvider);

  final result = await service.getResult(resultId);
  final trend = await service.getResultTrends(resultId);

  return LabResultWithTrends(result: result, trend: trend);
});

/// Container for result with trend data
class LabResultWithTrends {
  final LabResult result;
  final LabResultTrend trend;

  LabResultWithTrends({
    required this.result,
    required this.trend,
  });
}

// ==================
// Lab Statistics Provider
// ==================

/// Provider for lab statistics
final labStatisticsProvider =
    FutureProvider.family<LabStatistics, String?>((ref, doctorId) async {
  final service = ref.watch(labServiceProvider);
  return service.getStatistics(doctorId: doctorId);
});

// ==================
// Lab Reports Provider
// ==================

/// Provider for lab reports of an order
final labReportsProvider =
    FutureProvider.family<List<LabReport>, String>((ref, orderId) async {
  final service = ref.watch(labServiceProvider);
  return service.getOrderReports(orderId);
});

// ==================
// Helper Providers
// ==================

/// Provider to check if patient has pending lab orders
final hasPendingLabOrdersProvider =
    FutureProvider.family<bool, String>((ref, patientId) async {
  final service = ref.watch(labServiceProvider);
  return service.hasPendingOrders(patientId);
});

/// Provider for abnormal results of a patient
final abnormalResultsProvider =
    FutureProvider.family<List<LabResult>, String>((ref, patientId) async {
  final service = ref.watch(labServiceProvider);
  return service.getAbnormalResults(patientId);
});
