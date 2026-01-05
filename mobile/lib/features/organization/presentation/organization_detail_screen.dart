import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/models/organization.dart';
import '../providers/organization_provider.dart';
import '../providers/clinic_provider.dart';

/// Organization detail screen
class OrganizationDetailScreen extends ConsumerStatefulWidget {
  final String organizationId;

  const OrganizationDetailScreen({
    super.key,
    required this.organizationId,
  });

  @override
  ConsumerState<OrganizationDetailScreen> createState() =>
      _OrganizationDetailScreenState();
}

class _OrganizationDetailScreenState
    extends ConsumerState<OrganizationDetailScreen> {
  Organization? _organization;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadOrganization();
  }

  Future<void> _loadOrganization() async {
    setState(() => _isLoading = true);
    final org = await ref
        .read(organizationProvider.notifier)
        .getOrganization(widget.organizationId);
    if (mounted) {
      setState(() {
        _organization = org;
        _isLoading = false;
      });
      // Load clinics for this organization
      ref.read(clinicProvider.notifier).loadClinics();
    }
  }

  @override
  Widget build(BuildContext context) {
    final clinicState = ref.watch(clinicProvider);

    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Loading...')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_organization == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Error')),
        body: const Center(child: Text('Organization not found')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_organization!.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: _editOrganization,
          ),
          IconButton(
            icon: const Icon(Icons.analytics),
            onPressed: _viewAnalytics,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadOrganization,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 24),
              _buildInfoSection(),
              const SizedBox(height: 24),
              _buildClinicsSection(clinicState),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            if (_organization!.logoUrl != null)
              CircleAvatar(
                backgroundImage: NetworkImage(_organization!.logoUrl!),
                radius: 40,
              )
            else
              CircleAvatar(
                backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                radius: 40,
                child: Text(
                  _organization!.name[0].toUpperCase(),
                  style: TextStyle(
                    fontSize: 32,
                    color: Theme.of(context).colorScheme.onPrimaryContainer,
                  ),
                ),
              ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _organization!.name,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  if (_organization!.description != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      _organization!.description!,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  const SizedBox(height: 8),
                  Chip(
                    label: Text(_organization!.subscriptionTier.toUpperCase()),
                    backgroundColor: _organization!.isActive
                        ? Colors.green.shade100
                        : Colors.grey.shade300,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoSection() {
    final dateFormat = DateFormat('dd MMM yyyy');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Organization Information',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Divider(),
            _InfoRow(
              icon: Icons.link,
              label: 'Slug',
              value: _organization!.slug,
            ),
            if (_organization!.email != null)
              _InfoRow(
                icon: Icons.email,
                label: 'Email',
                value: _organization!.email!,
              ),
            if (_organization!.phone != null)
              _InfoRow(
                icon: Icons.phone,
                label: 'Phone',
                value: _organization!.phone!,
              ),
            if (_organization!.website != null)
              _InfoRow(
                icon: Icons.language,
                label: 'Website',
                value: _organization!.website!,
              ),
            _InfoRow(
              icon: Icons.business,
              label: 'Max Clinics',
              value: '${_organization!.maxClinics}',
            ),
            _InfoRow(
              icon: Icons.people,
              label: 'Max Users',
              value: '${_organization!.maxUsers}',
            ),
            _InfoRow(
              icon: Icons.calendar_today,
              label: 'Created',
              value: dateFormat.format(_organization!.createdAt),
            ),
            if (_organization!.subscriptionExpiresAt != null)
              _InfoRow(
                icon: Icons.event_busy,
                label: 'Subscription Expires',
                value: _organization!.subscriptionExpiresAt!,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildClinicsSection(ClinicState state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Clinics (${state.clinics.length})',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            FilledButton.icon(
              onPressed: () => context.push('/clinics/add'),
              icon: const Icon(Icons.add),
              label: const Text('Add Clinic'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (state.isLoading)
          const Center(child: CircularProgressIndicator())
        else if (state.clinics.isEmpty)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(32),
              child: Center(
                child: Text('No clinics yet. Add your first clinic!'),
              ),
            ),
          )
        else
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: state.clinics.length,
            itemBuilder: (context, index) {
              final clinic = state.clinics[index];
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: const Icon(Icons.location_on),
                  title: Text(clinic.name),
                  subtitle: Text(clinic.fullAddress),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (clinic.isActive)
                        const Icon(Icons.check_circle, color: Colors.green)
                      else
                        const Icon(Icons.cancel, color: Colors.red),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                  onTap: () => context.push('/clinics/${clinic.id}'),
                ),
              );
            },
          ),
      ],
    );
  }

  void _editOrganization() {
    // TODO: Implement edit dialog
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Edit organization - Coming soon')),
    );
  }

  void _viewAnalytics() async {
    final analytics = await ref
        .read(organizationProvider.notifier)
        .getConsolidatedAnalytics();

    if (mounted && analytics != null) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Consolidated Analytics'),
          content: SingleChildScrollView(
            child: Text(analytics.toString()),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    }
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey),
          const SizedBox(width: 12),
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }
}
