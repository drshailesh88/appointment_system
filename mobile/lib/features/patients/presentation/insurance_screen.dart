import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/models/insurance.dart';
import '../../../core/providers/insurance_provider.dart';

/// Insurance management screen for a patient
class InsuranceScreen extends ConsumerStatefulWidget {
  final String patientId;
  final String patientName;

  const InsuranceScreen({
    super.key,
    required this.patientId,
    required this.patientName,
  });

  @override
  ConsumerState<InsuranceScreen> createState() => _InsuranceScreenState();
}

class _InsuranceScreenState extends ConsumerState<InsuranceScreen> {
  @override
  void initState() {
    super.initState();
    // Load insurance policies on init
    Future.microtask(() {
      ref
          .read(insuranceProvider.notifier)
          .loadPatientInsurance(widget.patientId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(insuranceProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text('Insurance - ${widget.patientName}'),
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? _ErrorView(
                  error: state.error!,
                  onRetry: () {
                    ref
                        .read(insuranceProvider.notifier)
                        .loadPatientInsurance(widget.patientId);
                  },
                )
              : state.insurances.isEmpty
                  ? _EmptyView(
                      onAddPressed: () => _showAddInsuranceDialog(),
                    )
                  : RefreshIndicator(
                      onRefresh: () async {
                        await ref
                            .read(insuranceProvider.notifier)
                            .loadPatientInsurance(widget.patientId);
                      },
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: state.insurances.length,
                        itemBuilder: (context, index) {
                          final insurance = state.insurances[index];
                          return _InsuranceCard(
                            insurance: insurance,
                            onTap: () => _showInsuranceDetails(insurance.id),
                            onVerify: () => _verifyInsurance(insurance.id),
                            onEdit: () => _showEditInsuranceDialog(insurance.id),
                            onDelete: () => _deleteInsurance(insurance.id),
                          );
                        },
                      ),
                    ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddInsuranceDialog,
        icon: const Icon(Icons.add),
        label: const Text('Add Insurance'),
      ),
    );
  }

  void _showInsuranceDetails(String insuranceId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => InsuranceDetailsScreen(insuranceId: insuranceId),
      ),
    );
  }

  Future<void> _verifyInsurance(String insuranceId) async {
    // Show verification dialog
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => _VerificationDialog(insuranceId: insuranceId),
    );

    if (result == true && mounted) {
      // Reload insurance list to update verification status
      ref
          .read(insuranceProvider.notifier)
          .loadPatientInsurance(widget.patientId);
    }
  }

  void _showAddInsuranceDialog() {
    showDialog(
      context: context,
      builder: (context) => _AddEditInsuranceDialog(
        patientId: widget.patientId,
      ),
    );
  }

  void _showEditInsuranceDialog(String insuranceId) {
    showDialog(
      context: context,
      builder: (context) => _AddEditInsuranceDialog(
        patientId: widget.patientId,
        insuranceId: insuranceId,
      ),
    );
  }

  Future<void> _deleteInsurance(String insuranceId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Insurance'),
        content: const Text(
            'Are you sure you want to delete this insurance policy?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final success =
          await ref.read(insuranceProvider.notifier).deleteInsurance(insuranceId);

      if (mounted) {
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Insurance deleted successfully')),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to delete insurance')),
          );
        }
      }
    }
  }
}

/// Empty state view
class _EmptyView extends StatelessWidget {
  final VoidCallback onAddPressed;

  const _EmptyView({required this.onAddPressed});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.health_and_safety_outlined,
            size: 64,
            color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'No insurance policies',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          const Text('Add insurance information for this patient'),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: onAddPressed,
            icon: const Icon(Icons.add),
            label: const Text('Add Insurance'),
          ),
        ],
      ),
    );
  }
}

/// Error view
class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: Theme.of(context).colorScheme.error,
          ),
          const SizedBox(height: 16),
          Text(
            'Error loading insurance',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(error),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}

