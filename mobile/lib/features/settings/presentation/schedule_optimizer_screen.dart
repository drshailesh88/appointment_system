import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../core/providers/slot_optimizer_provider.dart';
import '../../../core/providers/doctors_provider.dart';

/// Schedule Optimizer Screen
///
/// Provides schedule analysis, utilization visualization,
/// gap identification, and optimization suggestions.
class ScheduleOptimizerScreen extends ConsumerStatefulWidget {
  const ScheduleOptimizerScreen({super.key});

  @override
  ConsumerState<ScheduleOptimizerScreen> createState() =>
      _ScheduleOptimizerScreenState();
}

class _ScheduleOptimizerScreenState
    extends ConsumerState<ScheduleOptimizerScreen> {
  String? _selectedDoctorId;
  DateTime _selectedDate = DateTime.now();
  DateTime _dateRangeStart = DateTime.now().subtract(const Duration(days: 30));
  DateTime _dateRangeEnd = DateTime.now();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(doctorsProvider.notifier).loadDoctors();
    });
  }

  void _loadData() {
    if (_selectedDoctorId == null) return;

    // Load all analytics
    ref.read(slotOptimizerProvider.notifier).analyzeSchedule(
          doctorId: _selectedDoctorId!,
          targetDate: _selectedDate,
        );

    ref.read(slotOptimizerProvider.notifier).loadUtilizationMetrics(
          doctorId: _selectedDoctorId!,
          dateFrom: _dateRangeStart,
          dateTo: _dateRangeEnd,
        );

    ref.read(slotOptimizerProvider.notifier).identifyGaps(
          doctorId: _selectedDoctorId!,
          targetDate: _selectedDate,
        );

    ref.read(slotOptimizerProvider.notifier).loadOptimizationSuggestions(
          doctorId: _selectedDoctorId!,
          dateFrom: _dateRangeStart,
          dateTo: _dateRangeEnd,
        );
  }

  @override
  Widget build(BuildContext context) {
    final doctorsState = ref.watch(doctorsProvider);
    final optimizerState = ref.watch(slotOptimizerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Schedule Optimizer'),
        actions: [
          if (_selectedDoctorId != null)
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _loadData,
            ),
        ],
      ),
      body: Column(
        children: [
          // Doctor selector
          Container(
            padding: const EdgeInsets.all(16),
            color: Theme.of(context).primaryColor.withOpacity(0.1),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Select Doctor',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _selectedDoctorId,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                  hint: const Text('Choose a doctor'),
                  items: doctorsState.doctors
                      .map((doctor) => DropdownMenuItem(
                            value: doctor.id,
                            child: Text(doctor.name),
                          ))
                      .toList(),
                  onChanged: (value) {
                    setState(() => _selectedDoctorId = value);
                    if (value != null) {
                      _loadData();
                    }
                  },
                ),
              ],
            ),
          ),

          // Content
          Expanded(
            child: _selectedDoctorId == null
                ? const Center(
                    child: Text('Please select a doctor to view analytics'),
                  )
                : optimizerState.isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : RefreshIndicator(
                        onRefresh: () async => _loadData(),
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Date selector
                              _DateSelector(
                                selectedDate: _selectedDate,
                                onDateChanged: (date) {
                                  setState(() => _selectedDate = date);
                                  _loadData();
                                },
                              ),
                              const SizedBox(height: 24),

                              // Schedule Analysis
                              if (optimizerState.scheduleAnalysis != null)
                                _ScheduleAnalysisSection(
                                  analysis: optimizerState.scheduleAnalysis!,
                                ),
                              const SizedBox(height: 24),

                              // Utilization Charts
                              if (optimizerState.utilizationMetrics != null)
                                _UtilizationChartsSection(
                                  metrics: optimizerState.utilizationMetrics!,
                                ),
                              const SizedBox(height: 24),

                              // Gap Visualization
                              if (optimizerState.gapIdentification != null)
                                _GapVisualizationSection(
                                  gaps: optimizerState.gapIdentification!,
                                ),
                              const SizedBox(height: 24),

                              // Optimization Suggestions
                              if (optimizerState.optimizationSuggestions != null)
                                _OptimizationSuggestionsSection(
                                  suggestions:
                                      optimizerState.optimizationSuggestions!,
                                ),
                            ],
                          ),
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

class _DateSelector extends StatelessWidget {
  final DateTime selectedDate;
  final Function(DateTime) onDateChanged;

  const _DateSelector({
    required this.selectedDate,
    required this.onDateChanged,
  });

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('EEE, MMM d, yyyy');

