/// No-show prediction model
///
/// Represents ML-powered prediction of appointment no-show likelihood
/// with risk categorization and mitigation recommendations.
class NoShowPrediction {
  final String id;
  final String appointmentId;
  final double probability;
  final String riskLevel;
  final int riskPercentage;
  final Map<String, dynamic> featuresUsed;
  final String modelVersion;
  final DateTime predictedAt;
  final Map<String, dynamic>? mitigationActions;
  final bool? wasAccurate;
  final String? actualOutcome;
  final DateTime createdAt;
  final DateTime updatedAt;

  NoShowPrediction({
    required this.id,
    required this.appointmentId,
    required this.probability,
    required this.riskLevel,
    required this.riskPercentage,
    required this.featuresUsed,
    required this.modelVersion,
    required this.predictedAt,
    this.mitigationActions,
    this.wasAccurate,
    this.actualOutcome,
    required this.createdAt,
    required this.updatedAt,
  });

  factory NoShowPrediction.fromJson(Map<String, dynamic> json) {
    return NoShowPrediction(
      id: json['id'],
      appointmentId: json['appointment_id'],
      probability: (json['probability'] as num).toDouble(),
      riskLevel: json['risk_level'],
      riskPercentage: json['risk_percentage'],
      featuresUsed: Map<String, dynamic>.from(json['features_used']),
      modelVersion: json['model_version'],
      predictedAt: DateTime.parse(json['predicted_at']),
      mitigationActions: json['mitigation_actions'] != null
          ? Map<String, dynamic>.from(json['mitigation_actions'])
          : null,
      wasAccurate: json['was_accurate'],
      actualOutcome: json['actual_outcome'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'appointment_id': appointmentId,
      'probability': probability,
      'risk_level': riskLevel,
      'risk_percentage': riskPercentage,
      'features_used': featuresUsed,
      'model_version': modelVersion,
      'predicted_at': predictedAt.toIso8601String(),
      'mitigation_actions': mitigationActions,
      'was_accurate': wasAccurate,
      'actual_outcome': actualOutcome,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// Check if this is a high-risk prediction
  bool get isHighRisk => riskLevel == 'high';

  /// Check if this is a medium-risk prediction
  bool get isMediumRisk => riskLevel == 'medium';

  /// Check if this is a low-risk prediction
  bool get isLowRisk => riskLevel == 'low';

  /// Get recommended actions list
  List<MitigationAction> get recommendedActions {
    if (mitigationActions == null ||
        !mitigationActions!.containsKey('actions')) {
      return [];
    }

    final actionsList = mitigationActions!['actions'] as List<dynamic>;
    return actionsList
        .map((json) => MitigationAction.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  /// Get overbooking factor recommendation
  double get overbookingFactor {
    if (mitigationActions == null ||
        !mitigationActions!.containsKey('overbooking_factor')) {
      return 1.0;
    }
    return (mitigationActions!['overbooking_factor'] as num).toDouble();
  }

  /// Get number of recommended reminders
  int get recommendedReminderCount {
    if (mitigationActions == null ||
        !mitigationActions!.containsKey('recommended_reminder_count')) {
      return 1;
    }
    return mitigationActions!['recommended_reminder_count'] as int;
  }
}

/// Mitigation action recommendation
class MitigationAction {
  final String action;
  final String description;
  final String priority;

  MitigationAction({
    required this.action,
    required this.description,
    required this.priority,
  });

  factory MitigationAction.fromJson(Map<String, dynamic> json) {
    return MitigationAction(
      action: json['action'],
      description: json['description'],
      priority: json['priority'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'action': action,
      'description': description,
      'priority': priority,
    };
  }

  /// Check if this is a high-priority action
  bool get isHighPriority => priority == 'high';

  /// Check if this is a medium-priority action
  bool get isMediumPriority => priority == 'medium';

  /// Check if this is a low-priority action
  bool get isLowPriority => priority == 'low';
}

/// High-risk appointment list item
class HighRiskAppointment {
  final String appointmentId;
  final String patientId;
  final String patientName;
  final String doctorId;
  final String doctorName;
  final DateTime scheduledStart;
  final double probability;
  final int riskPercentage;
  final Map<String, dynamic>? mitigationActions;

  HighRiskAppointment({
    required this.appointmentId,
    required this.patientId,
    required this.patientName,
    required this.doctorId,
    required this.doctorName,
    required this.scheduledStart,
    required this.probability,
    required this.riskPercentage,
    this.mitigationActions,
  });

  factory HighRiskAppointment.fromJson(Map<String, dynamic> json) {
    return HighRiskAppointment(
      appointmentId: json['appointment_id'],
      patientId: json['patient_id'],
      patientName: json['patient_name'],
      doctorId: json['doctor_id'],
      doctorName: json['doctor_name'],
      scheduledStart: DateTime.parse(json['scheduled_start']),
      probability: (json['probability'] as num).toDouble(),
      riskPercentage: json['risk_percentage'],
      mitigationActions: json['mitigation_actions'] != null
          ? Map<String, dynamic>.from(json['mitigation_actions'])
          : null,
    );
  }

  /// Get recommended actions list
  List<MitigationAction> get recommendedActions {
    if (mitigationActions == null ||
        !mitigationActions!.containsKey('actions')) {
      return [];
    }

    final actionsList = mitigationActions!['actions'] as List<dynamic>;
    return actionsList
        .map((json) => MitigationAction.fromJson(json as Map<String, dynamic>))
        .toList();
  }
}

/// Model performance statistics
class ModelStats {
  final String modelVersion;
  final int totalPredictions;
  final int accuratePredictions;
  final double accuracy;
  final bool hasTrainedModel;
  final Map<String, int> riskDistribution;

  ModelStats({
    required this.modelVersion,
    required this.totalPredictions,
    required this.accuratePredictions,
    required this.accuracy,
    required this.hasTrainedModel,
    required this.riskDistribution,
  });

  factory ModelStats.fromJson(Map<String, dynamic> json) {
    return ModelStats(
      modelVersion: json['model_version'],
      totalPredictions: json['total_predictions'],
      accuratePredictions: json['accurate_predictions'],
      accuracy: (json['accuracy'] as num).toDouble(),
      hasTrainedModel: json['has_trained_model'],
      riskDistribution: Map<String, int>.from(json['risk_distribution']),
    );
  }

  /// Get accuracy as percentage
  int get accuracyPercentage => (accuracy * 100).round();
}
