import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../services/nl_search_service.dart';

/// Appointment search result model
class AppointmentSearchResult {
  final String id;
  final String patientId;
  final String patientName;
  final String doctorId;
  final String doctorName;
  final DateTime scheduledStart;
  final int durationMinutes;
  final String status;
  final String appointmentType;
  final String? chiefComplaint;
  final int? tokenNumber;
  final double relevanceScore;
  final String? matchReason;

  AppointmentSearchResult({
    required this.id,
    required this.patientId,
    required this.patientName,
    required this.doctorId,
    required this.doctorName,
    required this.scheduledStart,
    required this.durationMinutes,
    required this.status,
    required this.appointmentType,
    this.chiefComplaint,
    this.tokenNumber,
    required this.relevanceScore,
    this.matchReason,
  });

  factory AppointmentSearchResult.fromJson(Map<String, dynamic> json) {
    return AppointmentSearchResult(
      id: json['id'] ?? '',
      patientId: json['patient_id'] ?? '',
      patientName: json['patient_name'] ?? '',
      doctorId: json['doctor_id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      scheduledStart: json['scheduled_start'] != null
          ? DateTime.parse(json['scheduled_start'])
          : DateTime.now(),
      durationMinutes: json['duration_minutes'] ?? 15,
      status: json['status'] ?? '',
      appointmentType: json['appointment_type'] ?? '',
      chiefComplaint: json['chief_complaint'],
      tokenNumber: json['token_number'],
      relevanceScore: (json['relevance_score'] ?? 0.0).toDouble(),
      matchReason: json['match_reason'],
    );
  }

  String get statusIcon {
    switch (status) {
      case 'confirmed':
        return '✅';
      case 'scheduled':
        return '📅';
      case 'cancelled':
        return '❌';
      case 'no_show':
        return '👻';
      case 'completed':
        return '✔️';
      default:
        return '📋';
    }
  }

  String get statusLabel {
    switch (status) {
      case 'confirmed':
        return 'Confirmed';
      case 'scheduled':
        return 'Scheduled';
      case 'cancelled':
        return 'Cancelled';
      case 'no_show':
        return 'No Show';
      case 'completed':
        return 'Completed';
      case 'checked_in':
        return 'Checked In';
      case 'in_progress':
        return 'In Progress';
      default:
        return status;
    }
  }
}

/// Search suggestion model
class SearchSuggestion {
  final String text;
  final String category;
  final String? icon;

  SearchSuggestion({
    required this.text,
    required this.category,
    this.icon,
  });

  factory SearchSuggestion.fromJson(Map<String, dynamic> json) {
    return SearchSuggestion(
      text: json['text'] ?? '',
      category: json['category'] ?? '',
      icon: json['icon'],
    );
  }
}

/// Parsed query model
class ParsedQuery {
  final Map<String, dynamic> entities;
  final Map<String, dynamic> filters;
  final String queryType;
  final double confidence;
  final bool needsClarification;
  final String? clarificationQuestion;

  ParsedQuery({
    required this.entities,
    required this.filters,
    required this.queryType,
    required this.confidence,
    required this.needsClarification,
    this.clarificationQuestion,
  });

  factory ParsedQuery.fromJson(Map<String, dynamic> json) {
    return ParsedQuery(
      entities: Map<String, dynamic>.from(json['entities'] ?? {}),
      filters: Map<String, dynamic>.from(json['filters'] ?? {}),
      queryType: json['query_type'] ?? 'search',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      needsClarification: json['needs_clarification'] ?? false,
      clarificationQuestion: json['clarification_question'],
    );
  }
}

/// Search history entry model
class SearchHistoryEntry {
  final String id;
  final String query;
  final DateTime timestamp;
  final int resultCount;
  final String category;

  SearchHistoryEntry({
    required this.id,
    required this.query,
    required this.timestamp,
    required this.resultCount,
    required this.category,
  });

  factory SearchHistoryEntry.fromJson(Map<String, dynamic> json) {
    return SearchHistoryEntry(
      id: json['id'] ?? '',
      query: json['query'] ?? '',
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
      resultCount: json['result_count'] ?? 0,
      category: json['category'] ?? 'general',
    );
  }

  String get categoryIcon {
    switch (category) {
      case 'time':
        return '🕐';
      case 'status':
        return '📊';
      case 'doctor':
        return '👨‍⚕️';
      case 'patient':
        return '👤';
      default:
        return '🔍';
    }
  }
}

/// NL Search State
class NLSearchState {
  final bool isLoading;
  final bool isSearching;
  final String? error;
  final List<AppointmentSearchResult> results;
  final String? summary;
  final List<SearchSuggestion> suggestions;
  final ParsedQuery? parsedQuery;
  final int totalCount;
  final double? searchTimeMs;
  final List<SearchHistoryEntry> history;
  final String currentQuery;

