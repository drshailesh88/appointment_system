import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';

import '../../../core/models/daily_digest.dart';
import '../../../core/services/insights_service.dart';
import 'insights_provider.dart';

/// State for daily digest
class DigestState {
  final DailyDigest? digest;
  final bool isLoading;
  final String? error;
  final DateTime? lastFetched;

  DigestState({
    this.digest,
    this.isLoading = false,
    this.error,
    this.lastFetched,
  });

  DigestState copyWith({
    DailyDigest? digest,
    bool? isLoading,
    String? error,
    DateTime? lastFetched,
  }) {
    return DigestState(
      digest: digest ?? this.digest,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      lastFetched: lastFetched ?? this.lastFetched,
    );
  }

  bool get hasDigest => digest != null;

  bool get isToday {
    if (digest == null) return false;
    final now = DateTime.now();
    final digestDate = digest!.date;
    return digestDate.year == now.year &&
        digestDate.month == now.month &&
        digestDate.day == now.day;
  }
}

/// Daily Digest Provider
class DigestNotifier extends StateNotifier<DigestState> {
  final InsightsService _service;
  final Logger _logger = Logger();

  DigestNotifier(this._service) : super(DigestState());

  /// Fetch daily digest for specified date (default: today)
  Future<void> fetchDigest({
    DateTime? date,
    bool forceRefresh = false,
  }) async {
    // Skip if already loading
    if (state.isLoading && !forceRefresh) return;

    // Skip if recently fetched (within 5 minutes) and same date
    if (!forceRefresh &&
        state.lastFetched != null &&
        state.digest != null &&
        DateTime.now().difference(state.lastFetched!) <
            const Duration(minutes: 5)) {
      final targetDate = date ?? DateTime.now();
      if (_isSameDate(state.digest!.date, targetDate)) {
        _logger.d('Skipping fetch - recently fetched digest for same date');
        return;
      }
    }

    state = state.copyWith(isLoading: true, error: null);

    try {
      final digest = await _service.getDailyDigest(date: date);

      state = state.copyWith(
        digest: digest,
        isLoading: false,
        lastFetched: DateTime.now(),
      );

      _logger.i('Fetched daily digest for ${digest.date}');
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch digest', error: e, stackTrace: stackTrace);
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Fetch today's digest
  Future<void> fetchTodayDigest({bool forceRefresh = false}) async {
    await fetchDigest(date: DateTime.now(), forceRefresh: forceRefresh);
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Helper to check if two dates are the same day
  bool _isSameDate(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }
}

/// Daily digest state provider
final digestProvider = StateNotifierProvider<DigestNotifier, DigestState>((ref) {
  final service = ref.watch(insightsServiceProvider);
  return DigestNotifier(service);
});

/// Provider for auto-fetching today's digest on mount
final todayDigestProvider = FutureProvider<DailyDigest?>((ref) async {
  final digestNotifier = ref.watch(digestProvider.notifier);
  await digestNotifier.fetchTodayDigest();
  return ref.watch(digestProvider).digest;
});