    return Card(
      child: ListTile(
        leading: const Icon(Icons.calendar_today),
        title: const Text('Analysis Date'),
        subtitle: Text(dateFormat.format(selectedDate)),
        trailing: const Icon(Icons.arrow_drop_down),
        onTap: () async {
          final picked = await showDatePicker(
            context: context,
            initialDate: selectedDate,
            firstDate: DateTime.now().subtract(const Duration(days: 365)),
            lastDate: DateTime.now().add(const Duration(days: 30)),
          );
          if (picked != null) {
            onDateChanged(picked);
          }
        },
      ),
    );
  }
}

class _ScheduleAnalysisSection extends StatelessWidget {
  final ScheduleAnalysis analysis;

  const _ScheduleAnalysisSection({required this.analysis});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Schedule Analysis',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),

        // Efficiency Score
        Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                const Text(
                  'Efficiency Score',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 8),
                Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 120,
                      height: 120,
                      child: CircularProgressIndicator(
                        value: analysis.efficiencyScore / 100,
                        strokeWidth: 12,
                        backgroundColor: Colors.grey.shade200,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          _getScoreColor(analysis.efficiencyScore),
                        ),
                      ),
                    ),
                    Column(
                      children: [
                        Text(
                          '${analysis.efficiencyScore.toStringAsFixed(0)}%',
                          style: const TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          _getScoreLabel(analysis.efficiencyScore),
                          style: TextStyle(
                            fontSize: 12,
                            color: _getScoreColor(analysis.efficiencyScore),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Metrics Grid
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 1.5,
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          children: [
            _MetricCard(
              icon: Icons.event,
              label: 'Appointments',
              value: analysis.appointmentCount.toString(),
              color: Colors.blue,
            ),
            _MetricCard(
              icon: Icons.schedule,
              label: 'Working Hours',
              value: '${analysis.workingHours}h',
              color: Colors.green,
            ),
            _MetricCard(
              icon: Icons.gap,
              label: 'Gaps',
              value: analysis.gapCount.toString(),
              color: Colors.orange,
            ),
            _MetricCard(
              icon: Icons.percent,
              label: 'Utilization',
              value: '${analysis.utilizationRate.toStringAsFixed(1)}%',
              color: Colors.purple,
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Suggestions
        if (analysis.suggestions.isNotEmpty) ...[
          const Text(
            'Suggestions',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ...analysis.suggestions.map(
            (suggestion) => Card(
              child: ListTile(
                leading: const Icon(Icons.lightbulb_outline, color: Colors.amber),
                title: Text(suggestion),
                dense: true,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Color _getScoreColor(double score) {
    if (score >= 80) return Colors.green;
    if (score >= 60) return Colors.orange;
    return Colors.red;
  }

  String _getScoreLabel(double score) {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Needs Improvement';
  }
}

class _MetricCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _MetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(
              label,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _UtilizationChartsSection extends StatelessWidget {
  final UtilizationMetrics metrics;

  const _UtilizationChartsSection({required this.metrics});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Utilization Analysis',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),

        // Overall Utilization
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Overall Utilization',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                LinearProgressIndicator(
                  value: metrics.overallUtilization / 100,
                  minHeight: 20,
                  backgroundColor: Colors.grey.shade200,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    metrics.overallUtilization >= 70
                        ? Colors.green
                        : metrics.overallUtilization >= 50
                            ? Colors.orange
                            : Colors.red,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${metrics.overallUtilization.toStringAsFixed(1)}%',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // By Hour Chart
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Utilization by Hour',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  height: 200,
                  child: BarChart(
                    BarChartData(
                      alignment: BarChartAlignment.spaceAround,
                      maxY: 100,
                      barGroups: metrics.byHour.asMap().entries.map((entry) {
                        final index = entry.key;
                        final metric = entry.value;
                        return BarChartGroupData(
                          x: index,
                          barRods: [
                            BarChartRodData(
                              toY: metric.utilizationRate,
                              color: metrics.peakHours.contains(
                                      int.tryParse(metric.label.split(':')[0]))
                                  ? Colors.green
                                  : Colors.blue,
                              width: 16,
                            ),
                          ],
                        );
                      }).toList(),
                      titlesData: FlTitlesData(
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 40,
                            getTitlesWidget: (value, meta) {
                              return Text('${value.toInt()}%');
                            },
                          ),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            getTitlesWidget: (value, meta) {
                              if (value.toInt() >= metrics.byHour.length) {
                                return const Text('');
                              }
                              final hour = metrics.byHour[value.toInt()].label;
                              return Text(
                                hour.split(':')[0],
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
                      gridData: FlGridData(
                        show: true,
                        drawVerticalLine: false,
                      ),
                      borderData: FlBorderData(show: false),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Peak Hours
        if (metrics.peakHours.isNotEmpty)
          Card(
            color: Colors.green.shade50,
            child: ListTile(
              leading: const Icon(Icons.trending_up, color: Colors.green),
              title: const Text('Peak Hours'),
              subtitle: Text(
                metrics.peakHours.map((h) => '${h}:00').join(', '),
              ),
            ),
          ),
      ],
    );
  }
}

class _GapVisualizationSection extends StatelessWidget {
  final GapIdentification gaps;

  const _GapVisualizationSection({required this.gaps});

  @override
  Widget build(BuildContext context) {
    final timeFormat = DateFormat('h:mm a');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Schedule Gaps',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),

        // Summary Card
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    children: [
                      const Text(
                        'Total Gaps',
                        style: TextStyle(fontSize: 12),
                      ),
                      Text(
                        gaps.gaps.length.toString(),
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    children: [
                      const Text(
                        'Fillable',
                        style: TextStyle(fontSize: 12),
                      ),
                      Text(
                        gaps.fillableGapCount.toString(),
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: Colors.green,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    children: [
                      const Text(
                        'Total Time',
                        style: TextStyle(fontSize: 12),
                      ),
                      Text(
                        '${gaps.totalGapMinutes} min',
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: Colors.orange,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Gap List
        if (gaps.gaps.isNotEmpty) ...[
          const Text(
            'Gap Details',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ...gaps.gaps.map(
            (gap) => Card(
              color: gap.isFillable ? Colors.green.shade50 : null,
              child: ListTile(
                leading: Icon(
                  gap.isFillable ? Icons.add_circle : Icons.info_outline,
                  color: gap.isFillable ? Colors.green : Colors.grey,
                ),
                title: Text(
                  '${timeFormat.format(gap.gapStart)} - ${timeFormat.format(gap.gapEnd)}',
                ),
                subtitle: Text(gap.recommendedAction),
                trailing: Chip(
                  label: Text('${gap.durationMinutes} min'),
                  backgroundColor:
                      gap.isFillable ? Colors.green : Colors.grey.shade200,
                ),
              ),
            ),
          ),
        ],

        // Recommendations
        if (gaps.recommendations.isNotEmpty) ...[
          const SizedBox(height: 12),
          ...gaps.recommendations.map(
            (rec) => Card(
              child: ListTile(
                leading: const Icon(Icons.tips_and_updates, color: Colors.amber),
                title: Text(rec),
                dense: true,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _OptimizationSuggestionsSection extends StatelessWidget {
  final ScheduleOptimizationSuggestions suggestions;

  const _OptimizationSuggestionsSection({required this.suggestions});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Optimization Suggestions',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 12),

        // Improvement Potential
        Card(
          elevation: 4,
          color: Colors.blue.shade50,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                const Text(
                  'Potential Improvement',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    Column(
                      children: [
                        const Text('Current', style: TextStyle(fontSize: 12)),
                        Text(
                          '${suggestions.currentEfficiencyScore.toStringAsFixed(0)}%',
                          style: const TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const Icon(Icons.arrow_forward, size: 32),
                    Column(
                      children: [
                        const Text('Potential', style: TextStyle(fontSize: 12)),
                        Text(
                          '${suggestions.potentialEfficiencyScore.toStringAsFixed(0)}%',
                          style: const TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.green,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  suggestions.summary,
                  style: const TextStyle(fontSize: 14),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Adjustments
        if (suggestions.adjustments.isNotEmpty) ...[
          const Text(
            'Recommended Adjustments',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ...suggestions.adjustments.map(
            (adjustment) => Card(
              child: ExpansionTile(
                leading: Icon(
                  _getPriorityIcon(adjustment.priority),
                  color: _getPriorityColor(adjustment.priority),
                ),
                title: Text(
                  _formatAdjustmentType(adjustment.adjustmentType),
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                subtitle: Text(adjustment.reason),
                trailing: Chip(
                  label: Text(
                    '+${adjustment.expectedImprovement.toStringAsFixed(0)}%',
                  ),
                  backgroundColor: Colors.green.shade100,
                ),
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Current',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey,
                                    ),
                                  ),
                                  Text(
                                    adjustment.currentValue.toString(),
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.arrow_forward),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Suggested',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey,
                                    ),
                                  ),
                                  Text(
                                    adjustment.suggestedValue.toString(),
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.green,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed: () {
                            // TODO: Implement apply adjustment
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                    'Adjustment application coming soon!'),
                              ),
                            );
                          },
                          icon: const Icon(Icons.check),
                          label: const Text('Apply Adjustment'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.green,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }

  IconData _getPriorityIcon(String priority) {
    switch (priority.toLowerCase()) {
      case 'high':
        return Icons.priority_high;
      case 'medium':
        return Icons.trending_up;
      case 'low':
        return Icons.info_outline;
      default:
        return Icons.info;
    }
  }

  Color _getPriorityColor(String priority) {
    switch (priority.toLowerCase()) {
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      case 'low':
        return Colors.blue;
      default:
        return Colors.grey;
    }
  }

  String _formatAdjustmentType(String type) {
    return type
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
}
