import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';

import '../../../core/api/api_client.dart';
import '../../../core/models/insight.dart';
import '../../../core/services/insights_service.dart';

/// Provider for ApiClient
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

/// Provider for InsightsService
final insightsServiceProvider = Provider<InsightsService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return InsightsService(apiClient);
});

/// State for insights list
class InsightsState {
  final List<Insight> insights;
  final bool isLoading;
  final String? error;
  final DateTime? lastFetched;

  InsightsState({
    this.insights = const [],
    this.isLoading = false,
    this.error,
    this.lastFetched,
  });

  InsightsState copyWith({
    List<Insight>? insights,
    bool? isLoading,
    String? error,
    DateTime? lastFetched,
  }) {
    return InsightsState(
      insights: insights ?? this.insights,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      lastFetched: lastFetched ?? this.lastFetched,
    );
  }

  /// Get active insights (not dismissed, not expired)
  List<Insight> get activeInsights {
    return insights.where((insight) => insight.isActive).toList();
  }

  /// Get insights by category
  List<Insight> insightsByCategory(InsightCategory category) {
    return activeInsights
        .where((insight) => insight.category == category)
        .toList();
  }

  /// Get insights by priority
  List<Insight> insightsByPriority(InsightPriority priority) {
    return activeInsights
        .where((insight) => insight.priority == priority)
        .toList();
  }

  /// Get urgent insights
  List<Insight> get urgentInsights {
    return activeInsights
        .where((insight) => insight.priority == InsightPriority.urgent)
        .toList();
  }
}

/// Insights Provider
class InsightsNotifier extends StateNotifier<InsightsState> {
  final InsightsService _service;
  final Logger _logger = Logger();

  InsightsNotifier(this._service) : super(InsightsState());

  /// Fetch insights from backend
  Future<void> fetchInsights({
    String? category,
    String? priority,
    bool includeExpired = false,
    bool forceRefresh = false,
  }) async {
    // Skip if already loading
    if (state.isLoading && !forceRefresh) return;

    // Skip if recently fetched (within 1 minute)
    if (!forceRefresh &&
        state.lastFetched != null &&
        DateTime.now().difference(state.lastFetched!) < const Duration(minutes: 1)) {
      _logger.d('Skipping fetch - recently fetched');
      return;
    }

    state = state.copyWith(isLoading: true, error: null);

    try {
      final insights = await _service.getInsights(
        category: category,
        priority: priority,
        includeExpired: includeExpired,
      );

      state = state.copyWith(
        insights: insights,
        isLoading: false,
        lastFetched: DateTime.now(),
      );

      _logger.i('Fetched ${insights.length} insights');
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch insights', error: e, stackTrace: stackTrace);
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Perform action on insight
  Future<bool> performAction(
    String insightId,
    String actionType, {
    Map<String, dynamic>? params,
  }) async {
    try {
      await _service.performAction(insightId, actionType, params: params);
      _logger.i('Action performed: $actionType on $insightId');

      // Refresh insights after action
      await fetchInsights(forceRefresh: true);
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to perform action', error: e, stackTrace: stackTrace);
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Dismiss insight
  Future<bool> dismissInsight(String insightId, {String? reason}) async {
    try {
      await _service.dismissInsight(insightId, reason: reason);
      _logger.i('Insight dismissed: $insightId');

      // Remove from local state
      state = state.copyWith(
        insights: state.insights
            .map((insight) => insight.id == insightId
                ? Insight.fromJson({
                    ...insight.toJson(),
                    'is_dismissed': true,
                    'dismissed_at': DateTime.now().toIso8601String(),
                  })
                : insight)
            .toList(),
      );

      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to dismiss insight', error: e, stackTrace: stackTrace);
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Snooze insight
  Future<bool> snoozeInsight(String insightId, int durationMinutes) async {
    try {
      await _service.snoozeInsight(insightId, durationMinutes);
      _logger.i('Insight snoozed: $insightId for $durationMinutes minutes');

      // Refresh insights
      await fetchInsights(forceRefresh: true);
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to snooze insight', error: e, stackTrace: stackTrace);
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Get insight by ID
  Future<Insight?> getInsightById(String insightId) async {
    try {
      return await _service.getInsightById(insightId);
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch insight', error: e, stackTrace: stackTrace);
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Insights state provider
final insightsProvider =
    StateNotifierProvider<InsightsNotifier, InsightsState>((ref) {
  final service = ref.watch(insightsServiceProvider);
  return InsightsNotifier(service);
});
