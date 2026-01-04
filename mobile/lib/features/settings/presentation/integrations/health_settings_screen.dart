import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/models/health_record.dart';
import '../../../../core/providers/health_provider.dart';
import '../../../../core/providers/auth_provider.dart';

/// Health Settings Screen
///
/// Configure Apple Health integration settings including:
/// - Connection status
/// - Permission management
/// - Metric selection
/// - Auto-sync settings
/// - Privacy preferences
class HealthSettingsScreen extends ConsumerStatefulWidget {
  const HealthSettingsScreen({super.key});

  @override
  ConsumerState<HealthSettingsScreen> createState() =>
      _HealthSettingsScreenState();
}

class _HealthSettingsScreenState extends ConsumerState<HealthSettingsScreen> {
  bool autoSyncEnabled = true;
  int syncFrequencyHours = 6;
  bool backgroundSyncEnabled = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeHealth();
    });
  }

  Future<void> _initializeHealth() async {
    final healthNotifier = ref.read(healthProvider.notifier);
    await healthNotifier.initialize();
  }

  Future<void> _connectToHealth() async {
    final healthNotifier = ref.read(healthProvider.notifier);
    final granted = await healthNotifier.requestPermissions();

    if (granted && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Connected to Apple Health successfully'),
          backgroundColor: Colors.green,
        ),
      );

      // Optionally perform initial sync
      final authState = ref.read(authProvider);
      if (authState.user?.id != null) {
        await healthNotifier.syncHealthData(authState.user!.id);
      }
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to connect to Apple Health'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _disconnectFromHealth() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Disconnect Apple Health'),
        content: const Text(
          'Are you sure you want to disconnect from Apple Health? '
          'Your previously synced data will remain but no new data will be synced.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Disconnect'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final healthNotifier = ref.read(healthProvider.notifier);
      await healthNotifier.disconnect();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Disconnected from Apple Health'),
          ),
        );
      }
    }
  }

  Future<void> _syncNow() async {
    final authState = ref.read(authProvider);
    if (authState.user?.id == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please log in to sync health data'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final healthNotifier = ref.read(healthProvider.notifier);
    await healthNotifier.syncHealthData(authState.user!.id);

    if (mounted) {
      final healthState = ref.read(healthProvider);
      if (healthState.error == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Synced ${healthState.syncedCount} health records'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Sync failed: ${healthState.error}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _toggleBackgroundSync(bool enabled) async {
    setState(() {
      backgroundSyncEnabled = enabled;
    });

    if (enabled) {
      final healthNotifier = ref.read(healthProvider.notifier);
      await healthNotifier.enableBackgroundUpdates();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Background sync enabled'),
            backgroundColor: Colors.green,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final healthState = ref.watch(healthProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Health Integration'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildConnectionCard(healthState),
          const SizedBox(height: 24),
          if (healthState.isConnected) ...[
            _buildSyncSection(healthState),
            const SizedBox(height: 24),
            _buildMetricsSection(healthState),
            const SizedBox(height: 24),
            _buildPrivacySection(),
          ] else
            _buildSetupGuide(),
        ],
      ),
    );
  }

  Widget _buildConnectionCard(HealthState state) {
    final isConnected = state.isConnected;

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  isConnected ? Icons.check_circle : Icons.cloud_off,
                  color: isConnected ? Colors.green : Colors.grey,
                  size: 32,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isConnected ? 'Connected' : 'Not Connected',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      Text(
                        isConnected
                            ? 'Apple Health is connected'
                            : 'Connect to sync health data',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (isConnected)
              OutlinedButton.icon(
                onPressed: _disconnectFromHealth,
                icon: const Icon(Icons.link_off),
                label: const Text('Disconnect'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.red,
                  minimumSize: const Size(double.infinity, 48),
                ),
              )
            else
              ElevatedButton.icon(
                onPressed: _connectToHealth,
                icon: const Icon(Icons.link),
                label: const Text('Connect to Apple Health'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 48),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildSyncSection(HealthState state) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Sync Settings',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Auto-sync'),
              subtitle: const Text('Automatically sync health data'),
              value: autoSyncEnabled,
              onChanged: (value) {
                setState(() {
                  autoSyncEnabled = value;
                });
              },
              contentPadding: EdgeInsets.zero,
            ),
            const Divider(),
            SwitchListTile(
              title: const Text('Background sync'),
              subtitle: const Text('Sync health data in background'),
              value: backgroundSyncEnabled,
              onChanged: _toggleBackgroundSync,
              contentPadding: EdgeInsets.zero,
            ),
            const Divider(),
            ListTile(
              title: const Text('Sync frequency'),
              subtitle: Text('Every $syncFrequencyHours hours'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                _showSyncFrequencyDialog();
              },
              contentPadding: EdgeInsets.zero,
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: state.isSyncing ? null : _syncNow,
              icon: state.isSyncing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.sync),
              label: Text(state.isSyncing ? 'Syncing...' : 'Sync Now'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 48),
              ),
            ),
            if (state.lastSyncedAt != null) ...[
              const SizedBox(height: 8),
              Text(
                'Last synced: ${_formatDateTime(state.lastSyncedAt!)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey,
                    ),
                textAlign: TextAlign.center,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMetricsSection(HealthState state) {
    final permissions = state.permissions;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Health Metrics',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Select which health metrics to sync',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: 16),
            _buildMetricTile('Heart Rate', Icons.favorite, permissions.heartRate),
            _buildMetricTile(
                'Blood Pressure', Icons.show_chart, permissions.bloodPressure),
            _buildMetricTile('Weight', Icons.monitor_weight, permissions.weight),
            _buildMetricTile('Steps', Icons.directions_walk, permissions.steps),
            _buildMetricTile('Sleep', Icons.bedtime, permissions.sleep),
            _buildMetricTile(
                'Oxygen Saturation', Icons.air, permissions.oxygenSaturation),
            _buildMetricTile(
                'Blood Glucose', Icons.water_drop, permissions.bloodGlucose),
            _buildMetricTile('Body Temperature', Icons.thermostat,
                permissions.bodyTemperature),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricTile(String title, IconData icon, bool enabled) {
    return ListTile(
      leading: Icon(icon, color: enabled ? Colors.blue : Colors.grey),
      title: Text(title),
      trailing: Icon(
        enabled ? Icons.check_circle : Icons.cancel,
        color: enabled ? Colors.green : Colors.grey,
      ),
      contentPadding: EdgeInsets.zero,
      dense: true,
    );
  }

  Widget _buildPrivacySection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.privacy_tip, color: Colors.blue),
                const SizedBox(width: 12),
                Text(
                  'Privacy & Data',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              'Your health data is encrypted and stored securely. Only you and your healthcare providers can access this information.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.description),
              title: const Text('Privacy Policy'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                // Navigate to privacy policy
              },
              contentPadding: EdgeInsets.zero,
            ),
            ListTile(
              leading: const Icon(Icons.delete_forever, color: Colors.red),
              title: const Text('Delete All Health Data'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                _showDeleteDataDialog();
              },
              contentPadding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSetupGuide() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(
              Icons.info_outline,
              size: 48,
              color: Colors.blue,
            ),
            const SizedBox(height: 16),
            Text(
              'About Apple Health Integration',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            _buildSetupStep(
              '1',
              'Connect',
              'Tap "Connect to Apple Health" above to grant permissions',
            ),
            _buildSetupStep(
              '2',
              'Select Metrics',
              'Choose which health metrics to share with your doctor',
            ),
            _buildSetupStep(
              '3',
              'Auto-sync',
              'Your health data will be automatically synced to your medical records',
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.security, color: Colors.blue, size: 20),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Your health data is private and secure',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSetupStep(String number, String title, String description) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 16,
            child: Text(number),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showSyncFrequencyDialog() async {
    final selected = await showDialog<int>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Sync Frequency'),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.of(context).pop(1),
            child: const Text('Every hour'),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.of(context).pop(3),
            child: const Text('Every 3 hours'),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.of(context).pop(6),
            child: const Text('Every 6 hours'),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.of(context).pop(12),
            child: const Text('Every 12 hours'),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.of(context).pop(24),
            child: const Text('Once a day'),
          ),
        ],
      ),
    );

    if (selected != null) {
      setState(() {
        syncFrequencyHours = selected;
      });
    }
  }

  Future<void> _showDeleteDataDialog() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete All Health Data'),
        content: const Text(
          'This will permanently delete all health data synced from Apple Health. '
          'This action cannot be undone.\n\n'
          'Are you sure you want to continue?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      // TODO: Implement delete all health data API call
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('All health data has been deleted'),
          backgroundColor: Colors.orange,
        ),
      );
    }
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes} minutes ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours} hours ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else {
      return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
    }
  }
}
