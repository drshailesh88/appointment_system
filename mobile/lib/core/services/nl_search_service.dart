import '../api/api_client.dart';

/// Natural Language Search Service
///
/// Provides AI-powered conversational search for appointments
class NLSearchService {
  final ApiClient _apiClient;

  NLSearchService(this._apiClient);

  /// Search appointments using natural language
  ///
  /// Examples:
  /// - "appointments tomorrow"
  /// - "this week's schedule"
  /// - "Dr. Sharma's appointments next Monday"
  /// - "cancelled appointments this month"
  ///
  /// [query] - Natural language search query
  /// [context] - Optional context (filters, preferences)
  Future<Map<String, dynamic>> searchAppointments({
    required String query,
    Map<String, dynamic>? context,
  }) async {
    final response = await _apiClient.post('/nl-search/appointments', {
      'query': query,
      if (context != null) 'context': context,
    });

    return response as Map<String, dynamic>;
  }

  /// Parse query without executing search
  ///
  /// Useful for showing real-time parsing feedback
  ///
  /// [query] - Natural language query to parse
  Future<Map<String, dynamic>> parseQuery(String query) async {
    final response = await _apiClient.post('/nl-search/parse', {
      'query': query,
    });

    return response as Map<String, dynamic>;
  }

  /// Get search suggestions
  ///
  /// Returns common query examples to help users discover features
  Future<List<Map<String, dynamic>>> getSuggestions() async {
    final response = await _apiClient.get('/nl-search/suggestions');
    return List<Map<String, dynamic>>.from(response as List);
  }

  /// Execute aggregate query
  ///
  /// Examples:
  /// - "how many appointments tomorrow"
  /// - "number of no-shows this month"
  /// - "total appointments this week"
  ///
  /// [query] - Natural language aggregate query
  Future<Map<String, dynamic>> aggregateQuery(String query) async {
    final response = await _apiClient.post('/nl-search/aggregate', {
      'query': query,
    });

    return response as Map<String, dynamic>;
  }

  /// Get search history
  ///
  /// [limit] - Number of history entries to fetch
  Future<Map<String, dynamic>> getSearchHistory({int limit = 20}) async {
    final response = await _apiClient.get('/nl-search/history?limit=$limit');
    return response as Map<String, dynamic>;
  }
}
