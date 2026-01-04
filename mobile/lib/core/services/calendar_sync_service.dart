import 'package:url_launcher/url_launcher.dart';

import '../api/api_client.dart';

/// Google Calendar sync service
///
/// Handles OAuth flow and calendar synchronization with Google Calendar
class CalendarSyncService {
  final ApiClient _apiClient;

  CalendarSyncService(this._apiClient);

  /// Get OAuth authorization URL
  ///
  /// Opens browser for user to authorize Google Calendar access
  Future<Map<String, dynamic>> getAuthUrl() async {
    final response = await _apiClient.get('/calendar/auth-url');
    return response as Map<String, dynamic>;
  }

  /// Initiate OAuth flow
  ///
  /// Opens browser for user to authorize Google Calendar access
  /// Returns the auth URL that was opened
  Future<String> initiateOAuthFlow() async {
    try {
      final authData = await getAuthUrl();
      final authUrl = authData['auth_url'] as String;

      // Open authorization URL in browser
      final uri = Uri.parse(authUrl);
      if (await canLaunchUrl(uri)) {
        await launchUrl(
          uri,
          mode: LaunchMode.externalApplication,
        );
        return authUrl;
      } else {
        throw Exception('Could not launch authorization URL');
      }
    } catch (e) {
      throw Exception('Failed to initiate OAuth flow: $e');
    }
  }

  /// Handle OAuth callback
  ///
  /// Called after user authorizes in browser with the authorization code
  /// [code] - Authorization code from Google OAuth callback
  /// [state] - State parameter for CSRF protection (optional)
  Future<Map<String, dynamic>> handleCallback({
    required String code,
    String? state,
  }) async {
    final response = await _apiClient.post('/calendar/callback', {
      'code': code,
      if (state != null) 'state': state,
    });

    return response as Map<String, dynamic>;
  }

  /// Get calendar sync status
  ///
  /// Returns current connection status, last sync info, and recent logs
  Future<Map<String, dynamic>> getSyncStatus() async {
    final response = await _apiClient.get('/calendar/status');
    return response as Map<String, dynamic>;
  }

  /// Check if calendar is connected
  ///
  /// Convenience method to quickly check connection status
  Future<bool> isConnected() async {
    try {
      final status = await getSyncStatus();
      return status['connected'] == true;
    } catch (e) {
      return false;
    }
  }

  /// Trigger manual sync
  ///
  /// Syncs appointments to Google Calendar immediately
  /// Returns sync log with statistics
  Future<Map<String, dynamic>> triggerSync() async {
    final response = await _apiClient.post('/calendar/sync', {});
    return response as Map<String, dynamic>;
  }

  /// List available Google Calendars
  ///
  /// Returns list of calendars accessible by the connected account
  Future<List<Map<String, dynamic>>> listCalendars() async {
    final response = await _apiClient.get('/calendar/calendars');
    return (response as List).cast<Map<String, dynamic>>();
  }

  /// Update sync settings
  ///
  /// [googleCalendarId] - Which calendar to sync to (optional)
  /// [syncDirection] - Sync direction: one_way_to_google, one_way_from_google, two_way (optional)
  /// [conflictResolution] - How to resolve conflicts: google_wins, app_wins, latest_wins, manual (optional)
  /// [autoSyncEnabled] - Enable automatic background sync (optional)
  /// [syncIntervalMinutes] - Sync interval in minutes (5-1440) (optional)
  /// [colorMappings] - Map of appointment types to Google Calendar color IDs (optional)
  Future<Map<String, dynamic>> updateSettings({
    String? googleCalendarId,
    String? syncDirection,
    String? conflictResolution,
    bool? autoSyncEnabled,
    int? syncIntervalMinutes,
    Map<String, String>? colorMappings,
  }) async {
    final body = <String, dynamic>{};

    if (googleCalendarId != null) {
      body['google_calendar_id'] = googleCalendarId;
    }
    if (syncDirection != null) {
      body['sync_direction'] = syncDirection;
    }
    if (conflictResolution != null) {
      body['conflict_resolution'] = conflictResolution;
    }
    if (autoSyncEnabled != null) {
      body['auto_sync_enabled'] = autoSyncEnabled;
    }
    if (syncIntervalMinutes != null) {
      body['sync_interval_minutes'] = syncIntervalMinutes;
    }
    if (colorMappings != null) {
      body['color_mappings'] = colorMappings;
    }

    final response = await _apiClient.put('/calendar/settings', body);
    return response as Map<String, dynamic>;
  }

  /// Disconnect Google Calendar
  ///
  /// Deactivates the calendar connection without deleting sync history
  Future<void> disconnect() async {
    await _apiClient.delete('/calendar/disconnect');
  }

  /// Get sync logs
  ///
  /// Returns recent sync operation logs for debugging
  /// [limit] - Maximum number of logs to return (1-100, default: 20)
  Future<List<Map<String, dynamic>>> getSyncLogs({int limit = 20}) async {
    final response = await _apiClient.get(
      '/calendar/logs',
      queryParameters: {'limit': limit},
    );
    return (response as List).cast<Map<String, dynamic>>();
  }

  /// Get last sync information
  ///
  /// Convenience method to get just the last sync log
  Future<Map<String, dynamic>?> getLastSync() async {
    try {
      final status = await getSyncStatus();
      return status['last_sync'] as Map<String, dynamic>?;
    } catch (e) {
      return null;
    }
  }

  /// Get connection details
  ///
  /// Returns detailed information about the calendar connection
  Future<Map<String, dynamic>?> getConnection() async {
    try {
      final status = await getSyncStatus();
      return status['connection'] as Map<String, dynamic>?;
    } catch (e) {
      return null;
    }
  }

  /// Format sync direction for display
  ///
  /// Converts sync direction enum to human-readable string
  static String formatSyncDirection(String direction) {
    switch (direction) {
      case 'one_way_to_google':
        return 'App → Google Calendar';
      case 'one_way_from_google':
        return 'Google Calendar → App';
      case 'two_way':
        return 'Two-way sync';
      default:
        return direction;
    }
  }

  /// Format conflict resolution for display
  ///
  /// Converts conflict resolution enum to human-readable string
  static String formatConflictResolution(String resolution) {
    switch (resolution) {
      case 'google_wins':
        return 'Google Calendar wins';
      case 'app_wins':
        return 'App wins';
      case 'latest_wins':
        return 'Latest change wins';
      case 'manual':
        return 'Manual resolution';
      default:
        return resolution;
    }
  }

  /// Format sync status for display
  ///
  /// Converts sync status enum to human-readable string
  static String formatSyncStatus(String status) {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'in_progress':
        return 'In Progress';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      default:
        return status;
    }
  }

  /// Get sync status color
  ///
  /// Returns appropriate color for sync status display
  /// Returns hex color code as string (e.g., '#4CAF50')
  static String getSyncStatusColor(String status) {
    switch (status) {
      case 'pending':
        return '#FFC107'; // Amber
      case 'in_progress':
        return '#2196F3'; // Blue
      case 'completed':
        return '#4CAF50'; // Green
      case 'failed':
        return '#F44336'; // Red
      default:
        return '#9E9E9E'; // Grey
    }
  }
}
