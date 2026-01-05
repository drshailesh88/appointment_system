import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/models/clinic.dart';
import '../providers/clinic_provider.dart';

/// Clinic detail screen
class ClinicDetailScreen extends ConsumerStatefulWidget {
  final String clinicId;

  const ClinicDetailScreen({
    super.key,
    required this.clinicId,
  });

  @override
  ConsumerState<ClinicDetailScreen> createState() =>
      _ClinicDetailScreenState();
}

class _ClinicDetailScreenState extends ConsumerState<ClinicDetailScreen> {
  Clinic? _clinic;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadClinic();
  }

  Future<void> _loadClinic() async {
    setState(() => _isLoading = true);
    final clinic = await ref
        .read(clinicProvider.notifier)
        .getClinic(widget.clinicId);
    if (mounted) {
      setState(() {
        _clinic = clinic;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Loading...')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_clinic == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Error')),
        body: const Center(child: Text('Clinic not found')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_clinic!.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: _editClinic,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadClinic,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 24),
              _buildContactInfo(),
              const SizedBox(height: 24),
              _buildLocationInfo(),
              const SizedBox(height: 24),
              _buildStatsSection(),
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.location_city,
                  size: 40,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _clinic!.name,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      if (_clinic!.code != null)
                        Text(
                          'Code: ${_clinic!.code}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                    ],
                  ),
                ),
                Chip(
                  label: Text(_clinic!.isActive ? 'Active' : 'Inactive'),
                  backgroundColor: _clinic!.isActive
                      ? Colors.green.shade100
                      : Colors.grey.shade300,
                ),
              ],
            ),
            if (_clinic!.description != null) ...[
              const Divider(),
              Text(
                _clinic!.description!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildContactInfo() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Contact Information',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Divider(),
            if (_clinic!.phone != null)
              _InfoRow(
                icon: Icons.phone,
                label: 'Phone',
                value: _clinic!.phone!,
              ),
            if (_clinic!.email != null)
              _InfoRow(
                icon: Icons.email,
                label: 'Email',
                value: _clinic!.email!,
              ),
            if (_clinic!.website != null)
              _InfoRow(
                icon: Icons.language,
                label: 'Website',
                value: _clinic!.website!,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildLocationInfo() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Location',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Divider(),
            _InfoRow(
              icon: Icons.location_on,
              label: 'Address',
              value: _clinic!.address,
            ),
            _InfoRow(
              icon: Icons.location_city,
              label: 'City',
              value: _clinic!.city,
            ),
            _InfoRow(
              icon: Icons.map,
              label: 'State',
              value: _clinic!.state,
            ),
            _InfoRow(
              icon: Icons.pin_drop,
              label: 'Postal Code',
              value: _clinic!.postalCode,
            ),
            _InfoRow(
              icon: Icons.flag,
              label: 'Country',
              value: _clinic!.country,
            ),
            if (_clinic!.hasCoordinates) ...[
              const Divider(),
              _InfoRow(
                icon: Icons.my_location,
                label: 'Coordinates',
                value: '${_clinic!.latitude}, ${_clinic!.longitude}',
              ),
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: _openInMaps,
                icon: const Icon(Icons.map),
                label: const Text('Open in Maps'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatsSection() {
    final dateFormat = DateFormat('dd MMM yyyy');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Statistics',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Divider(),
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    icon: Icons.people,
                    label: 'Staff',
                    value: '${_clinic!.staffCount}',
                    color: Colors.blue,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    icon: Icons.person,
                    label: 'Patients',
                    value: '${_clinic!.patientCount}',
                    color: Colors.green,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _InfoRow(
              icon: Icons.calendar_today,
              label: 'Created',
              value: dateFormat.format(_clinic!.createdAt),
            ),
            _InfoRow(
              icon: Icons.update,
              label: 'Updated',
              value: dateFormat.format(_clinic!.updatedAt),
            ),
          ],
        ),
      ),
    );
  }

  void _editClinic() {
    // TODO: Implement edit dialog
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Edit clinic - Coming soon')),
    );
  }

  void _openInMaps() {
    // TODO: Open in maps app
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Opening in maps - Coming soon')),
    );
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
            width: 120,
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

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Icon(icon, size: 32, color: color),
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
            style: TextStyle(
              fontSize: 12,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
