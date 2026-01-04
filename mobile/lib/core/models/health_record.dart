/// Health record models for Apple Health integration
///
/// Represents health data synced from Apple Health including
/// heart rate, blood pressure, weight, steps, sleep, and more.

/// Enum for different health metric types
enum HealthMetric {
  heartRate('heart_rate', 'Heart Rate', 'bpm'),
  bloodPressureSystolic('blood_pressure_systolic', 'Blood Pressure (Systolic)', 'mmHg'),
  bloodPressureDiastolic('blood_pressure_diastolic', 'Blood Pressure (Diastolic)', 'mmHg'),
  weight('weight', 'Weight', 'kg'),
  height('height', 'Height', 'cm'),
  bodyTemperature('body_temperature', 'Body Temperature', '°C'),
  bloodGlucose('blood_glucose', 'Blood Glucose', 'mg/dL'),
  oxygenSaturation('oxygen_saturation', 'Oxygen Saturation', '%'),
  steps('steps', 'Steps', 'steps'),
  sleepAnalysis('sleep_analysis', 'Sleep', 'hours'),
  activeEnergyBurned('active_energy_burned', 'Active Energy', 'kcal'),
  exerciseTime('exercise_time', 'Exercise Time', 'minutes'),
  respiratoryRate('respiratory_rate', 'Respiratory Rate', 'breaths/min');

  final String value;
  final String displayName;
  final String unit;

  const HealthMetric(this.value, this.displayName, this.unit);

  /// Get HealthMetric from string value
  static HealthMetric fromString(String value) {
    return HealthMetric.values.firstWhere(
      (metric) => metric.value == value,
      orElse: () => HealthMetric.heartRate,
    );
  }
}

/// Represents a single health reading
class HealthReading {
  final String id;
  final String patientId;
  final HealthMetric metricType;
  final double value;
  final String unit;
  final DateTime recordedAt;
  final String source;
  final String? deviceId;
  final Map<String, dynamic>? metadata;

  HealthReading({
    required this.id,
    required this.patientId,
    required this.metricType,
    required this.value,
    required this.unit,
    required this.recordedAt,
    this.source = 'Apple Health',
    this.deviceId,
    this.metadata,
  });

  factory HealthReading.fromJson(Map<String, dynamic> json) {
    return HealthReading(
      id: json['id'],
      patientId: json['patient_id'],
      metricType: HealthMetric.fromString(json['metric_type']),
      value: (json['value'] as num).toDouble(),
      unit: json['unit'],
      recordedAt: DateTime.parse(json['recorded_at']),
      source: json['source'] ?? 'Apple Health',
      deviceId: json['device_id'],
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'patient_id': patientId,
      'metric_type': metricType.value,
      'value': value,
      'unit': unit,
      'recorded_at': recordedAt.toIso8601String(),
      'source': source,
      if (deviceId != null) 'device_id': deviceId,
      if (metadata != null) 'metadata': metadata,
    };
  }

  /// Get formatted value with unit
  String get formattedValue => '${value.toStringAsFixed(1)} $unit';

  /// Check if reading is recent (within last 24 hours)
  bool get isRecent {
    final now = DateTime.now();
    final difference = now.difference(recordedAt);
    return difference.inHours < 24;
  }

  /// Check if reading is abnormal (basic thresholds)
  bool get isAbnormal {
    switch (metricType) {
      case HealthMetric.heartRate:
        return value < 60 || value > 100;
      case HealthMetric.bloodPressureSystolic:
        return value < 90 || value > 140;
      case HealthMetric.bloodPressureDiastolic:
        return value < 60 || value > 90;
      case HealthMetric.oxygenSaturation:
        return value < 95;
      case HealthMetric.bloodGlucose:
        return value < 70 || value > 140;
      case HealthMetric.bodyTemperature:
        return value < 36.1 || value > 37.2;
      default:
        return false;
    }
  }
}

/// Summary of health data for a patient
class HealthSummary {
  final String patientId;
  final HealthReading? latestHeartRate;
  final HealthReading? latestBloodPressureSystolic;
  final HealthReading? latestBloodPressureDiastolic;
  final HealthReading? latestWeight;
  final HealthReading? latestOxygenSaturation;
  final HealthReading? latestBloodGlucose;
  final int? todaySteps;
  final double? todaySleepHours;
  final DateTime? lastSyncedAt;
  final int totalReadings;

  HealthSummary({
    required this.patientId,
    this.latestHeartRate,
    this.latestBloodPressureSystolic,
    this.latestBloodPressureDiastolic,
    this.latestWeight,
    this.latestOxygenSaturation,
    this.latestBloodGlucose,
    this.todaySteps,
    this.todaySleepHours,
    this.lastSyncedAt,
    this.totalReadings = 0,
  });

