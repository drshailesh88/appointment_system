/// Consultation model for video consultations
class Consultation {
  final String id;
  final String appointmentId;
  final String roomName;
  final String? roomUrl;
  final String status;
  final DateTime? scheduledStart;
  final DateTime? patientJoinedAt;
  final DateTime? doctorJoinedAt;
  final DateTime? startedAt;
  final DateTime? endedAt;
  final int? durationMinutes;
  final bool recordingConsent;
  final String? recordingUrl;
  final int? patientRating;
  final int? doctorRating;
  final String? connectionQuality;
  final DateTime createdAt;
  final DateTime updatedAt;

  Consultation({
    required this.id,
    required this.appointmentId,
    required this.roomName,
    this.roomUrl,
    required this.status,
    this.scheduledStart,
    this.patientJoinedAt,
    this.doctorJoinedAt,
    this.startedAt,
    this.endedAt,
    this.durationMinutes,
    required this.recordingConsent,
    this.recordingUrl,
    this.patientRating,
    this.doctorRating,
    this.connectionQuality,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Consultation.fromJson(Map<String, dynamic> json) {
    return Consultation(
      id: json['id'],
      appointmentId: json['appointment_id'],
      roomName: json['room_name'],
      roomUrl: json['room_url'],
      status: json['status'],
      scheduledStart: json['scheduled_start'] != null
          ? DateTime.parse(json['scheduled_start'])
          : null,
      patientJoinedAt: json['patient_joined_at'] != null
          ? DateTime.parse(json['patient_joined_at'])
          : null,
      doctorJoinedAt: json['doctor_joined_at'] != null
          ? DateTime.parse(json['doctor_joined_at'])
          : null,
      startedAt: json['started_at'] != null
          ? DateTime.parse(json['started_at'])
          : null,
      endedAt:
          json['ended_at'] != null ? DateTime.parse(json['ended_at']) : null,
      durationMinutes: json['duration_minutes'],
      recordingConsent: json['recording_consent'] ?? false,
      recordingUrl: json['recording_url'],
      patientRating: json['patient_rating'],
      doctorRating: json['doctor_rating'],
      connectionQuality: json['connection_quality'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'appointment_id': appointmentId,
      'room_name': roomName,
      'room_url': roomUrl,
      'status': status,
      'scheduled_start': scheduledStart?.toIso8601String(),
      'patient_joined_at': patientJoinedAt?.toIso8601String(),
      'doctor_joined_at': doctorJoinedAt?.toIso8601String(),
      'started_at': startedAt?.toIso8601String(),
      'ended_at': endedAt?.toIso8601String(),
      'duration_minutes': durationMinutes,
      'recording_consent': recordingConsent,
      'recording_url': recordingUrl,
      'patient_rating': patientRating,
      'doctor_rating': doctorRating,
      'connection_quality': connectionQuality,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  int? get waitTimeMinutes {
    if (patientJoinedAt != null && startedAt != null) {
      return startedAt!.difference(patientJoinedAt!).inMinutes;
    }
    return null;
  }

  bool get isWaiting => status == 'waiting';
  bool get isInProgress => status == 'in_progress';
  bool get isCompleted => status == 'completed';
}

/// Join room response model
class JoinRoomResponse {
  final String roomUrl;
  final String jwtToken;
  final String roomName;
  final String consultationId;
  final String role;

  JoinRoomResponse({
    required this.roomUrl,
    required this.jwtToken,
    required this.roomName,
    required this.consultationId,
    required this.role,
  });

  factory JoinRoomResponse.fromJson(Map<String, dynamic> json) {
    return JoinRoomResponse(
      roomUrl: json['room_url'],
      jwtToken: json['jwt_token'],
      roomName: json['room_name'],
      consultationId: json['consultation_id'],
      role: json['role'],
    );
  }
}

/// Waiting room status model
class WaitingRoomStatus {
  final String status;
  final int? position;
  final int? estimatedWaitMinutes;
  final DateTime? patientJoinedAt;

  WaitingRoomStatus({
    required this.status,
    this.position,
    this.estimatedWaitMinutes,
    this.patientJoinedAt,
  });

  factory WaitingRoomStatus.fromJson(Map<String, dynamic> json) {
    return WaitingRoomStatus(
      status: json['status'],
      position: json['position'],
      estimatedWaitMinutes: json['estimated_wait_minutes'],
      patientJoinedAt: json['patient_joined_at'] != null
          ? DateTime.parse(json['patient_joined_at'])
          : null,
    );
  }

  String get waitingMessage {
    if (position != null) {
      return position == 1
          ? "You're next!"
          : "You are #$position in the queue";
    }
    return "Waiting for doctor";
  }

  String get estimatedWaitMessage {
    if (estimatedWaitMinutes != null) {
      return estimatedWaitMinutes! < 60
          ? "~$estimatedWaitMinutes minutes"
          : "~${(estimatedWaitMinutes! / 60).ceil()} hour(s)";
    }
    return "Calculating...";
  }
}

/// Doctor queue item model
class DoctorQueueItem {
  final String consultationId;
  final String appointmentId;
  final String patientId;
  final String patientName;
  final DateTime patientJoinedAt;
  final int waitTimeMinutes;
  final String? chiefComplaint;
  final bool isEmergency;

  DoctorQueueItem({
    required this.consultationId,
    required this.appointmentId,
    required this.patientId,
    required this.patientName,
    required this.patientJoinedAt,
    required this.waitTimeMinutes,
    this.chiefComplaint,
    required this.isEmergency,
  });

  factory DoctorQueueItem.fromJson(Map<String, dynamic> json) {
    return DoctorQueueItem(
      consultationId: json['consultation_id'],
      appointmentId: json['appointment_id'],
      patientId: json['patient_id'],
      patientName: json['patient_name'],
      patientJoinedAt: DateTime.parse(json['patient_joined_at']),
      waitTimeMinutes: json['wait_time_minutes'],
      chiefComplaint: json['chief_complaint'],
      isEmergency: json['is_emergency'] ?? false,
    );
  }
}

/// Doctor queue response model
class DoctorQueueResponse {
  final String doctorId;
  final List<DoctorQueueItem> queue;
  final int totalWaiting;

  DoctorQueueResponse({
    required this.doctorId,
    required this.queue,
    required this.totalWaiting,
  });

  factory DoctorQueueResponse.fromJson(Map<String, dynamic> json) {
    return DoctorQueueResponse(
      doctorId: json['doctor_id'],
      queue: (json['queue'] as List)
          .map((item) => DoctorQueueItem.fromJson(item))
          .toList(),
      totalWaiting: json['total_waiting'],
    );
  }
}
