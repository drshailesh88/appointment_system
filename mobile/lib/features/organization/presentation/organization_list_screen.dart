import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/organization.dart';
import '../providers/organization_provider.dart';

/// Organization list screen
class OrganizationListScreen extends ConsumerStatefulWidget {
  const OrganizationListScreen({super.key});

  @override
  ConsumerState<OrganizationListScreen> createState() =>
      _OrganizationListScreenState();
}

class _OrganizationListScreenState
    extends ConsumerState<OrganizationListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(organizationProvider.notifier).loadOrganizations();
    });
  }

  @override
  Widget build(BuildContext context) {
    final orgState = ref.watch(organizationProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Organizations'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(organizationProvider.notifier).loadOrganizations();
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(organizationProvider.notifier).loadOrganizations();
        },
        child: _buildBody(orgState),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddOrganizationDialog,
        icon: const Icon(Icons.add),
        label: const Text('Add Organization'),
      ),
    );
  }

  Widget _buildBody(OrganizationState state) {
    if (state.isLoading && state.organizations.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.organizations.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(state.error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                ref.read(organizationProvider.notifier).loadOrganizations();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.organizations.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.business, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text('No organizations found'),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _showAddOrganizationDialog,
              icon: const Icon(Icons.add),
              label: const Text('Add Organization'),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: state.organizations.length,
      padding: const EdgeInsets.all(16),
      itemBuilder: (context, index) {
        final org = state.organizations[index];
        return _OrganizationCard(
          organization: org,
          isSelected: state.selectedOrganization?.id == org.id,
          onTap: () => _viewOrganization(org),
          onSelect: () {
            ref.read(organizationProvider.notifier).selectOrganization(org);
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Selected ${org.name}')),
            );
          },
        );
      },
    );
  }

  void _viewOrganization(Organization org) {
    // Navigate to organization detail screen
    context.push('/organization/${org.id}');
  }

  void _showAddOrganizationDialog() {
    final nameController = TextEditingController();
    final slugController = TextEditingController();
    final descriptionController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Organization'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: 'Organization Name',
                  hintText: 'e.g., City Heart Hospitals',
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: slugController,
                decoration: const InputDecoration(
                  labelText: 'Slug (URL identifier)',
                  hintText: 'e.g., city-heart-hospitals',
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: descriptionController,
                decoration: const InputDecoration(
                  labelText: 'Description',
                  hintText: 'Brief description',
                ),
                maxLines: 3,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              if (nameController.text.isEmpty || slugController.text.isEmpty) {
                return;
              }

              final success = await ref
                  .read(organizationProvider.notifier)
                  .createOrganization({
                'name': nameController.text,
                'slug': slugController.text,
                'description': descriptionController.text,
                'subscription_tier': 'basic',
                'max_clinics': 5,
                'max_users': 50,
                'primary_color': '#2196F3',
              });

              if (mounted && success != null) {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Organization created successfully'),
                  ),
                );
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }
}

class _OrganizationCard extends StatelessWidget {
  final Organization organization;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback onSelect;

  const _OrganizationCard({
    required this.organization,
    required this.isSelected,
    required this.onTap,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              if (organization.logoUrl != null)
                CircleAvatar(
                  backgroundImage: NetworkImage(organization.logoUrl!),
                  radius: 30,
                )
              else
                CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                  radius: 30,
                  child: Text(
                    organization.name[0].toUpperCase(),
                    style: TextStyle(
                      fontSize: 24,
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
                      organization.name,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    if (organization.description != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        organization.description!,
                        style: Theme.of(context).textTheme.bodySmall,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        _InfoChip(
                          icon: Icons.business,
                          label: '${organization.clinicCount} clinics',
                        ),
                        const SizedBox(width: 8),
                        _InfoChip(
                          icon: Icons.people,
                          label: '${organization.userCount} users',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (isSelected)
                Icon(
                  Icons.check_circle,
                  color: Theme.of(context).colorScheme.primary,
                  size: 28,
                )
              else
                IconButton(
                  icon: const Icon(Icons.radio_button_unchecked),
                  onPressed: onSelect,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _InfoChip({
    required this.icon,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14),
          const SizedBox(width: 4),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}
