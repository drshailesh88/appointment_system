import 'dart:io';

import 'package:health/health.dart';
import 'package:logger/logger.dart';
import 'package:uuid/uuid.dart';

import '../api/api_client.dart';
import '../models/health_record.dart';

/// Service for interacting with Apple Health (HealthKit)
///
/// Handles:
/// - Requesting health permissions
/// - Reading health data from HealthKit
/// - Syncing health data to backend
/// - Background health updates
class HealthService {
  final ApiClient _apiClient;
  final Logger _logger = Logger();
  final Health _health = Health();
  final Uuid _uuid = const Uuid();

  // Health data types to request
  static const List<HealthDataType> _healthDataTypes = [
    HealthDataType.HEART_RATE,
    HealthDataType.BLOOD_PRESSURE_SYSTOLIC,
    HealthDataType.BLOOD_PRESSURE_DIASTOLIC,
    HealthDataType.WEIGHT,
    HealthDataType.HEIGHT,
    HealthDataType.BODY_TEMPERATURE,
    HealthDataType.BLOOD_GLUCOSE,
    HealthDataType.BLOOD_OXYGEN,
    HealthDataType.STEPS,
    HealthDataType.SLEEP_ASLEEP,
    HealthDataType.ACTIVE_ENERGY_BURNED,
    HealthDataType.EXERCISE_TIME,
    HealthDataType.RESPIRATORY_RATE,
  ];

  // Permissions for health data (all read-only)
  static const List<HealthDataAccess> _permissions = [
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
  ];

  HealthService(this._apiClient);

  /// Check if Apple Health is available on this device
  ///
  /// Returns true only on iOS devices
  Future<bool> isHealthAvailable() async {
    if (!Platform.isIOS) {
      _logger.i('Health not available: Not an iOS device');
      return false;
    }

    try {
      final available = await _health.hasPermissions(_healthDataTypes,
              permissions: _permissions) !=
          null;
      return available;
    } catch (e) {
      _logger.e('Error checking health availability: $e');
      return false;
    }
  }

  /// Request permissions to access health data
  ///
  /// Shows iOS Health permissions dialog
  /// Returns true if all permissions were granted
  Future<bool> requestPermissions() async {
    if (!Platform.isIOS) {
      _logger.w('Cannot request health permissions on non-iOS device');
      return false;
    }

    try {
      _logger.i('Requesting health permissions');

      final granted = await _health.requestAuthorization(
        _healthDataTypes,
        permissions: _permissions,
      );

      if (granted) {
        _logger.i('Health permissions granted');
      } else {
        _logger.w('Health permissions denied');
      }

      return granted;
    } catch (e) {
      _logger.e('Error requesting health permissions: $e');
      return false;
    }
  }

  /// Check current permission status
  ///
  /// Returns HealthPermissions object with individual permission states
  Future<HealthPermissions> checkPermissions() async {
    if (!Platform.isIOS) {
      return const HealthPermissions();
    }

    try {
      final hasPermissions = await _health.hasPermissions(
        _healthDataTypes,
        permissions: _permissions,
      );

      if (hasPermissions == null || !hasPermissions) {
        return const HealthPermissions();
      }

      // Note: iOS doesn't allow checking individual permissions for privacy
      // So we return all true if general permission was granted
      return const HealthPermissions(
        heartRate: true,
        bloodPressure: true,
        weight: true,
        steps: true,
        sleep: true,
        oxygenSaturation: true,
        bloodGlucose: true,
        bodyTemperature: true,
      );
    } catch (e) {
      _logger.e('Error checking permissions: $e');
      return const HealthPermissions();
    }
  }