  factory HealthSummary.fromJson(Map<String, dynamic> json) {
    return HealthSummary(
      patientId: json['patient_id'],
      latestHeartRate: json['latest_heart_rate'] != null
          ? HealthReading.fromJson(json['latest_heart_rate'])
          : null,
      latestBloodPressureSystolic: json['latest_blood_pressure_systolic'] != null
          ? HealthReading.fromJson(json['latest_blood_pressure_systolic'])
          : null,
      latestBloodPressureDiastolic: json['latest_blood_pressure_diastolic'] != null
          ? HealthReading.fromJson(json['latest_blood_pressure_diastolic'])
          : null,
      latestWeight: json['latest_weight'] != null
          ? HealthReading.fromJson(json['latest_weight'])
          : null,
      latestOxygenSaturation: json['latest_oxygen_saturation'] != null
          ? HealthReading.fromJson(json['latest_oxygen_saturation'])
          : null,
      latestBloodGlucose: json['latest_blood_glucose'] != null
          ? HealthReading.fromJson(json['latest_blood_glucose'])
          : null,
      todaySteps: json['today_steps'] as int?,
      todaySleepHours: json['today_sleep_hours'] != null
          ? (json['today_sleep_hours'] as num).toDouble()
          : null,
      lastSyncedAt: json['last_synced_at'] != null
          ? DateTime.parse(json['last_synced_at'])
          : null,
      totalReadings: json['total_readings'] ?? 0,
    );
  }

  /// Get blood pressure as a formatted string (Systolic/Diastolic)
  String? get bloodPressure {
    if (latestBloodPressureSystolic != null && latestBloodPressureDiastolic != null) {
      return '${latestBloodPressureSystolic!.value.toInt()}/${latestBloodPressureDiastolic!.value.toInt()} mmHg';
    }
    return null;
  }

  /// Check if any vital signs are abnormal
  bool get hasAbnormalVitals {
    return [
      latestHeartRate,
      latestBloodPressureSystolic,
      latestBloodPressureDiastolic,
      latestOxygenSaturation,
      latestBloodGlucose,
    ].any((reading) => reading?.isAbnormal ?? false);
  }

  /// Check if data is stale (last sync > 24 hours ago)
  bool get isStale {
    if (lastSyncedAt == null) return true;
    final now = DateTime.now();
    final difference = now.difference(lastSyncedAt!);
    return difference.inHours > 24;
  }
}

/// Health connection state
enum HealthConnectionStatus {
  disconnected,
  connecting,
  connected,
  error,
  permissionDenied,
}

/// Health permissions state
class HealthPermissions {
  final bool heartRate;
  final bool bloodPressure;
  final bool weight;
  final bool steps;
  final bool sleep;
  final bool oxygenSaturation;
  final bool bloodGlucose;
  final bool bodyTemperature;

  const HealthPermissions({
    this.heartRate = false,
    this.bloodPressure = false,
    this.weight = false,
    this.steps = false,
    this.sleep = false,
    this.oxygenSaturation = false,
    this.bloodGlucose = false,
    this.bodyTemperature = false,
  });

  factory HealthPermissions.fromJson(Map<String, dynamic> json) {
    return HealthPermissions(
      heartRate: json['heart_rate'] ?? false,
      bloodPressure: json['blood_pressure'] ?? false,
      weight: json['weight'] ?? false,
      steps: json['steps'] ?? false,
      sleep: json['sleep'] ?? false,
      oxygenSaturation: json['oxygen_saturation'] ?? false,
      bloodGlucose: json['blood_glucose'] ?? false,
      bodyTemperature: json['body_temperature'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'heart_rate': heartRate,
      'blood_pressure': bloodPressure,
      'weight': weight,
      'steps': steps,
      'sleep': sleep,
      'oxygen_saturation': oxygenSaturation,
      'blood_glucose': bloodGlucose,
      'body_temperature': bodyTemperature,
    };
  }

  /// Check if all permissions are granted
  bool get allGranted {
    return heartRate &&
        bloodPressure &&
        weight &&
        steps &&
        sleep &&
        oxygenSaturation &&
        bloodGlucose &&
        bodyTemperature;
  }

  /// Get count of granted permissions
  int get grantedCount {
    int count = 0;
    if (heartRate) count++;
    if (bloodPressure) count++;
    if (weight) count++;
    if (steps) count++;
    if (sleep) count++;
    if (oxygenSaturation) count++;
    if (bloodGlucose) count++;
    if (bodyTemperature) count++;
    return count;
  }

  HealthPermissions copyWith({
    bool? heartRate,
    bool? bloodPressure,
    bool? weight,
    bool? steps,
    bool? sleep,
    bool? oxygenSaturation,
    bool? bloodGlucose,
    bool? bodyTemperature,
  }) {
    return HealthPermissions(
      heartRate: heartRate ?? this.heartRate,
      bloodPressure: bloodPressure ?? this.bloodPressure,
      weight: weight ?? this.weight,
      steps: steps ?? this.steps,
      sleep: sleep ?? this.sleep,
      oxygenSaturation: oxygenSaturation ?? this.oxygenSaturation,
      bloodGlucose: bloodGlucose ?? this.bloodGlucose,
      bodyTemperature: bodyTemperature ?? this.bodyTemperature,
    );
  }
}
