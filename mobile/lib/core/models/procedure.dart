/// Procedure model for tracking medical procedures
///
/// Phase 9: Procedure & Intervention Tracking
class Procedure {
  final String id;
  final String patientId;
  final String doctorId;
  final String? appointmentId;
  final String clinicId;
  final String category; // Cardiology, Orthopedics, etc.
  final String procedureType; // Echo, Stent, Surgery
  final String? subType;
  final DateTime procedureDate;
  final Map<String, dynamic>? consumables;
  final Map<String, dynamic>? customFields;
  final String? icdCode;
  final String? cptCode;
  final String outcome; // successful, partial, failed, referred
  final String? notes;
  final double? billedAmount;
  final String? invoiceId;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Nested data
  final String? patientName;
  final String? doctorName;

  Procedure({
    required this.id,
    required this.patientId,
    required this.doctorId,
    this.appointmentId,
    required this.clinicId,
    required this.category,
    required this.procedureType,
    this.subType,
    required this.procedureDate,
    this.consumables,
    this.customFields,
    this.icdCode,
    this.cptCode,
    required this.outcome,
    this.notes,
    this.billedAmount,
    this.invoiceId,
    required this.createdAt,
    required this.updatedAt,
    this.patientName,
    this.doctorName,
  });

  factory Procedure.fromJson(Map<String, dynamic> json) {
    return Procedure(
      id: json['id'] as String,
      patientId: json['patient_id'] as String,
      doctorId: json['doctor_id'] as String,
      appointmentId: json['appointment_id'] as String?,
      clinicId: json['clinic_id'] as String,
      category: json['category'] as String,
      procedureType: json['procedure_type'] as String,
      subType: json['sub_type'] as String?,
      procedureDate: DateTime.parse(json['procedure_date'] as String),
      consumables: json['consumables'] as Map<String, dynamic>?,
      customFields: json['custom_fields'] as Map<String, dynamic>?,
      icdCode: json['icd_code'] as String?,
      cptCode: json['cpt_code'] as String?,
      outcome: json['outcome'] as String,
      notes: json['notes'] as String?,
      billedAmount: json['billed_amount'] != null
          ? (json['billed_amount'] as num).toDouble()
          : null,
      invoiceId: json['invoice_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      patientName: json['patient_name'] as String?,
      doctorName: json['doctor_name'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'patient_id': patientId,
      'doctor_id': doctorId,
      'appointment_id': appointmentId,
      'clinic_id': clinicId,
      'category': category,
      'procedure_type': procedureType,
      'sub_type': subType,
      'procedure_date': procedureDate.toIso8601String().split('T')[0],
      'consumables': consumables,
      'custom_fields': customFields,
      'icd_code': icdCode,
      'cpt_code': cptCode,
      'outcome': outcome,
      'notes': notes,
      'billed_amount': billedAmount,
      'invoice_id': invoiceId,
    };
  }
}

/// Procedure statistics
class ProcedureStats {
  final int totalProcedures;
  final int successfulCount;
  final int partialCount;
  final int failedCount;
  final int referredCount;
  final double totalBilled;
  final double successRate;

  ProcedureStats({
    required this.totalProcedures,
    required this.successfulCount,
    required this.partialCount,
    required this.failedCount,
    required this.referredCount,
    required this.totalBilled,
    required this.successRate,
  });

  factory ProcedureStats.fromJson(Map<String, dynamic> json) {
    return ProcedureStats(
      totalProcedures: json['total_procedures'] as int,
      successfulCount: json['successful_count'] as int,
      partialCount: json['partial_count'] as int,
      failedCount: json['failed_count'] as int,
      referredCount: json['referred_count'] as int,
      totalBilled: (json['total_billed'] as num).toDouble(),
      successRate: (json['success_rate'] as num).toDouble(),
    );
  }
}

/// Procedure type count for analytics
class ProcedureTypeCount {
  final String category;
  final String procedureType;
  final int count;
  final double totalBilled;

  ProcedureTypeCount({
    required this.category,
    required this.procedureType,
    required this.count,
    required this.totalBilled,
  });

  factory ProcedureTypeCount.fromJson(Map<String, dynamic> json) {
    return ProcedureTypeCount(
      category: json['category'] as String,
      procedureType: json['procedure_type'] as String,
      count: json['count'] as int,
      totalBilled: (json['total_billed'] as num).toDouble(),
    );
  }
}

/// Procedure template for quick logging
class ProcedureTemplate {
  final String category;
  final List<String> types;
  final List<String> subtypes;
  final List<String> commonConsumables;

  ProcedureTemplate({
    required this.category,
    required this.types,
    required this.subtypes,
    required this.commonConsumables,
  });

  factory ProcedureTemplate.fromJson(Map<String, dynamic> json) {
    return ProcedureTemplate(
      category: json['category'] as String,
      types: List<String>.from(json['types'] as List),
      subtypes: List<String>.from(json['subtypes'] as List),
      commonConsumables: List<String>.from(json['common_consumables'] as List),
    );
  }
}