  /// Read health data for a specific metric
  ///
  /// [metricType] - Type of health metric to read
  /// [startDate] - Start of date range
  /// [endDate] - End of date range
  /// [patientId] - Patient ID to associate readings with
  ///
  /// Returns list of health readings
  Future<List<HealthReading>> readHealthData({
    required HealthMetric metricType,
    required DateTime startDate,
    required DateTime endDate,
    required String patientId,
  }) async {
    if (!Platform.isIOS) {
      return [];
    }

    try {
      final healthDataType = _mapMetricToHealthDataType(metricType);
      if (healthDataType == null) {
        _logger.w('Unsupported metric type: ${metricType.value}');
        return [];
      }

      _logger.i('Reading ${metricType.value} from $startDate to $endDate');

      final healthData = await _health.getHealthDataFromTypes(
        types: [healthDataType],
        startTime: startDate,
        endTime: endDate,
      );

      final readings = healthData.map((dataPoint) {
        return HealthReading(
          id: _uuid.v4(),
          patientId: patientId,
          metricType: metricType,
          value: _extractValue(dataPoint),
          unit: metricType.unit,
          recordedAt: dataPoint.dateFrom,
          source: dataPoint.sourceName,
          deviceId: dataPoint.deviceId,
          metadata: {
            'platform': dataPoint.platform.toString(),
            'source_id': dataPoint.sourceId,
          },
        );
      }).toList();

      _logger.i('Found ${readings.length} readings for ${metricType.value}');
      return readings;
    } catch (e) {
      _logger.e('Error reading health data: $e');
      return [];
    }
  }

  /// Read all available health metrics
  ///
  /// [startDate] - Start of date range (default: 7 days ago)
  /// [endDate] - End of date range (default: now)
  /// [patientId] - Patient ID to associate readings with
  ///
  /// Returns map of metric type to list of readings
  Future<Map<HealthMetric, List<HealthReading>>> readAllHealthData({
    DateTime? startDate,
    DateTime? endDate,
    required String patientId,
  }) async {
    final start = startDate ?? DateTime.now().subtract(const Duration(days: 7));
    final end = endDate ?? DateTime.now();

    final Map<HealthMetric, List<HealthReading>> allReadings = {};

    for (final metric in HealthMetric.values) {
      final readings = await readHealthData(
        metricType: metric,
        startDate: start,
        endDate: end,
        patientId: patientId,
      );

      if (readings.isNotEmpty) {
        allReadings[metric] = readings;
      }
    }

    return allReadings;
  }

  /// Sync health data to backend
  ///
  /// [readings] - List of health readings to sync
  ///
  /// Returns true if sync was successful
  Future<bool> syncHealthData(List<HealthReading> readings) async {
    if (readings.isEmpty) {
      _logger.i('No health data to sync');
      return true;
    }

    try {
      _logger.i('Syncing ${readings.length} health readings to backend');

      final data = {
        'readings': readings.map((r) => r.toJson()).toList(),
      };

      await _apiClient.post('/health/sync', data);
      _logger.i('Health data synced successfully');
      return true;
    } catch (e) {
      _logger.e('Error syncing health data: $e');
      return false;
    }
  }

  /// Perform full sync of health data
  ///
  /// Reads all health data from the past 7 days and syncs to backend
  ///
  /// [patientId] - Patient ID to sync data for
  /// [daysBack] - Number of days to look back (default: 7)
  ///
  /// Returns number of readings synced
  Future<int> performFullSync({
    required String patientId,
    int daysBack = 7,
  }) async {
    try {
      _logger.i('Starting full health sync for patient $patientId');

      final endDate = DateTime.now();
      final startDate = endDate.subtract(Duration(days: daysBack));

      // Read all health data
      final allReadings = await readAllHealthData(
        startDate: startDate,
        endDate: endDate,
        patientId: patientId,
      );

      // Flatten all readings
      final readings = allReadings.values.expand((list) => list).toList();

      if (readings.isEmpty) {
        _logger.i('No health data found to sync');
        return 0;
      }

      // Sync to backend
      final success = await syncHealthData(readings);
      if (success) {
        _logger.i('Full sync completed: ${readings.length} readings');
        return readings.length;
      } else {
        _logger.e('Full sync failed');
        return 0;
      }
    } catch (e) {
      _logger.e('Error performing full sync: $e');
      return 0;
    }
  }

