import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/health_record.dart';
import '../services/health_service.dart';

/// Health state for tracking connection and data
class HealthState {
  final HealthConnectionStatus connectionStatus;
  final HealthPermissions permissions;
  final HealthSummary? summary;
  final List<HealthReading> recentReadings;
  final bool isSyncing;
  final bool isLoading;
  final String? error;
  final DateTime? lastSyncedAt;
  final int syncedCount;

  const HealthState({
    this.connectionStatus = HealthConnectionStatus.disconnected,
    this.permissions = const HealthPermissions(),
    this.summary,
    this.recentReadings = const [],
    this.isSyncing = false,
    this.isLoading = false,
    this.error,
    this.lastSyncedAt,
    this.syncedCount = 0,
  });

  HealthState copyWith({
    HealthConnectionStatus? connectionStatus,
    HealthPermissions? permissions,
    HealthSummary? summary,
    List<HealthReading>? recentReadings,
    bool? isSyncing,
    bool? isLoading,
    String? error,
    DateTime? lastSyncedAt,
    int? syncedCount,
  }) {
    return HealthState(
      connectionStatus: connectionStatus ?? this.connectionStatus,
      permissions: permissions ?? this.permissions,
      summary: summary ?? this.summary,
      recentReadings: recentReadings ?? this.recentReadings,
      isSyncing: isSyncing ?? this.isSyncing,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
      syncedCount: syncedCount ?? this.syncedCount,
    );
  }

  /// Check if health is connected and ready
  bool get isConnected =>
      connectionStatus == HealthConnectionStatus.connected &&
      permissions.grantedCount > 0;

  /// Check if sync is needed (stale data or never synced)
  bool get needsSync {
    if (lastSyncedAt == null) return true;
    final now = DateTime.now();
    final difference = now.difference(lastSyncedAt!);
    return difference.inHours > 6; // Sync every 6 hours
  }
}

/// Health notifier for managing health state and operations
class HealthNotifier extends StateNotifier<HealthState> {
  final HealthService _healthService;

  HealthNotifier(this._healthService) : super(const HealthState());

