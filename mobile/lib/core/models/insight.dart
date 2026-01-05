/// Insight model for Proactive Intelligence Display.
///
/// Phase 16C: Proactive Intelligence

enum InsightCategory {
  followUp('follow_up'),
  schedule('schedule'),
  revenue('revenue'),
  anomaly('anomaly');

  final String value;
  const InsightCategory(this.value);

  static InsightCategory fromString(String value) {
    return InsightCategory.values.firstWhere(
      (e) => e.value == value,
      orElse: () => InsightCategory.anomaly,
    );
  }
}

enum InsightPriority {
  urgent('urgent'),
  important('important'),
  info('info');

  final String value;
  const InsightPriority(this.value);

  static InsightPriority fromString(String value) {
    return InsightPriority.values.firstWhere(
      (e) => e.value == value,
      orElse: () => InsightPriority.info,
    );
  }
}

class Insight {
  final String id;
  final InsightCategory category;
  final InsightPriority priority;
  final String title;
  final String description;
  final Map<String, dynamic>? data;
  final List<InsightAction>? suggestedActions;
  final DateTime createdAt;
  final DateTime? expiresAt;
  final bool isDismissed;
  final DateTime? dismissedAt;

  Insight({
    required this.id,
    required this.category,
    required this.priority,
    required this.title,
    required this.description,
    this.data,
    this.suggestedActions,
    required this.createdAt,
    this.expiresAt,
    this.isDismissed = false,
    this.dismissedAt,
  });

  factory Insight.fromJson(Map<String, dynamic> json) {
    return Insight(
      id: json['id'] as String,
      category: InsightCategory.fromString(json['category'] as String),
      priority: InsightPriority.fromString(json['priority'] as String),
      title: json['title'] as String,
      description: json['description'] as String,
      data: json['data'] as Map<String, dynamic>?,
      suggestedActions: (json['suggested_actions'] as List<dynamic>?)
          ?.map((e) => InsightAction.fromJson(e as Map<String, dynamic>))
          .toList(),
      createdAt: DateTime.parse(json['created_at'] as String),
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'] as String)
          : null,
      isDismissed: json['is_dismissed'] as bool? ?? false,
      dismissedAt: json['dismissed_at'] != null
          ? DateTime.parse(json['dismissed_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'category': category.value,
      'priority': priority.value,
      'title': title,
      'description': description,
      'data': data,
      'suggested_actions':
          suggestedActions?.map((e) => e.toJson()).toList(),
      'created_at': createdAt.toIso8601String(),
      'expires_at': expiresAt?.toIso8601String(),
      'is_dismissed': isDismissed,
      'dismissed_at': dismissedAt?.toIso8601String(),
    };
  }

  bool get isExpired =>
      expiresAt != null && DateTime.now().isAfter(expiresAt!);

  bool get isActive => !isDismissed && !isExpired;

  String get categoryDisplay {
    switch (category) {
      case InsightCategory.followUp:
        return 'Follow-up';
      case InsightCategory.schedule:
        return 'Schedule';
      case InsightCategory.revenue:
        return 'Revenue';
      case InsightCategory.anomaly:
        return 'Anomaly';
    }
  }

  String get priorityDisplay {
    switch (priority) {
      case InsightPriority.urgent:
        return 'Urgent';
      case InsightPriority.important:
        return 'Important';
      case InsightPriority.info:
        return 'Info';
    }
  }
}

class InsightAction {
  final String actionType;
  final String label;
  final Map<String, dynamic>? params;

  InsightAction({
    required this.actionType,
    required this.label,
    this.params,
  });

  factory InsightAction.fromJson(Map<String, dynamic> json) {
    return InsightAction(
      actionType: json['action_type'] as String,
      label: json['label'] as String,
      params: json['params'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'action_type': actionType,
      'label': label,
      'params': params,
    };
  }
}
