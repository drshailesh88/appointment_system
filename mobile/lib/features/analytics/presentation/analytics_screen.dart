import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/analytics_provider.dart';

/// Analytics Dashboard Screen
class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  String _selectedPeriod = 'month';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(analyticsProvider.notifier).loadDashboard(_selectedPeriod);
    });
  }

  @override
  Widget build(BuildContext context) {
    final analyticsState = ref.watch(analyticsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Analytics'),
        actions: [
          PopupMenuButton<String>(
            initialValue: _selectedPeriod,
            onSelected: (value) {
              setState(() => _selectedPeriod = value);
              ref.read(analyticsProvider.notifier).loadDashboard(value);
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'today', child: Text('Today')),
              const PopupMenuItem(value: 'week', child: Text('This Week')),
              const PopupMenuItem(value: 'month', child: Text('This Month')),
              const PopupMenuItem(value: 'quarter', child: Text('This Quarter')),
              const PopupMenuItem(value: 'year', child: Text('This Year')),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Text(_getPeriodLabel(_selectedPeriod)),
                  const Icon(Icons.arrow_drop_down),
                ],
              ),
            ),
          ),
        ],
      ),
      body: analyticsState.isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () => ref
                  .read(analyticsProvider.notifier)
                  .loadDashboard(_selectedPeriod),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Appointment Stats Cards
                    Text(
                      'Appointment Statistics',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _AppointmentStatsGrid(
                      stats: analyticsState.appointmentStats,
                    ),
                    const SizedBox(height: 24),

                    // Revenue Section
                    Text(
                      'Revenue',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _RevenueCard(revenue: analyticsState.revenueStats),
                    const SizedBox(height: 24),

                    // Doctor Utilization
                    Text(
                      'Doctor Utilization',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _DoctorUtilizationList(
                      doctors: analyticsState.doctorUtilization,
                    ),
                    const SizedBox(height: 24),

                    // Daily Trend Chart
                    Text(
                      'Daily Trend',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _DailyTrendChart(trend: analyticsState.dailyTrend),
                  ],
                ),
              ),
            ),
    );
  }

  String _getPeriodLabel(String period) {
    switch (period) {
      case 'today':
        return 'Today';
      case 'week':
        return 'This Week';
      case 'month':
        return 'This Month';
      case 'quarter':
        return 'This Quarter';
      case 'year':
        return 'This Year';
      default:
        return 'Period';
    }
  }
}

class _AppointmentStatsGrid extends StatelessWidget {
  final AppointmentStats? stats;

  const _AppointmentStatsGrid({required this.stats});

  @override
  Widget build(BuildContext context) {
    if (stats == null) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Center(child: Text('No data available')),
        ),
      );
    }

    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.5,
      children: [
        _StatTile(
          title: 'Total',
          value: '${stats!.total}',
          icon: Icons.calendar_today,
          color: Colors.blue,
        ),
        _StatTile(
          title: 'Completed',
          value: '${stats!.completed}',
          subtitle: '${stats!.completionRate.toStringAsFixed(1)}%',
          icon: Icons.check_circle,
          color: Colors.green,
        ),
        _StatTile(
          title: 'Cancelled',
          value: '${stats!.cancelled}',
          subtitle: '${stats!.cancellationRate.toStringAsFixed(1)}%',
          icon: Icons.cancel,
          color: Colors.red,
        ),
        _StatTile(
          title: 'No Show',
          value: '${stats!.noShow}',
          subtitle: '${stats!.noShowRate.toStringAsFixed(1)}%',
          icon: Icons.person_off,
          color: Colors.orange,
        ),
      ],
    );
  }
}

class _StatTile extends StatelessWidget {
  final String title;
  final String value;
  final String? subtitle;
  final IconData icon;
  final Color color;

  const _StatTile({
    required this.title,
    required this.value,
    this.subtitle,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            if (subtitle != null)
              Text(
                subtitle!,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: color,
                    ),
              ),
          ],
        ),
      ),
    );
  }
}

class _RevenueCard extends StatelessWidget {
  final RevenueStats? revenue;

  const _RevenueCard({required this.revenue});

  @override
  Widget build(BuildContext context) {
    if (revenue == null) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Center(child: Text('No revenue data')),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Total Revenue',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Colors.grey,
                          ),
                    ),
                    Text(
                      '₹${revenue!.totalRevenue.toStringAsFixed(0)}',
                      style:
                          Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.green,
                              ),
                    ),
                  ],
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${revenue!.collectionRate.toStringAsFixed(1)}% collected',
                    style: TextStyle(color: Colors.green.shade700),
                  ),
                ),
              ],
            ),
            const Divider(height: 32),
            Row(
              children: [
                Expanded(
                  child: _RevenueMetric(
                    label: 'Collected',
                    value: '₹${revenue!.collected.toStringAsFixed(0)}',
                    color: Colors.green,
                  ),
                ),
                Expanded(
                  child: _RevenueMetric(
                    label: 'Pending',
                    value: '₹${revenue!.pending.toStringAsFixed(0)}',
                    color: Colors.orange,
                  ),
                ),
                Expanded(
                  child: _RevenueMetric(
                    label: 'Avg Invoice',
                    value: '₹${revenue!.averageInvoice.toStringAsFixed(0)}',
                    color: Colors.blue,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RevenueMetric extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _RevenueMetric({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey,
              ),
        ),
      ],
    );
  }
}

class _DoctorUtilizationList extends StatelessWidget {
  final List<DoctorUtilization> doctors;

  const _DoctorUtilizationList({required this.doctors});

  @override
  Widget build(BuildContext context) {
    if (doctors.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Center(child: Text('No doctor data')),
        ),
      );
    }

    return Card(
      child: Column(
        children: doctors.map((doctor) {
          return ListTile(
            leading: CircleAvatar(
              backgroundColor: _getUtilizationColor(doctor.utilizationRate),
              child: Text(
                doctor.doctorName.substring(0, 1),
                style: const TextStyle(color: Colors.white),
              ),
            ),
            title: Text('Dr. ${doctor.doctorName}'),
            subtitle: Text(
              '${doctor.completedAppointments} appointments completed',
            ),
            trailing: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${doctor.utilizationRate.toStringAsFixed(0)}%',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: _getUtilizationColor(doctor.utilizationRate),
                      ),
                ),
                Text(
                  'utilization',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey,
                      ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Color _getUtilizationColor(double rate) {
    if (rate >= 80) return Colors.green;
    if (rate >= 50) return Colors.orange;
    return Colors.red;
  }
}

class _DailyTrendChart extends StatelessWidget {
  final List<DailyMetric> trend;

  const _DailyTrendChart({required this.trend});

  @override
  Widget build(BuildContext context) {
    if (trend.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Center(child: Text('No trend data')),
        ),
      );
    }

    final maxAppointments = trend
        .map((m) => m.appointments)
        .reduce((a, b) => a > b ? a : b)
        .toDouble();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 150,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: trend.map((metric) {
                  final height = maxAppointments > 0
                      ? (metric.appointments / maxAppointments) * 120
                      : 0.0;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 2),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Text(
                            '${metric.appointments}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 4),
                          Container(
                            height: height,
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.primary,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _formatDate(metric.date),
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  fontSize: 10,
                                ),
                          ),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}';
  }
}
