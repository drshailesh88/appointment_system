/// Timeline event types
enum TimelineEventType {
  appointment,
  visit,
  procedure,
  document,
}

/// Timeline event model for patient history
class TimelineEvent {
  final String id;
  final String patientId;
  final TimelineEventType type;
  final DateTime date;
  final String title;
  final String? subtitle;
  final String? description;
  final String? doctorName;
  final String? status;
  final Map<String, dynamic>? metadata;

  TimelineEvent({
    required this.id,
    required this.patientId,
    required this.type,
    required this.date,
    required this.title,
    this.subtitle,
    this.description,
    this.doctorName,
    this.status,
    this.metadata,
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> json) {
    return TimelineEvent(
      id: json['id'] as String,
      patientId: json['patient_id'] as String,
      type: _parseEventType(json['type'] as String),
      date: DateTime.parse(json['date'] as String),
      title: json['title'] as String,
      subtitle: json['subtitle'] as String?,
      description: json['description'] as String?,
      doctorName: json['doctor_name'] as String?,
      status: json['status'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  static TimelineEventType _parseEventType(String type) {
    switch (type.toLowerCase()) {
      case 'appointment':
        return TimelineEventType.appointment;
      case 'visit':
        return TimelineEventType.visit;
      case 'procedure':
        return TimelineEventType.procedure;
      case 'document':
        return TimelineEventType.document;
      default:
        return TimelineEventType.appointment;
    }
  }

  String get typeDisplay {
    switch (type) {
      case TimelineEventType.appointment:
        return 'Appointment';
      case TimelineEventType.visit:
        return 'Visit';
      case TimelineEventType.procedure:
        return 'Procedure';
      case TimelineEventType.document:
        return 'Document';
    }
  }

  String get typeIcon {
    switch (type) {
      case TimelineEventType.appointment:
        return '📅';
      case TimelineEventType.visit:
        return '🏥';
      case TimelineEventType.procedure:
        return '⚕️';
      case TimelineEventType.document:
        return '📄';
    }
  }
}