  /// Initialize health connection
  ///
  /// Checks if health is available and loads current permissions
  Future<void> initialize() async {
    state = state.copyWith(
      connectionStatus: HealthConnectionStatus.connecting,
      isLoading: true,
      error: null,
    );

    try {
      final isAvailable = await _healthService.isHealthAvailable();

      if (!isAvailable) {
        state = state.copyWith(
          connectionStatus: HealthConnectionStatus.disconnected,
          isLoading: false,
          error: 'Apple Health not available on this device',
        );
        return;
      }

      final permissions = await _healthService.checkPermissions();

      state = state.copyWith(
        connectionStatus: permissions.grantedCount > 0
            ? HealthConnectionStatus.connected
            : HealthConnectionStatus.disconnected,
        permissions: permissions,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        connectionStatus: HealthConnectionStatus.error,
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Request health permissions
  ///
  /// Shows iOS Health permissions dialog
  Future<bool> requestPermissions() async {
    state = state.copyWith(
      connectionStatus: HealthConnectionStatus.connecting,
      error: null,
    );

    try {
      final granted = await _healthService.requestPermissions();

      if (granted) {
        final permissions = await _healthService.checkPermissions();

        state = state.copyWith(
          connectionStatus: HealthConnectionStatus.connected,
          permissions: permissions,
        );
        return true;
      } else {
        state = state.copyWith(
          connectionStatus: HealthConnectionStatus.permissionDenied,
          error: 'Health permissions denied',
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        connectionStatus: HealthConnectionStatus.error,
        error: e.toString(),
      );
      return false;
    }
  }

  /// Sync health data from HealthKit to backend
  ///
  /// [patientId] - Patient ID to sync data for
  /// [daysBack] - Number of days to look back (default: 7)
  Future<void> syncHealthData(String patientId, {int daysBack = 7}) async {
    if (state.isSyncing) {
      return; // Already syncing
    }

    state = state.copyWith(isSyncing: true, error: null);

    try {
      final syncedCount = await _healthService.performFullSync(
        patientId: patientId,
        daysBack: daysBack,
      );

      state = state.copyWith(
        isSyncing: false,
        lastSyncedAt: DateTime.now(),
        syncedCount: syncedCount,
      );

      // Load updated summary
      await loadHealthSummary(patientId);
    } catch (e) {
      state = state.copyWith(
        isSyncing: false,
        error: 'Sync failed: ${e.toString()}',
      );
    }
  }

  /// Load health summary from backend
  ///
  /// [patientId] - Patient ID
  Future<void> loadHealthSummary(String patientId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final summary = await _healthService.getHealthSummary(patientId);

      state = state.copyWith(
        summary: summary,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load health summary: ${e.toString()}',
      );
    }
  }

  /// Load recent health readings
  ///
  /// [patientId] - Patient ID
  /// [metricType] - Optional filter by metric type
  /// [limit] - Maximum number of readings (default: 50)
  Future<void> loadRecentReadings({
    required String patientId,
    HealthMetric? metricType,
    int limit = 50,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final readings = await _healthService.getHealthRecords(
        patientId: patientId,
        metricType: metricType,
        limit: limit,
      );

      state = state.copyWith(
        recentReadings: readings,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load readings: ${e.toString()}',
      );
    }
  }

  /// Load health readings for a specific date range
  ///
  /// [patientId] - Patient ID
  /// [metricType] - Metric type to load
  /// [startDate] - Start date
  /// [endDate] - End date
  Future<List<HealthReading>> loadReadingsForRange({
    required String patientId,
    required HealthMetric metricType,
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    try {
      final readings = await _healthService.getHealthRecords(
        patientId: patientId,
        metricType: metricType,
        startDate: startDate,
        endDate: endDate,
        limit: 1000,
      );

      return readings;
    } catch (e) {
      state = state.copyWith(
        error: 'Failed to load readings: ${e.toString()}',
      );
      return [];
    }
  }

  /// Disconnect from health (clear permissions and data)
  Future<void> disconnect() async {
    state = const HealthState(
      connectionStatus: HealthConnectionStatus.disconnected,
    );
  }

  /// Clear error message
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Enable background health updates
  Future<void> enableBackgroundUpdates() async {
    try {
      await _healthService.enableBackgroundUpdates();
    } catch (e) {
      state = state.copyWith(
        error: 'Failed to enable background updates: ${e.toString()}',
      );
    }
  }
}

/// Provider for HealthService
final healthServiceProvider = Provider<HealthService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return HealthService(apiClient);
});

/// Provider for HealthNotifier and HealthState
final healthProvider = StateNotifierProvider<HealthNotifier, HealthState>((ref) {
  final healthService = ref.watch(healthServiceProvider);
  return HealthNotifier(healthService);
});

/// Provider for auto-syncing health data
///
/// Call this provider with a patient ID to trigger auto-sync if needed
final healthAutoSyncProvider = FutureProvider.family<void, String>((ref, patientId) async {
  final healthNotifier = ref.watch(healthProvider.notifier);
  final healthState = ref.watch(healthProvider);

  // Only sync if connected and sync is needed
  if (healthState.isConnected && healthState.needsSync && !healthState.isSyncing) {
    await healthNotifier.syncHealthData(patientId);
  }
});

/// Provider for checking if specific metric data is available
final hasHealthMetricProvider = Provider.family<bool, HealthMetric>((ref, metric) {
  final summary = ref.watch(healthProvider.select((state) => state.summary));

  if (summary == null) return false;

  switch (metric) {
    case HealthMetric.heartRate:
      return summary.latestHeartRate != null;
    case HealthMetric.bloodPressureSystolic:
    case HealthMetric.bloodPressureDiastolic:
      return summary.latestBloodPressureSystolic != null;
    case HealthMetric.weight:
      return summary.latestWeight != null;
    case HealthMetric.oxygenSaturation:
      return summary.latestOxygenSaturation != null;
    case HealthMetric.bloodGlucose:
      return summary.latestBloodGlucose != null;
    case HealthMetric.steps:
      return summary.todaySteps != null;
    case HealthMetric.sleepAnalysis:
      return summary.todaySleepHours != null;
    default:
      return false;
  }
});
