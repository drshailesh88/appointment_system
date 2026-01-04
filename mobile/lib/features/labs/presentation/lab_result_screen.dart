import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../core/models/lab_result.dart';
import '../../../core/providers/labs_provider.dart';

/// Lab result detail screen showing all results for an order
class LabResultScreen extends ConsumerStatefulWidget {
  final String orderId;
  final DateTime orderDate;
  final String? patientName;

  const LabResultScreen({
    super.key,
    required this.orderId,
    required this.orderDate,
    this.patientName,
  });

  @override
  ConsumerState<LabResultScreen> createState() => _LabResultScreenState();
}

class _LabResultScreenState extends ConsumerState<LabResultScreen> {
  @override
  void initState() {
    super.initState();

    // Load results
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(labResultsProvider.notifier).loadOrderResults(widget.orderId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(labResultsProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Lab Results'),
            Text(
              DateFormat('MMM dd, yyyy').format(widget.orderDate),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.white70,
                  ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Share Results',
            onPressed: () => _shareResults(),
          ),
          IconButton(
            icon: const Icon(Icons.picture_as_pdf),
            tooltip: 'View PDF Report',
            onPressed: () => _viewPdfReport(),
          ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? _buildError(state.error!)
              : _buildResults(state),
    );
  }

  Widget _buildError(String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          Text(
            'Error loading results',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(error),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () => ref
                .read(labResultsProvider.notifier)
                .loadOrderResults(widget.orderId),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildResults(LabResultsState state) {
    if (state.results.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.science_outlined,
              size: 64,
              color: Colors.grey[400],
            ),
            const SizedBox(height: 16),
            Text(
              'No results yet',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 8),
            const Text('Results will appear here when available'),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Summary card
        _buildSummaryCard(state),

        // Results by category
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              ...state.resultsByCategory.entries.map((entry) {
                return _buildCategorySection(entry.key, entry.value);
              }),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSummaryCard(LabResultsState state) {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Theme.of(context).primaryColor.withOpacity(0.1),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _SummaryItem(
            icon: Icons.check_circle,
            label: 'Total Tests',
            value: state.totalTests.toString(),
            color: Colors.blue,
          ),
          _SummaryItem(
            icon: Icons.warning_amber,
            label: 'Abnormal',
            value: state.abnormalCount.toString(),
            color: Colors.orange,
          ),
          if (state.criticalCount > 0)
            _SummaryItem(
              icon: Icons.error,
              label: 'Critical',
              value: state.criticalCount.toString(),
              color: Colors.red,
            ),
        ],
      ),
    );
  }

  Widget _buildCategorySection(String category, List<LabResult> results) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 16),
        Text(
          category,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).primaryColor,
              ),
        ),
        const SizedBox(height: 8),
        ...results.map((result) => _buildResultCard(result)),
      ],
    );
  }

  Widget _buildResultCard(LabResult result) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () => _navigateToTrends(result),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Test name and abnormal indicator
              Row(
                children: [
                  Expanded(
                    child: Text(
                      result.testName,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                  ),
                  if (result.isAbnormal)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: result.isCritical ? Colors.red : Colors.orange,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        result.isCritical ? 'CRITICAL' : 'ABNORMAL',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Value and unit
              Row(
                children: [
                  Text(
                    'Result:',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    result.displayValue,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: result.isAbnormal
                              ? (result.isCritical ? Colors.red : Colors.orange)
                              : Colors.green,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Reference range
              Row(
                children: [
                  Text(
                    'Reference Range:',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    result.referenceRangeDisplay,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),

              // Visual indicator
              if (result.valueNumeric != null &&
                  result.referenceRangeMin != null &&
                  result.referenceRangeMax != null)
                _buildRangeIndicator(result),

              // Notes
              if (result.notes != null && result.notes!.isNotEmpty) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.blue.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          result.notes!,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRangeIndicator(LabResult result) {
    final min = result.referenceRangeMin!;
    final max = result.referenceRangeMax!;
    final value = result.valueNumeric!;

    // Calculate position (0.0 to 1.0)
    double position;
    if (value < min) {
      position = 0.0;
    } else if (value > max) {
      position = 1.0;
    } else {
      position = (value - min) / (max - min);
    }

    return Column(
      children: [
        const SizedBox(height: 12),
        Stack(
          children: [
            // Background bar
            Container(
              height: 8,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.red,
                    Colors.orange,
                    Colors.green,
                    Colors.orange,
                    Colors.red,
                  ],
                  stops: const [0.0, 0.2, 0.5, 0.8, 1.0],
                ),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            // Value indicator
            Positioned(
              left: position * (MediaQuery.of(context).size.width - 64) - 4,
              top: 0,
              child: Container(
                width: 16,
                height: 8,
                decoration: BoxDecoration(
                  color: Colors.black,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              min.toString(),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            Text(
              max.toString(),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ],
    );
  }

  void _navigateToTrends(LabResult result) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => LabTrendScreen(
          resultId: result.id,
          testName: result.testName,
          patientName: widget.patientName,
        ),
      ),
    );
  }

  void _shareResults() {
    // TODO: Implement share functionality
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Share functionality coming soon')),
    );
  }

  void _viewPdfReport() {
    // TODO: Implement PDF viewer
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('PDF viewer coming soon')),
    );
  }
}

/// Summary item widget
class _SummaryItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _SummaryItem({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
              ),
        ),
      ],
    );
  }
}

/// Lab trend screen showing historical trends
class LabTrendScreen extends ConsumerWidget {
  final String resultId;
  final String testName;
  final String? patientName;

  const LabTrendScreen({
    super.key,
    required this.resultId,
    required this.testName,
    this.patientName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final trendAsync = ref.watch(labResultWithTrendsProvider(resultId));

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(testName),
            if (patientName != null)
              Text(
                patientName!,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.white70,
                    ),
              ),
          ],
        ),
      ),
      body: trendAsync.when(
        data: (data) => _buildTrendView(context, data),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: Colors.red),
              const SizedBox(height: 16),
              Text('Error: $error'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTrendView(BuildContext context, LabResultWithTrends data) {
    final result = data.result;
    final trend = data.trend;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Current value card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Latest Result',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        result.displayValue,
                        style:
                            Theme.of(context).textTheme.headlineMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: result.isAbnormal
                                      ? Colors.orange
                                      : Colors.green,
                                ),
                      ),
                      if (result.isAbnormal)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: result.isCritical
                                ? Colors.red
                                : Colors.orange,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            result.isCritical ? 'CRITICAL' : 'ABNORMAL',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Reference: ${result.referenceRangeDisplay}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  if (result.resultDate != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Date: ${DateFormat('MMM dd, yyyy').format(result.resultDate!)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Trend chart
          if (trend.dataPoints.isNotEmpty) ...[
            Text(
              'Historical Trend',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: SizedBox(
                  height: 250,
                  child: _buildTrendChart(context, trend),
                ),
              ),
            ),
          ] else
            const Card(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Center(
                  child: Text('No historical data available'),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTrendChart(BuildContext context, LabResultTrend trend) {
    final spots = trend.dataPoints
        .asMap()
        .entries
        .map((entry) => FlSpot(
              entry.key.toDouble(),
              entry.value.value,
            ))
        .toList();

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: true),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return Text(
                  value.toStringAsFixed(1),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index < 0 || index >= trend.dataPoints.length) {
                  return const Text('');
                }
                final date = trend.dataPoints[index].date;
                return Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Text(
                    DateFormat('MMM\nyy').format(date),
                    style: const TextStyle(fontSize: 9),
                    textAlign: TextAlign.center,
                  ),
                );
              },
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: true),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Theme.of(context).primaryColor,
            barWidth: 3,
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, barData, index) {
                final isAbnormal = trend.dataPoints[index].isAbnormal;
                return FlDotCirclePainter(
                  radius: 4,
                  color: isAbnormal ? Colors.red : Colors.green,
                  strokeWidth: 1,
                  strokeColor: Colors.white,
                );
              },
            ),
          ),
        ],
        // Reference range bands
        extraLinesData: ExtraLinesData(
          horizontalLines: [
            if (trend.referenceRangeMin != null)
              HorizontalLine(
                y: trend.referenceRangeMin!,
                color: Colors.orange.withOpacity(0.3),
                strokeWidth: 1,
                dashArray: [5, 5],
              ),
            if (trend.referenceRangeMax != null)
              HorizontalLine(
                y: trend.referenceRangeMax!,
                color: Colors.orange.withOpacity(0.3),
                strokeWidth: 1,
                dashArray: [5, 5],
              ),
          ],
        ),
      ),
    );
  }
}
