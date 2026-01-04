import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/providers/reports_provider.dart';

/// Main reports screen with report generation and history
class ReportsScreen extends ConsumerStatefulWidget {
  const ReportsScreen({super.key});

  @override
  ConsumerState<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends ConsumerState<ReportsScreen> {
  String _selectedReportType = 'daily';
  String _selectedFormat = 'pdf';
  DateTime? _dateFrom;
  DateTime? _dateTo;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(reportsProvider.notifier).loadRecentReports();
    });
  }

  @override
  Widget build(BuildContext context) {
    final reportsState = ref.watch(reportsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Reports & Exports'),
        actions: [
          IconButton(
            icon: const Icon(Icons.schedule),
            tooltip: 'Scheduled Reports',
            onPressed: () => context.pushNamed('scheduled-reports'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(reportsProvider.notifier).loadRecentReports(),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Generate Report Section
              _buildGenerateReportSection(context, reportsState),
              const SizedBox(height: 32),

              // Recent Reports Section
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Recent Reports',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  if (reportsState.recentReports.isNotEmpty)
                    TextButton.icon(
                      onPressed: () => _showClearHistoryDialog(context),
                      icon: const Icon(Icons.delete_outline, size: 18),
                      label: const Text('Clear'),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              _buildRecentReportsList(context, reportsState),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGenerateReportSection(
    BuildContext context,
    ReportsState state,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.analytics_outlined,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Generate New Report',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Report Type Selection
            Text(
              'Report Type',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _selectedReportType,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              ),
              items: const [
                DropdownMenuItem(value: 'daily', child: Text('Daily Report')),
                DropdownMenuItem(value: 'weekly', child: Text('Weekly Report')),
                DropdownMenuItem(value: 'monthly', child: Text('Monthly Report')),
                DropdownMenuItem(value: 'custom', child: Text('Custom Date Range')),
                DropdownMenuItem(
                    value: 'appointments', child: Text('Appointments Summary')),
                DropdownMenuItem(value: 'revenue', child: Text('Revenue Analysis')),
                DropdownMenuItem(
                    value: 'doctor_utilization',
                    child: Text('Doctor Utilization')),
              ],
              onChanged: (value) {
                setState(() => _selectedReportType = value!);
              },
            ),
            const SizedBox(height: 16),

            // Date Range Picker (for custom reports)
            if (_selectedReportType == 'custom') ...[
              Text(
                'Date Range',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _selectDate(context, true),
                      icon: const Icon(Icons.calendar_today, size: 18),
                      label: Text(
                        _dateFrom != null
                            ? DateFormat('dd MMM yyyy').format(_dateFrom!)
                            : 'From Date',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.arrow_forward, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _selectDate(context, false),
                      icon: const Icon(Icons.calendar_today, size: 18),
                      label: Text(
                        _dateTo != null
                            ? DateFormat('dd MMM yyyy').format(_dateTo!)
                            : 'To Date',
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],

            // Format Selection
            Text(
              'Export Format',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                  value: 'pdf',
                  label: Text('PDF'),
                  icon: Icon(Icons.picture_as_pdf),
                ),
                ButtonSegment(
                  value: 'excel',
                  label: Text('Excel'),
                  icon: Icon(Icons.table_chart),
                ),
                ButtonSegment(
                  value: 'csv',
                  label: Text('CSV'),
                  icon: Icon(Icons.grid_on),
                ),
              ],
              selected: {_selectedFormat},
              onSelectionChanged: (Set<String> selection) {
                setState(() => _selectedFormat = selection.first);
              },
            ),
            const SizedBox(height: 24),

            // Generate Button
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: state.isGenerating ? null : _generateReport,
                icon: state.isGenerating
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.file_download),
                label: Text(state.isGenerating
                    ? 'Generating...'
                    : 'Generate & Download'),
              ),
            ),

            // Error message
            if (state.error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline, color: Colors.red.shade700),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        state.error!,
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 18),
                      onPressed: () =>
                          ref.read(reportsProvider.notifier).clearError(),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRecentReportsList(BuildContext context, ReportsState state) {
    if (state.isLoading && state.recentReports.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (state.recentReports.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            children: [
              Icon(
                Icons.description_outlined,
                size: 64,
                color: Colors.grey.shade400,
              ),
              const SizedBox(height: 16),
              Text(
                'No reports yet',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Colors.grey,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                'Generate your first report above',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey.shade600,
                    ),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: state.recentReports.length,
      itemBuilder: (context, index) {
        final report = state.recentReports[index];
        final isDownloading = state.currentReportId == report.id &&
            state.downloadProgress != null;

        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              child: Text(
                report.formatIcon,
                style: const TextStyle(fontSize: 20),
              ),
            ),
            title: Text(report.displayName),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${DateFormat('dd MMM yyyy, HH:mm').format(report.createdAt)} • ${_formatFileSize(report.fileSize)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (isDownloading) ...[
                  const SizedBox(height: 4),
                  LinearProgressIndicator(
                    value: state.downloadProgress,
                  ),
                ],
              ],
            ),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (report.status == 'ready' && !isDownloading) ...[
                  IconButton(
                    icon: const Icon(Icons.visibility),
                    tooltip: 'Preview',
                    onPressed: () => _previewReport(context, report),
                  ),
                  IconButton(
                    icon: const Icon(Icons.share),
                    tooltip: 'Share',
                    onPressed: () => _shareReport(report),
                  ),
                ] else if (report.status == 'generating')
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  ),
              ],
            ),
            onTap: () => _previewReport(context, report),
          ),
        );
      },
    );
  }

  Future<void> _selectDate(BuildContext context, bool isFromDate) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: isFromDate
          ? (_dateFrom ?? DateTime.now())
          : (_dateTo ?? DateTime.now()),
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );

    if (picked != null) {
      setState(() {
        if (isFromDate) {
          _dateFrom = picked;
        } else {
          _dateTo = picked;
        }
      });
    }
  }

  Future<void> _generateReport() async {
    // Validate custom date range
    if (_selectedReportType == 'custom') {
      if (_dateFrom == null || _dateTo == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Please select both from and to dates'),
            backgroundColor: Colors.orange,
          ),
        );
        return;
      }

      if (_dateTo!.isBefore(_dateFrom!)) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('To date must be after from date'),
            backgroundColor: Colors.orange,
          ),
        );
        return;
      }
    }

    final report = await ref.read(reportsProvider.notifier).generateReport(
          reportType: _selectedReportType,
          format: _selectedFormat,
          dateFrom:
              _dateFrom != null ? DateFormat('yyyy-MM-dd').format(_dateFrom!) : null,
          dateTo: _dateTo != null ? DateFormat('yyyy-MM-dd').format(_dateTo!) : null,
        );

    if (report != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${report.displayName} generated successfully'),
          backgroundColor: Colors.green,
          action: SnackBarAction(
            label: 'View',
            textColor: Colors.white,
            onPressed: () => _previewReport(context, report),
          ),
        ),
      );

      // Auto-download
      _downloadAndPreview(report);
    }
  }

  Future<void> _downloadAndPreview(Report report) async {
    final filePath = await ref.read(reportsProvider.notifier).downloadReport(report.id);

    if (filePath != null && mounted) {
      context.pushNamed(
        'report-preview',
        extra: {'reportId': report.id, 'filePath': filePath},
      );
    }
  }

  Future<void> _previewReport(BuildContext context, Report report) async {
    // Check if already downloaded
    final reportService = ref.read(reportServiceProvider);
    final localPath = await reportService.getLocalReportPath(report.id);

    if (localPath != null) {
      if (mounted) {
        context.pushNamed(
          'report-preview',
          extra: {'reportId': report.id, 'filePath': localPath},
        );
      }
    } else {
      // Download first
      _downloadAndPreview(report);
    }
  }

  Future<void> _shareReport(Report report) async {
    final reportService = ref.read(reportServiceProvider);
    final localPath = await reportService.getLocalReportPath(report.id);

    if (localPath != null) {
      await ref.read(reportsProvider.notifier).shareReport(
            localPath,
            reportName: report.displayName,
          );
    } else {
      // Download first then share
      final filePath =
          await ref.read(reportsProvider.notifier).downloadReport(report.id);
      if (filePath != null) {
        await ref.read(reportsProvider.notifier).shareReport(
              filePath,
              reportName: report.displayName,
            );
      }
    }
  }

  Future<void> _showClearHistoryDialog(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear History'),
        content: const Text(
          'This will remove all reports from the history. Downloaded files will remain on your device.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Clear'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      // Clear all reports (implementation depends on backend)
      // For now, just reload
      ref.read(reportsProvider.notifier).loadRecentReports();
    }
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}
