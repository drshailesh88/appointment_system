import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';

import '../../../core/providers/auth_provider.dart';

/// Reports & Exports Screen
///
/// Phase 8: Allows users to download PDF and Excel reports
class ReportsScreen extends ConsumerStatefulWidget {
  const ReportsScreen({super.key});

  @override
  ConsumerState<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends ConsumerState<ReportsScreen> {
  String _selectedPeriod = 'month';
  DateTime _startDate = DateTime.now().subtract(const Duration(days: 30));
  DateTime _endDate = DateTime.now();
  bool _isDownloading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reports & Exports'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Period Selector
            _buildPeriodSelector(),
            const SizedBox(height: 24),

            // PDF Reports Section
            _buildSectionHeader(
              'PDF Reports',
              Icons.picture_as_pdf,
              Colors.red,
            ),
            const SizedBox(height: 12),
            _buildReportCard(
              title: 'Daily Summary',
              description: 'Overview of today\'s appointments and revenue',
              icon: Icons.today,
              format: 'PDF',
              onDownload: () => _downloadReport('daily-summary', 'pdf'),
            ),
            _buildReportCard(
              title: 'Monthly Analytics',
              description: 'Comprehensive monthly analysis with trends',
              icon: Icons.calendar_month,
              format: 'PDF',
              onDownload: () => _downloadReport('monthly', 'pdf'),
            ),
            _buildReportCard(
              title: 'Revenue Report',
              description: 'Detailed revenue breakdown and collection metrics',
              icon: Icons.attach_money,
              format: 'PDF',
              onDownload: () => _downloadReport('revenue', 'pdf'),
            ),
            const SizedBox(height: 24),

            // Excel Reports Section
            _buildSectionHeader(
              'Excel Exports',
              Icons.table_chart,
              Colors.green,
            ),
            const SizedBox(height: 12),
            _buildReportCard(
              title: 'Appointments Export',
              description: 'All appointment data with patient details',
              icon: Icons.event,
              format: 'Excel',
              formatColor: Colors.green,
              onDownload: () => _downloadReport('appointments', 'excel'),
            ),
            _buildReportCard(
              title: 'Revenue Export',
              description: 'Revenue data with charts and daily breakdown',
              icon: Icons.monetization_on,
              format: 'Excel',
              formatColor: Colors.green,
              onDownload: () => _downloadReport('revenue', 'excel'),
            ),
            _buildReportCard(
              title: 'Doctor Utilization',
              description: 'Doctor productivity and utilization metrics',
              icon: Icons.medical_services,
              format: 'Excel',
              formatColor: Colors.green,
              onDownload: () => _downloadReport('doctors/utilization', 'excel'),
            ),
            _buildReportCard(
              title: 'Patient Demographics',
              description: 'Patient population analysis by location',
              icon: Icons.people,
              format: 'Excel',
              formatColor: Colors.green,
              onDownload: () => _downloadReport('patients/demographics', 'excel'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPeriodSelector() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Report Period',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                _PeriodChip(
                  label: 'Today',
                  value: 'today',
                  selected: _selectedPeriod == 'today',
                  onSelected: (v) => _updatePeriod(v),
                ),
                _PeriodChip(
                  label: 'This Week',
                  value: 'week',
                  selected: _selectedPeriod == 'week',
                  onSelected: (v) => _updatePeriod(v),
                ),
                _PeriodChip(
                  label: 'This Month',
                  value: 'month',
                  selected: _selectedPeriod == 'month',
                  onSelected: (v) => _updatePeriod(v),
                ),
                _PeriodChip(
                  label: 'This Quarter',
                  value: 'quarter',
                  selected: _selectedPeriod == 'quarter',
                  onSelected: (v) => _updatePeriod(v),
                ),
                _PeriodChip(
                  label: 'This Year',
                  value: 'year',
                  selected: _selectedPeriod == 'year',
                  onSelected: (v) => _updatePeriod(v),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _selectDate(isStart: true),
                    icon: const Icon(Icons.calendar_today, size: 18),
                    label: Text(DateFormat('MMM d, y').format(_startDate)),
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 8),
                  child: Text('to'),
                ),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _selectDate(isStart: false),
                    icon: const Icon(Icons.calendar_today, size: 18),
                    label: Text(DateFormat('MMM d, y').format(_endDate)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon, Color color) {
    return Row(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
      ],
    );
  }

  Widget _buildReportCard({
    required String title,
    required String description,
    required IconData icon,
    required String format,
    Color formatColor = Colors.red,
    required VoidCallback onDownload,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: formatColor.withOpacity(0.1),
          child: Icon(icon, color: formatColor),
        ),
        title: Text(title),
        subtitle: Text(
          description,
          style: Theme.of(context).textTheme.bodySmall,
        ),
        trailing: _isDownloading
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : ElevatedButton.icon(
                onPressed: onDownload,
                icon: const Icon(Icons.download, size: 18),
                label: Text(format),
                style: ElevatedButton.styleFrom(
                  backgroundColor: formatColor,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                ),
              ),
      ),
    );
  }

  void _updatePeriod(String period) {
    setState(() {
      _selectedPeriod = period;
      final now = DateTime.now();

      switch (period) {
        case 'today':
          _startDate = now;
          _endDate = now;
          break;
        case 'week':
          _startDate = now.subtract(Duration(days: now.weekday - 1));
          _endDate = now;
          break;
        case 'month':
          _startDate = DateTime(now.year, now.month, 1);
          _endDate = now;
          break;
        case 'quarter':
          final quarterMonth = ((now.month - 1) ~/ 3) * 3 + 1;
          _startDate = DateTime(now.year, quarterMonth, 1);
          _endDate = now;
          break;
        case 'year':
          _startDate = DateTime(now.year, 1, 1);
          _endDate = now;
          break;
      }
    });
  }

  Future<void> _selectDate({required bool isStart}) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: isStart ? _startDate : _endDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );

    if (picked != null) {
      setState(() {
        if (isStart) {
          _startDate = picked;
          if (_startDate.isAfter(_endDate)) {
            _endDate = _startDate;
          }
        } else {
          _endDate = picked;
          if (_endDate.isBefore(_startDate)) {
            _startDate = _endDate;
          }
        }
        _selectedPeriod = 'custom';
      });
    }
  }

  Future<void> _downloadReport(String reportType, String format) async {
    setState(() => _isDownloading = true);

    try {
      // Get the base URL from auth provider
      final authState = ref.read(authProvider);
      final baseUrl = authState.baseUrl ?? 'http://localhost:8000';

      // Build the URL with date parameters
      final startStr = DateFormat('yyyy-MM-dd').format(_startDate);
      final endStr = DateFormat('yyyy-MM-dd').format(_endDate);

      String url;
      if (format == 'pdf') {
        url = '$baseUrl/api/v1/reports/$reportType/pdf'
            '?start_date=$startStr&end_date=$endStr';
      } else {
        url = '$baseUrl/api/v1/reports/$reportType/excel'
            '?start_date=$startStr&end_date=$endStr';
      }

      // Launch URL to download
      final uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Downloading ${reportType.replaceAll('/', ' ')} report...'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        throw Exception('Could not launch URL');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to download report: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isDownloading = false);
      }
    }
  }
}

class _PeriodChip extends StatelessWidget {
  final String label;
  final String value;
  final bool selected;
  final Function(String) onSelected;

  const _PeriodChip({
    required this.label,
    required this.value,
    required this.selected,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => onSelected(value),
    );
  }
}
