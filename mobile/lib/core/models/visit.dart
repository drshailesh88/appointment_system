/// Visit model from EMR
class Visit {
  final String id;
  final String patientId;
  final String? appointmentId;
  final String doctorId;
  final DateTime visitDate;
  final String chiefComplaint;
  final String? diagnosis;
  final String? prescriptionSummary;
  final String? notes;
  final List<String>? vitalSigns;
  final double? billedAmount;
  final String? invoiceId;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Nested data
  final String? patientName;
  final String? doctorName;

  Visit({
    required this.id,
    required this.patientId,
    this.appointmentId,
    required this.doctorId,
    required this.visitDate,
    required this.chiefComplaint,
    this.diagnosis,
    this.prescriptionSummary,
    this.notes,
    this.vitalSigns,
    this.billedAmount,
    this.invoiceId,
    required this.createdAt,
    required this.updatedAt,
    this.patientName,
    this.doctorName,
  });

  factory Visit.fromJson(Map<String, dynamic> json) {
    return Visit(
      id: json['id'] as String,
      patientId: json['patient_id'] as String,
      appointmentId: json['appointment_id'] as String?,
      doctorId: json['doctor_id'] as String,
      visitDate: DateTime.parse(json['visit_date'] as String),
      chiefComplaint: json['chief_complaint'] as String,
      diagnosis: json['diagnosis'] as String?,
      prescriptionSummary: json['prescription_summary'] as String?,
      notes: json['notes'] as String?,
      vitalSigns: json['vital_signs'] != null
          ? List<String>.from(json['vital_signs'] as List)
          : null,
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
      'appointment_id': appointmentId,
      'doctor_id': doctorId,
      'visit_date': visitDate.toIso8601String(),
      'chief_complaint': chiefComplaint,
      'diagnosis': diagnosis,
      'prescription_summary': prescriptionSummary,
      'notes': notes,
      'vital_signs': vitalSigns,
      'billed_amount': billedAmount,
      'invoice_id': invoiceId,
    };
  }
}
