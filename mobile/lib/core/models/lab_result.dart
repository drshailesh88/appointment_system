/// Lab result models

/// Lab order model
class LabOrder {
  final String id;
  final String patientId;
  final String doctorId;
  final String? appointmentId;
  final DateTime orderDate;
  final List<String> testsOrdered;
  final String priority;
  final String status;
  final String? clinicalNotes;
  final List<String>? diagnosisCodes;
  final DateTime? sampleCollectedAt;
  final DateTime? expectedCompletion;
  final String? labProvider;
  final String? labOrderId;
  final Map<String, dynamic>? metadata;

  // Enriched data
  final String? patientName;
  final String? doctorName;
  final int resultsCount;
  final int abnormalCount;

  final DateTime createdAt;
  final DateTime updatedAt;

  LabOrder({
    required this.id,
    required this.patientId,
    required this.doctorId,
    this.appointmentId,
    required this.orderDate,
    required this.testsOrdered,
    required this.priority,
    required this.status,
    this.clinicalNotes,
    this.diagnosisCodes,
    this.sampleCollectedAt,
    this.expectedCompletion,
    this.labProvider,
    this.labOrderId,
    this.metadata,
    this.patientName,
    this.doctorName,
    this.resultsCount = 0,
    this.abnormalCount = 0,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LabOrder.fromJson(Map<String, dynamic> json) {
    return LabOrder(
      id: json['id'],
      patientId: json['patient_id'],
      doctorId: json['doctor_id'],
      appointmentId: json['appointment_id'],
      orderDate: DateTime.parse(json['order_date']),
      testsOrdered: List<String>.from(json['tests_ordered'] ?? []),
      priority: json['priority'] ?? 'routine',
      status: json['status'] ?? 'ordered',
      clinicalNotes: json['clinical_notes'],
      diagnosisCodes: json['diagnosis_codes'] != null
          ? List<String>.from(json['diagnosis_codes'])
          : null,
      sampleCollectedAt: json['sample_collected_at'] != null
          ? DateTime.parse(json['sample_collected_at'])
          : null,
      expectedCompletion: json['expected_completion'] != null
          ? DateTime.parse(json['expected_completion'])
          : null,
      labProvider: json['lab_provider'],
      labOrderId: json['lab_order_id'],
      metadata: json['metadata'],
      patientName: json['patient_name'],
      doctorName: json['doctor_name'],
      resultsCount: json['results_count'] ?? 0,
      abnormalCount: json['abnormal_count'] ?? 0,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'patient_id': patientId,
      'doctor_id': doctorId,
      'appointment_id': appointmentId,
      'tests_ordered': testsOrdered,
      'priority': priority,
      'clinical_notes': clinicalNotes,
      'diagnosis_codes': diagnosisCodes,
      'expected_completion': expectedCompletion?.toIso8601String(),
      'lab_provider': labProvider,
    };
  }

  String get statusDisplay {
    switch (status) {
      case 'ordered':
        return 'Ordered';
      case 'sample_collected':
        return 'Sample Collected';
      case 'in_progress':
        return 'In Progress';
      case 'completed':
        return 'Completed';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  }

  String get priorityDisplay {
    switch (priority) {
      case 'routine':
        return 'Routine';
      case 'urgent':
        return 'Urgent';
      case 'stat':
        return 'STAT';
      default:
        return priority;
    }
  }

  bool get isCompleted => status == 'completed';
  bool get isPending => status != 'completed' && status != 'cancelled';
  bool get hasAbnormalResults => abnormalCount > 0;
}

/// Lab result model
class LabResult {
  final String id;
  final String orderId;
  final String testName;
  final String? testCode;
  final String? testCategory;
  final String value;
  final double? valueNumeric;
  final String? unit;
  final double? referenceRangeMin;
  final double? referenceRangeMax;
  final String? referenceRangeText;
  final bool isAbnormal;
  final String? abnormalFlag;
  final String status;
  final DateTime? resultDate;
  final String? notes;
  final String? performedBy;
  final String? methodology;
  final DateTime createdAt;
  final DateTime updatedAt;

  LabResult({
    required this.id,
    required this.orderId,
    required this.testName,
    this.testCode,
    this.testCategory,
    required this.value,
    this.valueNumeric,
    this.unit,
    this.referenceRangeMin,
    this.referenceRangeMax,
    this.referenceRangeText,
    required this.isAbnormal,
    this.abnormalFlag,
    required this.status,
    this.resultDate,
    this.notes,
    this.performedBy,
    this.methodology,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LabResult.fromJson(Map<String, dynamic> json) {
    return LabResult(
      id: json['id'],
      orderId: json['order_id'],
      testName: json['test_name'],
      testCode: json['test_code'],
      testCategory: json['test_category'],
      value: json['value'],
      valueNumeric: json['value_numeric']?.toDouble(),
      unit: json['unit'],
      referenceRangeMin: json['reference_range_min']?.toDouble(),
      referenceRangeMax: json['reference_range_max']?.toDouble(),
      referenceRangeText: json['reference_range_text'],
      isAbnormal: json['is_abnormal'] ?? false,
      abnormalFlag: json['abnormal_flag'],
      status: json['status'] ?? 'final',
      resultDate: json['result_date'] != null
          ? DateTime.parse(json['result_date'])
          : null,
      notes: json['notes'],
      performedBy: json['performed_by'],
      methodology: json['methodology'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  String get displayValue {
    if (unit != null) {
      return '$value $unit';
    }
    return value;
  }

  String get referenceRangeDisplay {
    if (referenceRangeText != null && referenceRangeText!.isNotEmpty) {
      return referenceRangeText!;
    }
    if (referenceRangeMin != null && referenceRangeMax != null) {
      return '$referenceRangeMin - $referenceRangeMax${unit != null ? ' $unit' : ''}';
    }
    if (referenceRangeMax != null) {
      return '< $referenceRangeMax${unit != null ? ' $unit' : ''}';
    }
    if (referenceRangeMin != null) {
      return '> $referenceRangeMin${unit != null ? ' $unit' : ''}';
    }
    return 'N/A';
  }

  bool get isHigh => abnormalFlag == 'H' || abnormalFlag == 'HH';
  bool get isLow => abnormalFlag == 'L' || abnormalFlag == 'LL';
  bool get isCritical => abnormalFlag == 'HH' || abnormalFlag == 'LL';
}

/// Lab result trend data point
class LabResultTrendPoint {
  final DateTime date;
  final double value;
  final bool isAbnormal;

  LabResultTrendPoint({
    required this.date,
    required this.value,
    required this.isAbnormal,
  });

  factory LabResultTrendPoint.fromJson(Map<String, dynamic> json) {
    return LabResultTrendPoint(
      date: DateTime.parse(json['date']),
      value: json['value'].toDouble(),
      isAbnormal: json['is_abnormal'] ?? false,
    );
  }
}

/// Lab result trend response
class LabResultTrend {
  final String testName;
  final String? unit;
  final double? referenceRangeMin;
  final double? referenceRangeMax;
  final List<LabResultTrendPoint> dataPoints;

  LabResultTrend({
    required this.testName,
    this.unit,
    this.referenceRangeMin,
    this.referenceRangeMax,
    required this.dataPoints,
  });

  factory LabResultTrend.fromJson(Map<String, dynamic> json) {
    return LabResultTrend(
      testName: json['test_name'],
      unit: json['unit'],
      referenceRangeMin: json['reference_range_min']?.toDouble(),
      referenceRangeMax: json['reference_range_max']?.toDouble(),
      dataPoints: (json['data_points'] as List)
          .map((point) => LabResultTrendPoint.fromJson(point))
          .toList(),
    );
  }
}

/// Lab report model
class LabReport {
  final String id;
  final String orderId;
  final String reportType;
  final String? filePath;
  final String? fileUrl;
  final int? fileSize;
  final String? mimeType;
  final Map<String, dynamic>? parsedData;
  final DateTime receivedAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  LabReport({
    required this.id,
    required this.orderId,
    required this.reportType,
    this.filePath,
    this.fileUrl,
    this.fileSize,
    this.mimeType,
    this.parsedData,
    required this.receivedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  factory LabReport.fromJson(Map<String, dynamic> json) {
    return LabReport(
      id: json['id'],
      orderId: json['order_id'],
      reportType: json['report_type'],
      filePath: json['file_path'],
      fileUrl: json['file_url'],
      fileSize: json['file_size'],
      mimeType: json['mime_type'],
      parsedData: json['parsed_data'],
      receivedAt: DateTime.parse(json['received_at']),
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

/// Lab statistics model
class LabStatistics {
  final int totalOrders;
  final int pendingOrders;
  final int completedOrders;
  final int totalResults;
  final int abnormalResults;
  final List<Map<String, dynamic>> mostOrderedTests;
  final double? averageTurnaroundHours;

  LabStatistics({
    required this.totalOrders,
    required this.pendingOrders,
    required this.completedOrders,
    required this.totalResults,
    required this.abnormalResults,
    required this.mostOrderedTests,
    this.averageTurnaroundHours,
  });

  factory LabStatistics.fromJson(Map<String, dynamic> json) {
    return LabStatistics(
      totalOrders: json['total_orders'] ?? 0,
      pendingOrders: json['pending_orders'] ?? 0,
      completedOrders: json['completed_orders'] ?? 0,
      totalResults: json['total_results'] ?? 0,
      abnormalResults: json['abnormal_results'] ?? 0,
      mostOrderedTests: List<Map<String, dynamic>>.from(
        json['most_ordered_tests'] ?? [],
      ),
      averageTurnaroundHours: json['average_turnaround_hours']?.toDouble(),
    );
  }
}
