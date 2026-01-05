/// Insight preferences model for user settings.
///
/// Phase 16C: Proactive Intelligence

class InsightPreferences {
  final bool enabledFollowUp;
  final bool enabledSchedule;
  final bool enabledRevenue;
  final bool enabledAnomaly;
  final bool enabledDailyDigest;
  final String? digestDeliveryTime; // HH:MM format
  final QuietHours? quietHours;
  final bool enabledPushNotifications;

  InsightPreferences({
    this.enabledFollowUp = true,
    this.enabledSchedule = true,
    this.enabledRevenue = true,
    this.enabledAnomaly = true,
    this.enabledDailyDigest = true,
    this.digestDeliveryTime,
    this.quietHours,
    this.enabledPushNotifications = true,
  });

  factory InsightPreferences.fromJson(Map<String, dynamic> json) {
    return InsightPreferences(
      enabledFollowUp: json['enabled_follow_up'] as bool? ?? true,
      enabledSchedule: json['enabled_schedule'] as bool? ?? true,
      enabledRevenue: json['enabled_revenue'] as bool? ?? true,
      enabledAnomaly: json['enabled_anomaly'] as bool? ?? true,
      enabledDailyDigest: json['enabled_daily_digest'] as bool? ?? true,
      digestDeliveryTime: json['digest_delivery_time'] as String?,
      quietHours: json['quiet_hours'] != null
          ? QuietHours.fromJson(json['quiet_hours'] as Map<String, dynamic>)
          : null,
      enabledPushNotifications:
          json['enabled_push_notifications'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'enabled_follow_up': enabledFollowUp,
      'enabled_schedule': enabledSchedule,
      'enabled_revenue': enabledRevenue,
      'enabled_anomaly': enabledAnomaly,
      'enabled_daily_digest': enabledDailyDigest,
      'digest_delivery_time': digestDeliveryTime,
      'quiet_hours': quietHours?.toJson(),
      'enabled_push_notifications': enabledPushNotifications,
    };
  }

  InsightPreferences copyWith({
    bool? enabledFollowUp,
    bool? enabledSchedule,
    bool? enabledRevenue,
    bool? enabledAnomaly,
    bool? enabledDailyDigest,
    String? digestDeliveryTime,
    QuietHours? quietHours,
    bool? enabledPushNotifications,
  }) {
    return InsightPreferences(
      enabledFollowUp: enabledFollowUp ?? this.enabledFollowUp,
      enabledSchedule: enabledSchedule ?? this.enabledSchedule,
      enabledRevenue: enabledRevenue ?? this.enabledRevenue,
      enabledAnomaly: enabledAnomaly ?? this.enabledAnomaly,
      enabledDailyDigest: enabledDailyDigest ?? this.enabledDailyDigest,
      digestDeliveryTime: digestDeliveryTime ?? this.digestDeliveryTime,
      quietHours: quietHours ?? this.quietHours,
      enabledPushNotifications:
          enabledPushNotifications ?? this.enabledPushNotifications,
    );
  }
}

class QuietHours {
  final String startTime; // HH:MM format
  final String endTime; // HH:MM format

  QuietHours({
    required this.startTime,
    required this.endTime,
  });

  factory QuietHours.fromJson(Map<String, dynamic> json) {
    return QuietHours(
      startTime: json['start_time'] as String,
      endTime: json['end_time'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'start_time': startTime,
      'end_time': endTime,
    };
  }

  bool isInQuietHours(DateTime time) {
    final now = time;
    final start = _parseTime(startTime);
    final end = _parseTime(endTime);

    final currentMinutes = now.hour * 60 + now.minute;
    final startMinutes = start.hour * 60 + start.minute;
    final endMinutes = end.hour * 60 + end.minute;

    if (startMinutes <= endMinutes) {
      // Same day (e.g., 09:00 - 17:00)
      return currentMinutes >= startMinutes && currentMinutes <= endMinutes;
    } else {
      // Crosses midnight (e.g., 22:00 - 06:00)
      return currentMinutes >= startMinutes || currentMinutes <= endMinutes;
    }
  }

  DateTime _parseTime(String time) {
    final parts = time.split(':');
    final now = DateTime.now();
    return DateTime(
        now.year, now.month, now.day, int.parse(parts[0]), int.parse(parts[1]));
  }
}
