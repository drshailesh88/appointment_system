import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';

import '../../../core/models/insight_preferences.dart';
import '../../../core/services/insights_service.dart';
import 'insights_provider.dart';

/// State for insight preferences
class PreferencesState {
  final InsightPreferences? preferences;
  final bool isLoading;
  final String? error;
  final bool hasChanges;

  PreferencesState({
    this.preferences,
    this.isLoading = false,
    this.error,
    this.hasChanges = false,
  });

  PreferencesState copyWith({
    InsightPreferences? preferences,
    bool? isLoading,
    String? error,
    bool? hasChanges,
  }) {
    return PreferencesState(
      preferences: preferences ?? this.preferences,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      hasChanges: hasChanges ?? this.hasChanges,
    );
  }

  bool get hasPreferences => preferences != null;
}

/// Insight Preferences Provider
class PreferencesNotifier extends StateNotifier<PreferencesState> {
  final InsightsService _service;
  final Logger _logger = Logger();

  PreferencesNotifier(this._service) : super(PreferencesState());

  /// Fetch preferences from backend
  Future<void> fetchPreferences({bool forceRefresh = false}) async {
    // Skip if already loading
    if (state.isLoading && !forceRefresh) return;

    state = state.copyWith(isLoading: true, error: null);

    try {
      final preferences = await _service.getPreferences();

      state = state.copyWith(
        preferences: preferences,
        isLoading: false,
        hasChanges: false,
      );

      _logger.i('Fetched insight preferences');
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch preferences',
          error: e, stackTrace: stackTrace);
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Update preferences
  Future<bool> updatePreferences(InsightPreferences preferences) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      await _service.updatePreferences(preferences);

      state = state.copyWith(
        preferences: preferences,
        isLoading: false,
        hasChanges: false,
      );

      _logger.i('Updated insight preferences');
      return true;
    } catch (e, stackTrace) {
      _logger.e('Failed to update preferences',
          error: e, stackTrace: stackTrace);
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return false;
    }
  }

  /// Toggle category
  Future<bool> toggleCategory(String category, bool enabled) async {
    if (state.preferences == null) return false;

    final updated = _copyWithCategory(state.preferences!, category, enabled);
    state = state.copyWith(preferences: updated, hasChanges: true);
    return await updatePreferences(updated);
  }

  /// Toggle daily digest
  Future<bool> toggleDailyDigest(bool enabled) async {
    if (state.preferences == null) return false;

    final updated = state.preferences!.copyWith(enabledDailyDigest: enabled);
    state = state.copyWith(preferences: updated, hasChanges: true);
    return await updatePreferences(updated);
  }

  /// Set digest delivery time
  Future<bool> setDigestDeliveryTime(String time) async {
    if (state.preferences == null) return false;

    final updated = state.preferences!.copyWith(digestDeliveryTime: time);
    state = state.copyWith(preferences: updated, hasChanges: true);
    return await updatePreferences(updated);
  }

  /// Set quiet hours
  Future<bool> setQuietHours(QuietHours? quietHours) async {
    if (state.preferences == null) return false;

    final updated = state.preferences!.copyWith(quietHours: quietHours);
    state = state.copyWith(preferences: updated, hasChanges: true);
    return await updatePreferences(updated);
  }

  /// Toggle push notifications
  Future<bool> togglePushNotifications(bool enabled) async {
    if (state.preferences == null) return false;

    final updated =
        state.preferences!.copyWith(enabledPushNotifications: enabled);
    state = state.copyWith(preferences: updated, hasChanges: true);
    return await updatePreferences(updated);
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Helper to copy preferences with updated category
  InsightPreferences _copyWithCategory(
    InsightPreferences prefs,
    String category,
    bool enabled,
  ) {
    switch (category) {
      case 'follow_up':
        return prefs.copyWith(enabledFollowUp: enabled);
      case 'schedule':
        return prefs.copyWith(enabledSchedule: enabled);
      case 'revenue':
        return prefs.copyWith(enabledRevenue: enabled);
      case 'anomaly':
        return prefs.copyWith(enabledAnomaly: enabled);
      default:
        return prefs;
    }
  }
}

/// Insight preferences state provider
final preferencesProvider =
    StateNotifierProvider<PreferencesNotifier, PreferencesState>((ref) {
  final service = ref.watch(insightsServiceProvider);
  return PreferencesNotifier(service);
});

/// Provider for auto-fetching preferences on mount
final autoFetchPreferencesProvider = FutureProvider<InsightPreferences?>((ref) async {
  final preferencesNotifier = ref.watch(preferencesProvider.notifier);
  await preferencesNotifier.fetchPreferences();
  return ref.watch(preferencesProvider).preferences;
});
