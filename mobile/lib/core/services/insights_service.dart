import 'package:dio/dio.dart';
import 'package:logger/logger.dart';

import '../api/api_client.dart';
import '../models/insight.dart';
import '../models/daily_digest.dart';
import '../models/insight_preferences.dart';

/// Insights Service for Proactive Intelligence.
///
/// Phase 16C: Proactive Intelligence Display
///
/// Features:
/// - Fetch insights from backend
/// - Fetch daily digest
/// - Perform actions on insights
/// - Dismiss/snooze insights
/// - Manage insight preferences
class InsightsService {
  final ApiClient _apiClient;
  final Logger _logger = Logger();

  InsightsService(this._apiClient);

  /// Get all insights
  ///
  /// Returns a list of insights prioritized by backend.
  ///
  /// Parameters:
  /// - [category] - Filter by category (optional)
  /// - [priority] - Filter by priority (optional)
  /// - [includeExpired] - Include expired insights (default: false)
  /// - [limit] - Maximum number of insights to fetch (default: 50)
  Future<List<Insight>> getInsights({
    String? category,
    String? priority,
    bool includeExpired = false,
    int limit = 50,
  }) async {
    try {
      final response = await _apiClient._dio.get(
        '/api/v1/ai/insights',
        queryParameters: {
          if (category != null) 'category': category,
          if (priority != null) 'priority': priority,
          'include_expired': includeExpired,
          'limit': limit,
        },
      );

      final List<dynamic> data = response.data as List<dynamic>;
      return data.map((json) => Insight.fromJson(json)).toList();
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch insights', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Get daily digest
  ///
  /// Returns the daily digest summary for the specified date.
  ///
  /// Parameters:
  /// - [date] - Date for digest (default: today)
  Future<DailyDigest> getDailyDigest({DateTime? date}) async {
    try {
      final targetDate = date ?? DateTime.now();
      final dateStr = targetDate.toIso8601String().split('T')[0];

      final response = await _apiClient._dio.get(
        '/api/v1/ai/insights/digest',
        queryParameters: {
          'date': dateStr,
        },
      );

      return DailyDigest.fromJson(response.data);
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch daily digest', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Perform action on insight
  ///
  /// Executes the specified action on an insight.
  ///
  /// Parameters:
  /// - [insightId] - The insight ID
  /// - [actionType] - The action type to perform
  /// - [params] - Additional parameters for the action (optional)
  ///
  /// Returns: Result of the action
  Future<Map<String, dynamic>> performAction(
    String insightId,
    String actionType, {
    Map<String, dynamic>? params,
  }) async {
    try {
      final response = await _apiClient._dio.post(
        '/api/v1/ai/insights/$insightId/action',
        data: {
          'action_type': actionType,
          if (params != null) 'params': params,
        },
      );

      _logger.i('Action performed on insight $insightId: $actionType');
      return response.data;
    } catch (e, stackTrace) {
      _logger.e('Failed to perform action on insight',
          error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Dismiss insight
  ///
  /// Dismisses an insight so it won't be shown again.
  ///
  /// Parameters:
  /// - [insightId] - The insight ID to dismiss
  /// - [reason] - Optional reason for dismissal
  Future<void> dismissInsight(String insightId, {String? reason}) async {
    try {
      await _apiClient._dio.post(
        '/api/v1/ai/insights/$insightId/dismiss',
        data: {
          if (reason != null) 'reason': reason,
        },
      );

      _logger.i('Insight dismissed: $insightId');
    } catch (e, stackTrace) {
      _logger.e('Failed to dismiss insight', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Snooze insight
  ///
  /// Snoozes an insight for a specified duration.
  ///
  /// Parameters:
  /// - [insightId] - The insight ID to snooze
  /// - [duration] - Duration to snooze (in minutes)
  Future<void> snoozeInsight(String insightId, int durationMinutes) async {
    try {
      await _apiClient._dio.post(
        '/api/v1/ai/insights/$insightId/snooze',
        data: {
          'duration_minutes': durationMinutes,
        },
      );

      _logger.i('Insight snoozed: $insightId for $durationMinutes minutes');
    } catch (e, stackTrace) {
      _logger.e('Failed to snooze insight', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Get insight preferences
  ///
  /// Returns the user's insight preferences.
  Future<InsightPreferences> getPreferences() async {
    try {
      final response = await _apiClient._dio.get(
        '/api/v1/ai/insights/preferences',
      );

      return InsightPreferences.fromJson(response.data);
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch preferences', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Update insight preferences
  ///
  /// Updates the user's insight preferences.
  ///
  /// Parameters:
  /// - [preferences] - The updated preferences
  Future<void> updatePreferences(InsightPreferences preferences) async {
    try {
      await _apiClient._dio.put(
        '/api/v1/ai/insights/preferences',
        data: preferences.toJson(),
      );

      _logger.i('Insight preferences updated');
    } catch (e, stackTrace) {
      _logger.e('Failed to update preferences', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Get insight by ID
  ///
  /// Fetches a single insight by its ID.
  ///
  /// Parameters:
  /// - [insightId] - The insight ID
  Future<Insight> getInsightById(String insightId) async {
    try {
      final response = await _apiClient._dio.get(
        '/api/v1/ai/insights/$insightId',
      );

      return Insight.fromJson(response.data);
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch insight', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }
}