  const NLSearchState({
    this.isLoading = false,
    this.isSearching = false,
    this.error,
    this.results = const [],
    this.summary,
    this.suggestions = const [],
    this.parsedQuery,
    this.totalCount = 0,
    this.searchTimeMs,
    this.history = const [],
    this.currentQuery = '',
  });

  NLSearchState copyWith({
    bool? isLoading,
    bool? isSearching,
    String? error,
    List<AppointmentSearchResult>? results,
    String? summary,
    List<SearchSuggestion>? suggestions,
    ParsedQuery? parsedQuery,
    int? totalCount,
    double? searchTimeMs,
    List<SearchHistoryEntry>? history,
    String? currentQuery,
  }) {
    return NLSearchState(
      isLoading: isLoading ?? this.isLoading,
      isSearching: isSearching ?? this.isSearching,
      error: error,
      results: results ?? this.results,
      summary: summary ?? this.summary,
      suggestions: suggestions ?? this.suggestions,
      parsedQuery: parsedQuery ?? this.parsedQuery,
      totalCount: totalCount ?? this.totalCount,
      searchTimeMs: searchTimeMs ?? this.searchTimeMs,
      history: history ?? this.history,
      currentQuery: currentQuery ?? this.currentQuery,
    );
  }
}

/// NL Search Notifier
class NLSearchNotifier extends StateNotifier<NLSearchState> {
  final NLSearchService _searchService;
  Timer? _debounceTimer;

  NLSearchNotifier(this._searchService) : super(const NLSearchState());

  /// Search appointments with natural language
  Future<void> search(String query) async {
    if (query.trim().isEmpty) {
      state = const NLSearchState();
      return;
    }

    state = state.copyWith(
      isSearching: true,
      error: null,
      currentQuery: query,
    );

    try {
      final response = await _searchService.searchAppointments(query: query);

      final results = (response['results'] as List)
          .map((r) => AppointmentSearchResult.fromJson(r))
          .toList();

      final suggestions = (response['suggestions'] as List)
          .map((s) => SearchSuggestion.fromJson(s))
          .toList();

      final parsedQuery = ParsedQuery.fromJson(response['parsed_query']);

      state = state.copyWith(
        isSearching: false,
        results: results,
        summary: response['summary'],
        suggestions: suggestions,
        parsedQuery: parsedQuery,
        totalCount: response['total_count'] ?? 0,
        searchTimeMs: (response['search_time_ms'] ?? 0.0).toDouble(),
      );
    } catch (e) {
      state = state.copyWith(
        isSearching: false,
        error: 'Search failed: $e',
      );
    }
  }

  /// Debounced search (for real-time search as user types)
  void debouncedSearch(String query, {Duration delay = const Duration(milliseconds: 500)}) {
    _debounceTimer?.cancel();

    if (query.trim().isEmpty) {
      state = const NLSearchState();
      return;
    }

    state = state.copyWith(currentQuery: query);

    _debounceTimer = Timer(delay, () {
      search(query);
    });
  }

  /// Parse query without executing search (for real-time feedback)
  Future<void> parseQuery(String query) async {
    if (query.trim().isEmpty) {
      return;
    }

    try {
      final response = await _searchService.parseQuery(query);
      final parsedQuery = ParsedQuery.fromJson(response['parsed_query']);

      state = state.copyWith(parsedQuery: parsedQuery);
    } catch (e) {
      // Silent fail for parsing
      // Don't update state with error for real-time parsing
    }
  }

  /// Load search suggestions
  Future<void> loadSuggestions() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final suggestionsData = await _searchService.getSuggestions();
      final suggestions =
          suggestionsData.map((s) => SearchSuggestion.fromJson(s)).toList();

      state = state.copyWith(
        isLoading: false,
        suggestions: suggestions,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load suggestions: $e',
      );
    }
  }

  /// Load search history
  Future<void> loadHistory() async {
    try {
      final response = await _searchService.getSearchHistory();
      final historyData = response['entries'] as List;
      final history =
          historyData.map((h) => SearchHistoryEntry.fromJson(h)).toList();

      state = state.copyWith(history: history);
    } catch (e) {
      // Silent fail for history
    }
  }

  /// Execute aggregate query
  Future<Map<String, dynamic>?> aggregateQuery(String query) async {
    state = state.copyWith(isSearching: true, error: null);

    try {
      final response = await _searchService.aggregateQuery(query);

      state = state.copyWith(isSearching: false);

      return response;
    } catch (e) {
      state = state.copyWith(
        isSearching: false,
        error: 'Aggregate query failed: $e',
      );
      return null;
    }
  }

  /// Clear search results
  void clearSearch() {
    state = const NLSearchState();
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }
}

/// NL Search service provider
final nlSearchServiceProvider = Provider<NLSearchService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return NLSearchService(apiClient);
});

/// NL Search provider
final nlSearchProvider = StateNotifierProvider<NLSearchNotifier, NLSearchState>((ref) {
  final searchService = ref.watch(nlSearchServiceProvider);
  return NLSearchNotifier(searchService);
});
