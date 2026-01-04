import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/services/calendar_sync_service.dart';
import '../../../../core/api/api_client.dart';

/// Provider for calendar sync service
final calendarSyncServiceProvider = Provider<CalendarSyncService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CalendarSyncService(apiClient);
});

/// Google Calendar integration settings screen
class CalendarSettingsScreen extends ConsumerStatefulWidget {
  const CalendarSettingsScreen({super.key});

  @override
  ConsumerState<CalendarSettingsScreen> createState() =>
      _CalendarSettingsScreenState();
}

class _CalendarSettingsScreenState extends ConsumerState<CalendarSettingsScreen> {
  bool _isConnected = false;
  bool _isLoading = true;
  bool _isSyncing = false;
  Map<String, dynamic>? _connection;
  Map<String, dynamic>? _lastSync;
  List<Map<String, dynamic>> _recentLogs = [];
  List<Map<String, dynamic>> _availableCalendars = [];

  // Settings
  String? _selectedCalendarId;
  String _syncDirection = 'two_way';
  String _conflictResolution = 'latest_wins';
  bool _autoSyncEnabled = true;
  int _syncIntervalMinutes = 15;

  @override
  void initState() {
    super.initState();
    _loadStatus();
  }

  Future<void> _loadStatus() async {
    setState(() => _isLoading = true);

    try {
      final service = ref.read(calendarSyncServiceProvider);
      final status = await service.getSyncStatus();

      setState(() {
        _isConnected = status['connected'] == true;
        _connection = status['connection'] as Map<String, dynamic>?;
        _lastSync = status['last_sync'] as Map<String, dynamic>?;
        _recentLogs =
            (status['recent_logs'] as List?)?.cast<Map<String, dynamic>>() ?? [];

        // Load settings from connection
        if (_connection != null) {
          _selectedCalendarId = _connection!['google_calendar_id'] as String?;
          _syncDirection = _connection!['sync_direction'] as String? ?? 'two_way';
          _conflictResolution =
              _connection!['conflict_resolution'] as String? ?? 'latest_wins';
          _autoSyncEnabled = _connection!['auto_sync_enabled'] as bool? ?? true;
          _syncIntervalMinutes =
              _connection!['sync_interval_minutes'] as int? ?? 15;
        }
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load status: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _connect() async {
    try {
      final service = ref.read(calendarSyncServiceProvider);
      await service.initiateOAuthFlow();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Please complete authorization in browser.\n'
              'Return here after authorizing.',
            ),
            duration: Duration(seconds: 5),
          ),
        );

        // Reload status after a delay to check if connected
        Future.delayed(const Duration(seconds: 10), () {
          if (mounted) {
            _loadStatus();
          }
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to initiate connection: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _disconnect() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Disconnect Google Calendar?'),
        content: const Text(
          'This will stop syncing appointments with Google Calendar.\n'
          'Your sync history will be preserved.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Disconnect'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final service = ref.read(calendarSyncServiceProvider);
      await service.disconnect();

      setState(() {
        _isConnected = false;
        _connection = null;
        _lastSync = null;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Disconnected from Google Calendar'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to disconnect: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _syncNow() async {
    setState(() => _isSyncing = true);

    try {
      final service = ref.read(calendarSyncServiceProvider);
      final syncLog = await service.triggerSync();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Synced ${syncLog['events_synced']} appointments\n'
              'Created: ${syncLog['events_created']}, Updated: ${syncLog['events_updated']}',
            ),
            backgroundColor: Colors.green,
          ),
        );
      }

      await _loadStatus();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Sync failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() => _isSyncing = false);
    }
  }

  Future<void> _loadCalendars() async {
    try {
      final service = ref.read(calendarSyncServiceProvider);
      final calendars = await service.listCalendars();

      setState(() {
        _availableCalendars = calendars;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load calendars: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _updateSettings() async {
    try {
      final service = ref.read(calendarSyncServiceProvider);
      await service.updateSettings(
        googleCalendarId: _selectedCalendarId,
        syncDirection: _syncDirection,
        conflictResolution: _conflictResolution,
        autoSyncEnabled: _autoSyncEnabled,
        syncIntervalMinutes: _syncIntervalMinutes,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Settings updated successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }

      await _loadStatus();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update settings: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Google Calendar')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Google Calendar'),
        actions: [
          if (_isConnected)
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _loadStatus,
              tooltip: 'Refresh status',
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Connection Status Card
          Card(
            color: _isConnected ? Colors.green.shade50 : Colors.grey.shade100,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.calendar_today,
                        size: 40,
                        color: _isConnected ? Colors.green : Colors.grey,
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _isConnected
                                  ? 'Google Calendar Connected'
                                  : 'Not Connected',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                            ),
                            if (_isConnected && _connection != null)
                              Text(
                                _connection!['calendar_name'] as String? ?? '',
                                style: Theme.of(context).textTheme.bodySmall,
                              )
                            else
                              Text(
                                'Connect to sync appointments',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (!_isConnected)
                    ElevatedButton.icon(
                      onPressed: _connect,
                      icon: const Icon(Icons.link),
                      label: const Text('Connect Google Calendar'),
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size.fromHeight(48),
                      ),
                    )
                  else
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _isSyncing ? null : _syncNow,
                            icon: _isSyncing
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2),
                                  )
                                : const Icon(Icons.sync),
                            label: const Text('Sync Now'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _disconnect,
                            icon: const Icon(Icons.link_off),
                            label: const Text('Disconnect'),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.red,
                            ),
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),

          if (_isConnected) ...[
            const SizedBox(height: 24),

            // Last Sync Info
            if (_lastSync != null) ...[
              Text(
                'Last Sync',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Card(
                child: ListTile(
                  leading: Icon(
                    _getSyncIcon(_lastSync!['status'] as String?),
                    color: _getSyncColor(_lastSync!['status'] as String?),
                  ),
                  title: Text(
                    CalendarSyncService.formatSyncStatus(
                        _lastSync!['status'] as String? ?? 'unknown'),
                  ),
                  subtitle: Text(
                    '${_lastSync!['events_synced']} events synced\n'
                    '${_formatDateTime(_lastSync!['started_at'])}',
                  ),
                  isThreeLine: true,
                  trailing: _lastSync!['error_message'] != null
                      ? const Icon(Icons.error, color: Colors.red)
                      : null,
                ),
              ),
              const SizedBox(height: 24),
            ],

            // Sync Settings
            Text(
              'Sync Settings',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  ListTile(
                    title: const Text('Calendar'),
                    subtitle: Text(_connection!['calendar_name'] as String? ?? ''),
                    trailing: TextButton(
                      onPressed: () => _showCalendarPicker(),
                      child: const Text('Change'),
                    ),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    title: const Text('Sync Direction'),
                    subtitle: Text(
                        CalendarSyncService.formatSyncDirection(_syncDirection)),
                    trailing: DropdownButton<String>(
                      value: _syncDirection,
                      underline: const SizedBox(),
                      items: const [
                        DropdownMenuItem(
                          value: 'one_way_to_google',
                          child: Text('App → Google'),
                        ),
                        DropdownMenuItem(
                          value: 'two_way',
                          child: Text('Two-way'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _syncDirection = value);
                          _updateSettings();
                        }
                      },
                    ),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    title: const Text('Conflict Resolution'),
                    subtitle: Text(CalendarSyncService.formatConflictResolution(
                        _conflictResolution)),
                    trailing: DropdownButton<String>(
                      value: _conflictResolution,
                      underline: const SizedBox(),
                      items: const [
                        DropdownMenuItem(
                          value: 'latest_wins',
                          child: Text('Latest wins'),
                        ),
                        DropdownMenuItem(
                          value: 'app_wins',
                          child: Text('App wins'),
                        ),
                        DropdownMenuItem(
                          value: 'google_wins',
                          child: Text('Google wins'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _conflictResolution = value);
                          _updateSettings();
                        }
                      },
                    ),
                  ),
                  const Divider(height: 1),
                  SwitchListTile(
                    title: const Text('Auto Sync'),
                    subtitle: const Text('Sync automatically in background'),
                    value: _autoSyncEnabled,
                    onChanged: (value) {
                      setState(() => _autoSyncEnabled = value);
                      _updateSettings();
                    },
                  ),
                  if (_autoSyncEnabled) ...[
                    const Divider(height: 1),
                    ListTile(
                      title: const Text('Sync Interval'),
                      subtitle: Text('Every $_syncIntervalMinutes minutes'),
                      trailing: DropdownButton<int>(
                        value: _syncIntervalMinutes,
                        underline: const SizedBox(),
                        items: [5, 15, 30, 60]
                            .map((m) => DropdownMenuItem(
                                  value: m,
                                  child: Text('$m min'),
                                ))
                            .toList(),
                        onChanged: (value) {
                          if (value != null) {
                            setState(() => _syncIntervalMinutes = value);
                            _updateSettings();
                          }
                        },
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Recent Sync Logs
            if (_recentLogs.isNotEmpty) ...[
              Text(
                'Recent Syncs',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Card(
                child: ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: _recentLogs.take(5).length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final log = _recentLogs[index];
                    return ListTile(
                      leading: Icon(
                        _getSyncIcon(log['status'] as String?),
                        color: _getSyncColor(log['status'] as String?),
                        size: 20,
                      ),
                      title: Text(
                        '${log['events_synced']} events',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      subtitle: Text(
                        _formatDateTime(log['started_at']),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      trailing: log['error_message'] != null
                          ? const Icon(Icons.error, color: Colors.red, size: 16)
                          : null,
                    );
                  },
                ),
              ),
            ],
          ],

          const SizedBox(height: 24),

          // Help Section
          Card(
            color: Colors.blue.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.info_outline, color: Colors.blue.shade700),
                      const SizedBox(width: 8),
                      Text(
                        'How it works',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.blue.shade700,
                            ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '1. Connect your Google Calendar account\n'
                    '2. Choose sync direction and settings\n'
                    '3. Appointments sync automatically\n'
                    '4. Changes are reflected in both systems\n'
                    '5. Color-coded by appointment type',
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showCalendarPicker() async {
    if (_availableCalendars.isEmpty) {
      await _loadCalendars();
    }

    if (!mounted) return;

    await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Calendar'),
        content: _availableCalendars.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : SizedBox(
                width: double.maxFinite,
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: _availableCalendars.length,
                  itemBuilder: (context, index) {
                    final cal = _availableCalendars[index];
                    return RadioListTile<String>(
                      value: cal['id'] as String,
                      groupValue: _selectedCalendarId,
                      title: Text(cal['summary'] as String? ?? ''),
                      subtitle: cal['description'] != null &&
                              (cal['description'] as String).isNotEmpty
                          ? Text(cal['description'] as String)
                          : null,
                      secondary: cal['primary'] == true
                          ? const Icon(Icons.star, color: Colors.amber)
                          : null,
                      onChanged: (value) {
                        if (value != null) {
                          setState(() => _selectedCalendarId = value);
                          _updateSettings();
                          Navigator.pop(context);
                        }
                      },
                    );
                  },
                ),
              ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  IconData _getSyncIcon(String? status) {
    switch (status) {
      case 'completed':
        return Icons.check_circle;
      case 'failed':
        return Icons.error;
      case 'in_progress':
        return Icons.sync;
      default:
        return Icons.pending;
    }
  }

  Color _getSyncColor(String? status) {
    switch (status) {
      case 'completed':
        return Colors.green;
      case 'failed':
        return Colors.red;
      case 'in_progress':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  String _formatDateTime(dynamic dateTime) {
    if (dateTime == null) return 'Never';
    try {
      final dt = dateTime is DateTime ? dateTime : DateTime.parse(dateTime as String);
      return DateFormat('MMM d, y h:mm a').format(dt);
    } catch (e) {
      return dateTime.toString();
    }
  }
}