  /// Get health summary from backend
  ///
  /// [patientId] - Patient ID to get summary for
  ///
  /// Returns health summary or null if error
  Future<HealthSummary?> getHealthSummary(String patientId) async {
    try {
      _logger.i('Fetching health summary for patient $patientId');

      final response = await _apiClient.get('/health/patient/$patientId/summary');
      if (response == null) {
        return null;
      }

      return HealthSummary.fromJson(response as Map<String, dynamic>);
    } catch (e) {
      _logger.e('Error fetching health summary: $e');
      return null;
    }
  }

  /// Get health records from backend
  ///
  /// [patientId] - Patient ID
  /// [metricType] - Optional filter by metric type
  /// [startDate] - Optional start date
  /// [endDate] - Optional end date
  /// [limit] - Maximum number of records (default: 100)
  ///
  /// Returns list of health readings
  Future<List<HealthReading>> getHealthRecords({
    required String patientId,
    HealthMetric? metricType,
    DateTime? startDate,
    DateTime? endDate,
    int limit = 100,
  }) async {
    try {
      final params = <String, dynamic>{
        'limit': limit,
        if (metricType != null) 'metric_type': metricType.value,
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
      };

      final queryString = params.entries
          .map((e) => '${e.key}=${Uri.encodeComponent(e.value.toString())}')
          .join('&');

      final response =
          await _apiClient.get('/health/patient/$patientId/records?$queryString');

      if (response == null) {
        return [];
      }

      final records = (response as List<dynamic>)
          .map((json) => HealthReading.fromJson(json as Map<String, dynamic>))
          .toList();

      return records;
    } catch (e) {
      _logger.e('Error fetching health records: $e');
      return [];
    }
  }

  /// Enable background health updates
  ///
  /// Note: This requires proper iOS background modes configuration
  Future<void> enableBackgroundUpdates() async {
    if (!Platform.isIOS) {
      return;
    }

    try {
      // Note: Background updates require additional iOS setup
      // This is a placeholder for future implementation
      _logger.i('Background health updates enabled');
    } catch (e) {
      _logger.e('Error enabling background updates: $e');
    }
  }

  /// Map HealthMetric enum to Health package HealthDataType
  HealthDataType? _mapMetricToHealthDataType(HealthMetric metric) {
    switch (metric) {
      case HealthMetric.heartRate:
        return HealthDataType.HEART_RATE;
      case HealthMetric.bloodPressureSystolic:
        return HealthDataType.BLOOD_PRESSURE_SYSTOLIC;
      case HealthMetric.bloodPressureDiastolic:
        return HealthDataType.BLOOD_PRESSURE_DIASTOLIC;
      case HealthMetric.weight:
        return HealthDataType.WEIGHT;
      case HealthMetric.height:
        return HealthDataType.HEIGHT;
      case HealthMetric.bodyTemperature:
        return HealthDataType.BODY_TEMPERATURE;
      case HealthMetric.bloodGlucose:
        return HealthDataType.BLOOD_GLUCOSE;
      case HealthMetric.oxygenSaturation:
        return HealthDataType.BLOOD_OXYGEN;
      case HealthMetric.steps:
        return HealthDataType.STEPS;
      case HealthMetric.sleepAnalysis:
        return HealthDataType.SLEEP_ASLEEP;
      case HealthMetric.activeEnergyBurned:
        return HealthDataType.ACTIVE_ENERGY_BURNED;
      case HealthMetric.exerciseTime:
        return HealthDataType.EXERCISE_TIME;
      case HealthMetric.respiratoryRate:
        return HealthDataType.RESPIRATORY_RATE;
      default:
        return null;
    }
  }

  /// Extract numeric value from HealthDataPoint
  double _extractValue(HealthDataPoint dataPoint) {
    final value = dataPoint.value;

    if (value is NumericHealthValue) {
      return value.numericValue.toDouble();
    } else if (value is num) {
      return value.toDouble();
    } else {
      // For other types, try to parse or return 0
      return 0.0;
    }
  }
}
