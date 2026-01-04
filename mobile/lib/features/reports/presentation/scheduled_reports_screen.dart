import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/providers/reports_provider.dart';

/// Scheduled reports management screen
class ScheduledReportsScreen extends ConsumerStatefulWidget {
  const ScheduledReportsScreen({super.key});

  @override
  ConsumerState<ScheduledReportsScreen> createState() =>
      _ScheduledReportsScreenState();
}

class _ScheduledReportsScreenState
    extends ConsumerState<ScheduledReportsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(reportsProvider.notifier).loadScheduledReports();
    });
  }

  @override
  Widget build(BuildContext context) {
    final reportsState = ref.watch(reportsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Scheduled Reports'),
      ),
      body: reportsState.isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () =>
                  ref.read(reportsProvider.notifier).loadScheduledReports(),
              child: reportsState.scheduledReports.isEmpty
                  ? _buildEmptyState(context)
                  : _buildScheduledReportsList(context, reportsState),
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showCreateScheduleDialog(context),
        icon: const Icon(Icons.add),
        label: const Text('New Schedule'),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        Icon(
          Icons.schedule_outlined,
          size: 96,
          color: Colors.grey.shade400,
        ),
        const SizedBox(height: 24),
        Text(
          'No Scheduled Reports',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.grey,
              ),
        ),
        const SizedBox(height: 8),
        Text(
          'Create automated report schedules to receive reports via email regularly',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey.shade600,
              ),
        ),
        const SizedBox(height: 32),
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
                      'How Scheduled Reports Work',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: Colors.blue.shade700,
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Text(
                  '• Set up reports to be generated automatically\n'
                  '• Choose frequency: daily, weekly, or monthly\n'
                  '• Reports are emailed to specified recipients\n'
                  '• Enable or disable schedules anytime',
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildScheduledReportsList(BuildContext context, ReportsState state) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: state.scheduledReports.length,
      itemBuilder: (context, index) {
        final schedule = state.scheduledReports[index];
        return _buildScheduleCard(context, schedule);
      },
    );
  }

  Widget _buildScheduleCard(BuildContext context, ScheduledReport schedule) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Column(
        children: [
          ListTile(
            leading: CircleAvatar(
              backgroundColor: schedule.enabled
                  ? Theme.of(context).colorScheme.primaryContainer
                  : Colors.grey.shade300,
              child: Icon(
                Icons.schedule,
                color: schedule.enabled
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey.shade600,
              ),
            ),
            title: Text(schedule.displayName),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${schedule.frequencyLabel} • ${schedule.format.toUpperCase()}'),
                if (schedule.nextRun != null)
                  Text(
                    'Next run: ${DateFormat('dd MMM yyyy, HH:mm').format(schedule.nextRun!)}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey.shade600,
                        ),
                  ),
              ],
            ),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Switch(
                  value: schedule.enabled,
                  onChanged: (value) => _toggleSchedule(schedule.id, value),
                ),
                PopupMenuButton<String>(
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'edit',
                      child: Row(
                        children: [
                          Icon(Icons.edit, size: 18),
                          SizedBox(width: 8),
                          Text('Edit'),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete, size: 18, color: Colors.red),
                          SizedBox(width: 8),
                          Text('Delete', style: TextStyle(color: Colors.red)),
                        ],
                      ),
                    ),
                  ],
                  onSelected: (value) {
                    if (value == 'edit') {
                      _showEditScheduleDialog(context, schedule);
                    } else if (value == 'delete') {
                      _confirmDelete(context, schedule);
                    }
                  },
                ),
              ],
            ),
          ),
          if (schedule.recipients.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                border: Border(
                  top: BorderSide(color: Colors.grey.shade200),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Recipients:',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Colors.grey.shade600,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: schedule.recipients.map((email) {
                      return Chip(
                        label: Text(email),
                        labelStyle: Theme.of(context).textTheme.bodySmall,
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _toggleSchedule(String scheduleId, bool enabled) async {
    await ref.read(reportsProvider.notifier).toggleScheduledReport(
          scheduleId,
          enabled,
        );

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(enabled ? 'Schedule enabled' : 'Schedule disabled'),
          backgroundColor: enabled ? Colors.green : Colors.orange,
        ),
      );
    }
  }

  Future<void> _confirmDelete(
    BuildContext context,
    ScheduledReport schedule,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Schedule'),
        content: Text(
          'Are you sure you want to delete "${schedule.displayName}"?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(reportsProvider.notifier).deleteScheduledReport(schedule.id);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Schedule deleted'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _showCreateScheduleDialog(BuildContext context) async {
    await showDialog(
      context: context,
      builder: (context) => const _ScheduleReportDialog(),
    );
  }

  Future<void> _showEditScheduleDialog(
    BuildContext context,
    ScheduledReport schedule,
  ) async {
    await showDialog(
      context: context,
      builder: (context) => _ScheduleReportDialog(schedule: schedule),
    );
  }
}

/// Dialog for creating/editing scheduled reports
class _ScheduleReportDialog extends ConsumerStatefulWidget {
  final ScheduledReport? schedule;

  const _ScheduleReportDialog({this.schedule});

  @override
  ConsumerState<_ScheduleReportDialog> createState() =>
      _ScheduleReportDialogState();
}

class _ScheduleReportDialogState extends ConsumerState<_ScheduleReportDialog> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  late String _reportType;
  late String _format;
  late String _frequency;
  late List<String> _recipients;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _reportType = widget.schedule?.reportType ?? 'monthly';
    _format = widget.schedule?.format ?? 'pdf';
    _frequency = widget.schedule?.frequency ?? 'monthly';
    _recipients = List.from(widget.schedule?.recipients ?? []);
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.schedule == null
          ? 'Create Scheduled Report'
          : 'Edit Scheduled Report'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Report Type
              DropdownButtonFormField<String>(
                value: _reportType,
                decoration: const InputDecoration(
                  labelText: 'Report Type',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'daily', child: Text('Daily Report')),
                  DropdownMenuItem(value: 'weekly', child: Text('Weekly Report')),
                  DropdownMenuItem(
                      value: 'monthly', child: Text('Monthly Report')),
                  DropdownMenuItem(
                      value: 'appointments', child: Text('Appointments')),
                  DropdownMenuItem(value: 'revenue', child: Text('Revenue')),
                ],
                onChanged: (value) => setState(() => _reportType = value!),
              ),
              const SizedBox(height: 16),

              // Frequency
              DropdownButtonFormField<String>(
                value: _frequency,
                decoration: const InputDecoration(
                  labelText: 'Frequency',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'daily', child: Text('Daily')),
                  DropdownMenuItem(value: 'weekly', child: Text('Weekly')),
                  DropdownMenuItem(value: 'monthly', child: Text('Monthly')),
                ],
                onChanged: (value) => setState(() => _frequency = value!),
              ),
              const SizedBox(height: 16),

              // Format
              DropdownButtonFormField<String>(
                value: _format,
                decoration: const InputDecoration(
                  labelText: 'Format',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'pdf', child: Text('PDF')),
                  DropdownMenuItem(value: 'excel', child: Text('Excel')),
                  DropdownMenuItem(value: 'csv', child: Text('CSV')),
                ],
                onChanged: (value) => setState(() => _format = value!),
              ),
              const SizedBox(height: 16),

              // Recipients
              const Text(
                'Email Recipients',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _emailController,
                      decoration: const InputDecoration(
                        hintText: 'email@example.com',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.emailAddress,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _addRecipient,
                    icon: const Icon(Icons.add),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (_recipients.isNotEmpty)
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _recipients.map((email) {
                    return Chip(
                      label: Text(email),
                      onDeleted: () {
                        setState(() => _recipients.remove(email));
                      },
                    );
                  }).toList(),
                ),
              if (_recipients.isEmpty)
                Text(
                  'Add at least one recipient',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey.shade600,
                      ),
                ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isSaving ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _isSaving ? null : _saveSchedule,
          child: _isSaving
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(widget.schedule == null ? 'Create' : 'Update'),
        ),
      ],
    );
  }

  void _addRecipient() {
    final email = _emailController.text.trim();
    if (email.isEmpty) return;

    // Basic email validation
    if (!email.contains('@')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a valid email address'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    if (_recipients.contains(email)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Email already added'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() {
      _recipients.add(email);
      _emailController.clear();
    });
  }

  Future<void> _saveSchedule() async {
    if (!_formKey.currentState!.validate()) return;

    if (_recipients.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please add at least one recipient'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);

    try {
      if (widget.schedule == null) {
        // Create new
        await ref.read(reportsProvider.notifier).createScheduledReport(
              reportType: _reportType,
              format: _format,
              frequency: _frequency,
              recipients: _recipients,
            );
      } else {
        // Update existing
        await ref.read(reportsProvider.notifier).updateScheduledReport(
          widget.schedule!.id,
          {
            'report_type': _reportType,
            'format': _format,
            'frequency': _frequency,
            'recipients': _recipients,
          },
        );
      }

      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.schedule == null
                ? 'Schedule created successfully'
                : 'Schedule updated successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }
}
