/// Daily Digest model for morning summary.
///
/// Phase 16C: Proactive Intelligence

class DailyDigest {
  final DateTime date;
  final DigestSummary summary;
  final List<DigestMetric> keyMetrics;
  final List<String> actionItems;
  final DigestAppointmentsOverview appointmentsOverview;
  final List<DigestInsight> topInsights;
  final DateTime generatedAt;

  DailyDigest({
    required this.date,
    required this.summary,
    required this.keyMetrics,
    required this.actionItems,
    required this.appointmentsOverview,
    required this.topInsights,
    required this.generatedAt,
  });

  factory DailyDigest.fromJson(Map<String, dynamic> json) {
    return DailyDigest(
      date: DateTime.parse(json['date'] as String),
      summary: DigestSummary.fromJson(json['summary'] as Map<String, dynamic>),
      keyMetrics: (json['key_metrics'] as List<dynamic>)
          .map((e) => DigestMetric.fromJson(e as Map<String, dynamic>))
          .toList(),
      actionItems: (json['action_items'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      appointmentsOverview: DigestAppointmentsOverview.fromJson(
          json['appointments_overview'] as Map<String, dynamic>),
      topInsights: (json['top_insights'] as List<dynamic>)
          .map((e) => DigestInsight.fromJson(e as Map<String, dynamic>))
          .toList(),
      generatedAt: DateTime.parse(json['generated_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'date': date.toIso8601String(),
      'summary': summary.toJson(),
      'key_metrics': keyMetrics.map((e) => e.toJson()).toList(),
      'action_items': actionItems,
      'appointments_overview': appointmentsOverview.toJson(),
      'top_insights': topInsights.map((e) => e.toJson()).toList(),
      'generated_at': generatedAt.toIso8601String(),
    };
  }
}

class DigestSummary {
  final String greeting;
  final String overview;
  final String focus;

  DigestSummary({
    required this.greeting,
    required this.overview,
    required this.focus,
  });

  factory DigestSummary.fromJson(Map<String, dynamic> json) {
    return DigestSummary(
      greeting: json['greeting'] as String,
      overview: json['overview'] as String,
      focus: json['focus'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'greeting': greeting,
      'overview': overview,
      'focus': focus,
    };
  }
}

class DigestMetric {
  final String label;
  final String value;
  final String? trend; // 'up', 'down', 'stable'
  final String? trendPercentage;
  final String? icon;

  DigestMetric({
    required this.label,
    required this.value,
    this.trend,
    this.trendPercentage,
    this.icon,
  });

  factory DigestMetric.fromJson(Map<String, dynamic> json) {
    return DigestMetric(
      label: json['label'] as String,
      value: json['value'] as String,
      trend: json['trend'] as String?,
      trendPercentage: json['trend_percentage'] as String?,
      icon: json['icon'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'label': label,
      'value': value,
      'trend': trend,
      'trend_percentage': trendPercentage,
      'icon': icon,
    };
  }

  bool get isUpTrend => trend == 'up';
  bool get isDownTrend => trend == 'down';
  bool get isStableTrend => trend == 'stable';
}

class DigestAppointmentsOverview {
  final int totalAppointments;
  final int scheduledAppointments;
  final int confirmedAppointments;
  final int pendingConfirmations;
  final String? nextAppointmentTime;
  final String? nextPatientName;

  DigestAppointmentsOverview({
    required this.totalAppointments,
    required this.scheduledAppointments,
    required this.confirmedAppointments,
    required this.pendingConfirmations,
    this.nextAppointmentTime,
    this.nextPatientName,
  });

  factory DigestAppointmentsOverview.fromJson(Map<String, dynamic> json) {
    return DigestAppointmentsOverview(
      totalAppointments: json['total_appointments'] as int,
      scheduledAppointments: json['scheduled_appointments'] as int,
      confirmedAppointments: json['confirmed_appointments'] as int,
      pendingConfirmations: json['pending_confirmations'] as int,
      nextAppointmentTime: json['next_appointment_time'] as String?,
      nextPatientName: json['next_patient_name'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_appointments': totalAppointments,
      'scheduled_appointments': scheduledAppointments,
      'confirmed_appointments': confirmedAppointments,
      'pending_confirmations': pendingConfirmations,
      'next_appointment_time': nextAppointmentTime,
      'next_patient_name': nextPatientName,
    };
  }
}

class DigestInsight {
  final String title;
  final String description;
  final String priority;
  final String category;

  DigestInsight({
    required this.title,
    required this.description,
    required this.priority,
    required this.category,
  });

  factory DigestInsight.fromJson(Map<String, dynamic> json) {
    return DigestInsight(
      title: json['title'] as String,
      description: json['description'] as String,
      priority: json['priority'] as String,
      category: json['category'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'description': description,
      'priority': priority,
      'category': category,
    };
  }
}
