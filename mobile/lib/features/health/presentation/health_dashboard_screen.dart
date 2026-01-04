import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

import '../../../core/models/health_record.dart';
import '../../../core/providers/health_provider.dart';
import '../../../core/providers/auth_provider.dart';

/// Health Dashboard Screen
///
/// Displays health metrics overview, trends, and sync status
class HealthDashboardScreen extends ConsumerStatefulWidget {
  final String patientId;

  const HealthDashboardScreen({
    super.key,
    required this.patientId,
  });

  @override
  ConsumerState<HealthDashboardScreen> createState() =>
      _HealthDashboardScreenState();
}

class _HealthDashboardScreenState extends ConsumerState<HealthDashboardScreen> {
  HealthMetric? selectedMetric;
  List<HealthReading> chartData = [];
  bool loadingChart = false;

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
    await healthNotifier.loadHealthSummary(widget.patientId);
  }

  Future<void> _loadChartData(HealthMetric metric) async {
    setState(() {
      loadingChart = true;
      selectedMetric = metric;
    });

    final healthNotifier = ref.read(healthProvider.notifier);
    final endDate = DateTime.now();
    final startDate = endDate.subtract(const Duration(days: 7));

    final readings = await healthNotifier.loadReadingsForRange(
      patientId: widget.patientId,
      metricType: metric,
      startDate: startDate,
      endDate: endDate,
    );

    setState(() {
      chartData = readings;
      loadingChart = false;
    });
  }

  Future<void> _performSync() async {
    final healthNotifier = ref.read(healthProvider.notifier);
    await healthNotifier.syncHealthData(widget.patientId);
  }

  @override
  Widget build(BuildContext context) {
    final healthState = ref.watch(healthProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Health Dashboard'),
        actions: [
          if (healthState.isConnected)
            IconButton(
              icon: healthState.isSyncing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.sync),
              onPressed: healthState.isSyncing ? null : _performSync,
              tooltip: 'Sync Health Data',
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await _initializeHealth();
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildConnectionStatus(healthState),
              const SizedBox(height: 24),
              if (healthState.isConnected) ...[
                _buildSyncStatus(healthState),
                const SizedBox(height: 24),
                _buildVitalSignsCards(healthState),
                const SizedBox(height: 24),
                _buildActivityCards(healthState),
                const SizedBox(height: 24),
                _buildTrendChart(),
              ] else
                _buildConnectPrompt(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConnectionStatus(HealthState state) {
    Color statusColor;
    IconData statusIcon;
    String statusText;

    switch (state.connectionStatus) {
      case HealthConnectionStatus.connected:
        statusColor = Colors.green;
        statusIcon = Icons.check_circle;
        statusText = 'Connected to Apple Health';
        break;
      case HealthConnectionStatus.connecting:
        statusColor = Colors.orange;
        statusIcon = Icons.sync;
        statusText = 'Connecting...';
        break;
      case HealthConnectionStatus.permissionDenied:
        statusColor = Colors.red;
        statusIcon = Icons.block;
        statusText = 'Permission Denied';
        break;
      case HealthConnectionStatus.error:
        statusColor = Colors.red;
        statusIcon = Icons.error;
        statusText = 'Connection Error';
        break;
      default:
        statusColor = Colors.grey;
        statusIcon = Icons.cloud_off;
        statusText = 'Not Connected';
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(statusIcon, color: statusColor, size: 32),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    statusText,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: statusColor,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  if (state.error != null)
                    Text(
                      state.error!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.red,
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

  Widget _buildSyncStatus(HealthState state) {
    final lastSynced = state.lastSyncedAt;
    final syncedCount = state.syncedCount;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Sync Status',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Last Synced',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    Text(
                      lastSynced != null
                          ? _formatRelativeTime(lastSynced)
                          : 'Never',
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Records Synced',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    Text(
                      syncedCount.toString(),
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVitalSignsCards(HealthState state) {
    final summary = state.summary;
    if (summary == null) {
      return const SizedBox();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Vital Signs',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1.5,
          children: [
            if (summary.latestHeartRate != null)
              _buildVitalCard(
                'Heart Rate',
                summary.latestHeartRate!,
                Icons.favorite,
                Colors.red,
                () => _loadChartData(HealthMetric.heartRate),
              ),
            if (summary.bloodPressure != null)
              _buildVitalCard(
                'Blood Pressure',
                summary.latestBloodPressureSystolic!,
                Icons.show_chart,
                Colors.blue,
                () => _loadChartData(HealthMetric.bloodPressureSystolic),
                customValue: summary.bloodPressure,
              ),
            if (summary.latestOxygenSaturation != null)
              _buildVitalCard(
                'Oxygen',
                summary.latestOxygenSaturation!,
                Icons.air,
                Colors.cyan,
                () => _loadChartData(HealthMetric.oxygenSaturation),
              ),
            if (summary.latestBloodGlucose != null)
              _buildVitalCard(
                'Blood Glucose',
                summary.latestBloodGlucose!,
                Icons.water_drop,
                Colors.orange,
                () => _loadChartData(HealthMetric.bloodGlucose),
              ),
            if (summary.latestWeight != null)
              _buildVitalCard(
                'Weight',
                summary.latestWeight!,
                Icons.monitor_weight,
                Colors.purple,
                () => _loadChartData(HealthMetric.weight),
              ),
          ],
        ),
      ],
    );
  }

  Widget _buildVitalCard(
    String title,
    HealthReading reading,
    IconData icon,
    Color color,
    VoidCallback onTap, {
    String? customValue,
  }) {
    final isAbnormal = reading.isAbnormal;

    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Icon(icon, color: color, size: 24),
                  if (isAbnormal)
                    Icon(Icons.warning, color: Colors.orange, size: 20),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    customValue ?? reading.formattedValue,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: isAbnormal ? Colors.orange : null,
                        ),
                  ),
                  Text(
                    title,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  Text(
                    _formatRelativeTime(reading.recordedAt),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey,
                        ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActivityCards(HealthState state) {
    final summary = state.summary;
    if (summary == null) {
      return const SizedBox();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Today\'s Activity',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            if (summary.todaySteps != null)
              Expanded(
                child: _buildActivityCard(
                  'Steps',
                  summary.todaySteps.toString(),
                  'steps',
                  Icons.directions_walk,
                  Colors.green,
                  () => _loadChartData(HealthMetric.steps),
                ),
              ),
            if (summary.todaySteps != null && summary.todaySleepHours != null)
              const SizedBox(width: 12),
            if (summary.todaySleepHours != null)
              Expanded(
                child: _buildActivityCard(
                  'Sleep',
                  summary.todaySleepHours!.toStringAsFixed(1),
                  'hours',
                  Icons.bedtime,
                  Colors.indigo,
                  () => _loadChartData(HealthMetric.sleepAnalysis),
                ),
              ),
          ],
        ),
      ],
    );
  }

  Widget _buildActivityCard(
    String title,
    String value,
    String unit,
    IconData icon,
    Color color,
    VoidCallback onTap,
  ) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color, size: 32),
              const SizedBox(height: 12),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              Text(
                '$title ($unit)',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTrendChart() {
    if (selectedMetric == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              const Icon(Icons.insights, size: 64, color: Colors.grey),
              const SizedBox(height: 16),
              Text(
                'Select a health metric to view trends',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Colors.grey,
                    ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    if (loadingChart) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(64.0),
          child: Center(child: CircularProgressIndicator()),
        ),
      );
    }

    if (chartData.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Text(
            'No data available for ${selectedMetric!.displayName}',
            style: Theme.of(context).textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${selectedMetric!.displayName} (Last 7 Days)',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(show: true),
                  titlesData: FlTitlesData(
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          final index = value.toInt();
                          if (index >= 0 && index < chartData.length) {
                            final date = chartData[index].recordedAt;
                            return Text(
                              DateFormat('MM/dd').format(date),
                              style: const TextStyle(fontSize: 10),
                            );
                          }
                          return const Text('');
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 40,
                        getTitlesWidget: (value, meta) {
                          return Text(
                            value.toStringAsFixed(0),
                            style: const TextStyle(fontSize: 10),
                          );
                        },
                      ),
                    ),
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                  ),
                  borderData: FlBorderData(show: true),
                  lineBarsData: [
                    LineChartBarData(
                      spots: chartData
                          .asMap()
                          .entries
                          .map((e) => FlSpot(
                                e.key.toDouble(),
                                e.value.value,
                              ))
                          .toList(),
                      isCurved: true,
                      color: Colors.blue,
                      dotData: const FlDotData(show: true),
                      belowBarData: BarAreaData(
                        show: true,
                        color: Colors.blue.withOpacity(0.1),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectPrompt() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            const Icon(
              Icons.health_and_safety,
              size: 80,
              color: Colors.blue,
            ),
            const SizedBox(height: 24),
            Text(
              'Connect to Apple Health',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            Text(
              'Sync your health data from Apple Health to track vital signs, activity, and more.',
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () async {
                final healthNotifier = ref.read(healthProvider.notifier);
                final granted = await healthNotifier.requestPermissions();

                if (granted && mounted) {
                  await healthNotifier.syncHealthData(widget.patientId);
                }
              },
              icon: const Icon(Icons.link),
              label: const Text('Connect Now'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                  vertical: 16,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return DateFormat('MMM dd').format(dateTime);
    }
  }
}