/// Insurance card widget
class _InsuranceCard extends StatelessWidget {
  final InsuranceListItem insurance;
  final VoidCallback onTap;
  final VoidCallback onVerify;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const _InsuranceCard({
    required this.insurance,
    required this.onTap,
    required this.onVerify,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isExpired = insurance.coverageEndDate != null &&
        insurance.coverageEndDate!.isBefore(DateTime.now());
    final isExpiringSoon = insurance.coverageEndDate != null &&
        insurance.coverageEndDate!
                .difference(DateTime.now())
                .inDays <=
            30 &&
        !isExpired;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                insurance.providerName,
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(
                                      fontWeight: FontWeight.bold,
                                    ),
                              ),
                            ),
                            if (insurance.isPrimary) ...[
                              const SizedBox(width: 8),
                              Chip(
                                label: const Text(
                                  'PRIMARY',
                                  style: TextStyle(fontSize: 10),
                                ),
                                padding: EdgeInsets.zero,
                                visualDensity: VisualDensity.compact,
                                backgroundColor:
                                    Theme.of(context).colorScheme.primaryContainer,
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          insurance.policyNumber,
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: Theme.of(context)
                                    .colorScheme
                                    .onSurface
                                    .withOpacity(0.7),
                              ),
                        ),
                      ],
                    ),
                  ),
                  PopupMenuButton(
                    itemBuilder: (context) => [
                      const PopupMenuItem(
                        value: 'verify',
                        child: Row(
                          children: [
                            Icon(Icons.verified_user),
                            SizedBox(width: 8),
                            Text('Verify Eligibility'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'edit',
                        child: Row(
                          children: [
                            Icon(Icons.edit),
                            SizedBox(width: 8),
                            Text('Edit'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete),
                            SizedBox(width: 8),
                            Text('Delete'),
                          ],
                        ),
                      ),
                    ],
                    onSelected: (value) {
                      switch (value) {
                        case 'verify':
                          onVerify();
                          break;
                        case 'edit':
                          onEdit();
                          break;
                        case 'delete':
                          onDelete();
                          break;
                      }
                    },
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Coverage info
              if (insurance.coverageEndDate != null) ...[
                Row(
                  children: [
                    Icon(
                      Icons.calendar_today,
                      size: 16,
                      color: isExpired
                          ? Theme.of(context).colorScheme.error
                          : isExpiringSoon
                              ? Colors.orange
                              : Theme.of(context)
                                  .colorScheme
                                  .onSurface
                                  .withOpacity(0.6),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Valid until ${DateFormat('MMM dd, yyyy').format(insurance.coverageEndDate!)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: isExpired
                                ? Theme.of(context).colorScheme.error
                                : isExpiringSoon
                                    ? Colors.orange
                                    : null,
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
              ],

              // Last verification
              if (insurance.lastVerified != null) ...[
                Row(
                  children: [
                    Icon(
                      Icons.check_circle,
                      size: 16,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Last verified ${_formatRelativeTime(insurance.lastVerified!)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.primary,
                          ),
                    ),
                  ],
                ),
              ] else ...[
                Row(
                  children: [
                    Icon(
                      Icons.warning_amber,
                      size: 16,
                      color: Colors.orange,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Not verified',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.orange,
                          ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  String _formatRelativeTime(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inDays > 0) {
      return '${diff.inDays} day${diff.inDays > 1 ? 's' : ''} ago';
    } else if (diff.inHours > 0) {
      return '${diff.inHours} hour${diff.inHours > 1 ? 's' : ''} ago';
    } else if (diff.inMinutes > 0) {
      return '${diff.inMinutes} minute${diff.inMinutes > 1 ? 's' : ''} ago';
    } else {
      return 'just now';
    }
  }
}

/// Insurance details screen
class InsuranceDetailsScreen extends ConsumerWidget {
  final String insuranceId;

  const InsuranceDetailsScreen({
    super.key,
    required this.insuranceId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final insuranceAsync = ref.watch(insuranceDetailsProvider(insuranceId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Insurance Details'),
      ),
      body: insuranceAsync.when(
        data: (insurance) => _InsuranceDetailsView(insurance: insurance),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
      ),
    );
  }
}

/// Insurance details view
class _InsuranceDetailsView extends StatelessWidget {
  final PatientInsurance insurance;

  const _InsuranceDetailsView({required this.insurance});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Provider card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Provider Information',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 12),
                  _DetailRow('Provider', insurance.providerName),
                  _DetailRow('Policy Number', insurance.policyNumber),
                  if (insurance.groupNumber != null)
                    _DetailRow('Group Number', insurance.groupNumber!),
                  _DetailRow('Type', insurance.insuranceTypeDisplay),
                  if (insurance.planName != null)
                    _DetailRow('Plan Name', insurance.planName!),
                  _DetailRow('Status', insurance.isActive ? 'Active' : 'Inactive'),
                  _DetailRow('Priority',
                      insurance.isPrimary ? 'Primary' : 'Secondary'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Coverage card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Coverage Information',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 12),
                  if (insurance.coverageStartDate != null)
                    _DetailRow(
                      'Start Date',
                      DateFormat('MMM dd, yyyy')
                          .format(insurance.coverageStartDate!),
                    ),
                  if (insurance.coverageEndDate != null)
                    _DetailRow(
                      'End Date',
                      DateFormat('MMM dd, yyyy')
                          .format(insurance.coverageEndDate!),
                    ),
                  if (insurance.networkType != null)
                    _DetailRow('Network Type', insurance.networkType!),
                  if (insurance.copayAmount != null)
                    _DetailRow(
                      'Copay Amount',
                      '₹${insurance.copayAmount!.toStringAsFixed(2)}',
                    ),
                  if (insurance.deductibleAmount != null)
                    _DetailRow(
                      'Deductible',
                      '₹${insurance.deductibleAmount!.toStringAsFixed(2)}',
                    ),
                  if (insurance.outOfPocketMax != null)
                    _DetailRow(
                      'Out of Pocket Max',
                      '₹${insurance.outOfPocketMax!.toStringAsFixed(2)}',
                    ),
                  _DetailRow(
                    'Cashless Treatment',
                    insurance.cashlessEnabled ? 'Yes' : 'No',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Subscriber card
          if (insurance.subscriberName != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Subscriber Information',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _DetailRow('Name', insurance.subscriberName!),
                    if (insurance.subscriberRelationship != null)
                      _DetailRow('Relationship',
                          insurance.subscriberRelationshipDisplay),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],

          // TPA card
          if (insurance.tpaName != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'TPA Information',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _DetailRow('TPA Name', insurance.tpaName!),
                    if (insurance.tpaId != null)
                      _DetailRow('TPA ID', insurance.tpaId!),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Detail row widget
class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withOpacity(0.6),
                  ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Verification dialog
class _VerificationDialog extends ConsumerStatefulWidget {
  final String insuranceId;

  const _VerificationDialog({required this.insuranceId});

  @override
  ConsumerState<_VerificationDialog> createState() =>
      _VerificationDialogState();
}

class _VerificationDialogState extends ConsumerState<_VerificationDialog> {
  bool _isVerifying = false;
  VerificationResult? _result;
  String? _error;

  @override
  void initState() {
    super.initState();
    _performVerification();
  }

  Future<void> _performVerification() async {
    setState(() {
      _isVerifying = true;
      _error = null;
    });

    final result = await ref.read(verificationProvider.notifier).verifyInsurance(
          insuranceId: widget.insuranceId,
        );

    if (mounted) {
      setState(() {
        _isVerifying = false;
        _result = result;
        if (result == null) {
          _error = 'Verification failed';
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Insurance Verification'),
      content: SizedBox(
        width: double.maxFinite,
        child: _isVerifying
            ? const Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Verifying insurance eligibility...'),
                ],
              )
            : _error != null
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: 48,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      const SizedBox(height: 16),
                      Text(_error!),
                    ],
                  )
                : _result != null
                    ? _VerificationResultView(result: _result!)
                    : const SizedBox.shrink(),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, _result?.isSuccess ?? false),
          child: const Text('Close'),
        ),
      ],
    );
  }
}

/// Verification result view
class _VerificationResultView extends StatelessWidget {
  final VerificationResult result;

  const _VerificationResultView({required this.result});

  @override
  Widget build(BuildContext context) {
    if (!result.isSuccess) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.cancel_outlined,
            size: 48,
            color: Theme.of(context).colorScheme.error,
          ),
          const SizedBox(height: 16),
          Text(
            'Verification Failed',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          if (result.errorMessage != null) ...[
            const SizedBox(height: 8),
            Text(result.errorMessage!),
          ],
        ],
      );
    }

    return SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Eligibility status
          Row(
            children: [
              Icon(
                result.isEligible == true
                    ? Icons.check_circle
                    : Icons.cancel,
                color: result.isEligible == true
                    ? Colors.green
                    : Theme.of(context).colorScheme.error,
                size: 32,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  result.isEligible == true
                      ? 'Patient is eligible'
                      : 'Patient is not eligible',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Coverage details
          if (result.coverageDetails != null) ...[
            Text(
              'Coverage Details',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            if (result.coverageDetails!.planName != null)
              _DetailRow('Plan', result.coverageDetails!.planName!),
            if (result.coverageDetails!.networkStatus != null)
              _DetailRow('Network', result.coverageDetails!.networkStatus!),
            if (result.coverageDetails!.remainingCoverage != null)
              _DetailRow(
                'Remaining Coverage',
                '₹${result.coverageDetails!.remainingCoverage!.toStringAsFixed(2)}',
              ),
            const SizedBox(height: 12),
          ],

          // Copay info
          if (result.copayInfo != null && result.copayInfo!.amount != null) ...[
            Text(
              'Copay Information',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            _DetailRow(
              'Copay Amount',
              '₹${result.copayInfo!.amount!.toStringAsFixed(2)}',
            ),
            if (result.copayInfo!.description != null)
              Text(
                result.copayInfo!.description!,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            const SizedBox(height: 12),
          ],

          // Deductible info
          if (result.deductibleInfo != null) ...[
            Text(
              'Deductible Information',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            if (result.deductibleInfo!.totalDeductible != null)
              _DetailRow(
                'Total Deductible',
                '₹${result.deductibleInfo!.totalDeductible!.toStringAsFixed(2)}',
              ),
            if (result.deductibleInfo!.remainingDeductible != null)
              _DetailRow(
                'Remaining',
                '₹${result.deductibleInfo!.remainingDeductible!.toStringAsFixed(2)}',
              ),
          ],

          // Limitations
          if (result.limitations != null) ...[
            const SizedBox(height: 12),
            Text(
              'Limitations',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              result.limitations!,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}

/// Add/Edit insurance dialog (placeholder)
class _AddEditInsuranceDialog extends StatelessWidget {
  final String patientId;
  final String? insuranceId;

  const _AddEditInsuranceDialog({
    required this.patientId,
    this.insuranceId,
  });

  @override
  Widget build(BuildContext context) {
    // TODO: Implement full add/edit form
    return AlertDialog(
      title: Text(insuranceId == null ? 'Add Insurance' : 'Edit Insurance'),
      content: const Text(
        'Insurance form will be implemented here.\n\n'
        'Fields: Provider, Policy Number, Coverage Dates, etc.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            // TODO: Save insurance
            Navigator.pop(context);
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}
