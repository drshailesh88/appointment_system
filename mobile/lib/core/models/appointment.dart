/// Appointment model
class Appointment {
  final String id;
  final String patientId;
  final String patientName;
  final String doctorId;
  final String doctorName;
  final DateTime scheduledStart;
  final DateTime? scheduledEnd;
  final int durationMinutes;
  final String status;
  final String appointmentType;
  final String bookingSource;
  final String? chiefComplaint;
  final String? notes;
  final int? tokenNumber;
  final DateTime? checkInTime;
  final DateTime? startTime;
  final DateTime? endTime;

  Appointment({
    required this.id,
    required this.patientId,
    required this.patientName,
    required this.doctorId,
    required this.doctorName,
    required this.scheduledStart,
    this.scheduledEnd,
    required this.durationMinutes,
    required this.status,
    required this.appointmentType,
    required this.bookingSource,
    this.chiefComplaint,
    this.notes,
    this.tokenNumber,
    this.checkInTime,
    this.startTime,
    this.endTime,
  });

  factory Appointment.fromJson(Map<String, dynamic> json) {
    return Appointment(
      id: json['id'],
      patientId: json['patient_id'],
      patientName: json['patient_name'] ?? 'Unknown',
      doctorId: json['doctor_id'],
      doctorName: json['doctor_name'] ?? 'Unknown',
      scheduledStart: DateTime.parse(json['scheduled_start']),
      scheduledEnd: json['scheduled_end'] != null
          ? DateTime.parse(json['scheduled_end'])
          : null,
      durationMinutes: json['duration_minutes'] ?? 15,
      status: json['status'] ?? 'scheduled',
      appointmentType: json['appointment_type'] ?? 'new_consultation',
      bookingSource: json['booking_source'] ?? 'walk_in',
      chiefComplaint: json['chief_complaint'],
      notes: json['notes'],
      tokenNumber: json['token_number'],
      checkInTime: json['check_in_time'] != null
          ? DateTime.parse(json['check_in_time'])
          : null,
      startTime: json['start_time'] != null
          ? DateTime.parse(json['start_time'])
          : null,
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'patient_id': patientId,
      'doctor_id': doctorId,
      'scheduled_start': scheduledStart.toIso8601String(),
      'duration_minutes': durationMinutes,
      'appointment_type': appointmentType,
      'booking_source': bookingSource,
      'chief_complaint': chiefComplaint,
      'notes': notes,
    };
  }

  bool get isScheduled => status == 'scheduled';
  bool get isCheckedIn => status == 'checked_in';
  bool get isInProgress => status == 'in_progress';
  bool get isCompleted => status == 'completed';
  bool get isCancelled => status == 'cancelled';

  String get statusDisplay {
    switch (status) {
      case 'scheduled':
        return 'Scheduled';
      case 'confirmed':
        return 'Confirmed';
      case 'checked_in':
        return 'Checked In';
      case 'in_progress':
        return 'In Progress';
      case 'completed':
        return 'Completed';
      case 'cancelled':
        return 'Cancelled';
      case 'no_show':
        return 'No Show';
      default:
        return status;
    }
  }

  String get typeDisplay {
    switch (appointmentType) {
      case 'new_consultation':
        return 'New';
      case 'follow_up':
        return 'Follow-up';
      case 'procedure':
        return 'Procedure';
      case 'emergency':
        return 'Emergency';
      case 'teleconsultation':
        return 'Tele';
      default:
        return appointmentType;
    }
  }
}
