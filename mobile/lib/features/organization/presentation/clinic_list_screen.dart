import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/clinic.dart';
import '../providers/clinic_provider.dart';
import '../providers/organization_provider.dart';

/// Clinic list screen
class ClinicListScreen extends ConsumerStatefulWidget {
  const ClinicListScreen({super.key});

  @override
  ConsumerState<ClinicListScreen> createState() => _ClinicListScreenState();
}

class _ClinicListScreenState extends ConsumerState<ClinicListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(clinicProvider.notifier).loadClinics();
    });
  }

  @override
  Widget build(BuildContext context) {
    final clinicState = ref.watch(clinicProvider);
    final orgState = ref.watch(organizationProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text('Clinics - ${orgState.selectedOrganization?.name ?? ""}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(clinicProvider.notifier).loadClinics();
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(clinicProvider.notifier).loadClinics();
        },
        child: _buildBody(clinicState),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/clinics/add'),
        icon: const Icon(Icons.add),
        label: const Text('Add Clinic'),
      ),
    );
  }

  Widget _buildBody(ClinicState state) {
    if (state.isLoading && state.clinics.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.clinics.isEmpty) {
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
                ref.read(clinicProvider.notifier).loadClinics();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.clinics.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.location_on, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text('No clinics found'),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => context.push('/clinics/add'),
              icon: const Icon(Icons.add),
              label: const Text('Add Clinic'),
            ),
          ],
        ),
      );
    }

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 0.85,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemCount: state.clinics.length,
      itemBuilder: (context, index) {
        final clinic = state.clinics[index];
        return _ClinicCard(
          clinic: clinic,
          isSelected: state.selectedClinic?.id == clinic.id,
          onTap: () => context.push('/clinics/${clinic.id}'),
          onSelect: () {
            ref.read(clinicProvider.notifier).selectClinic(clinic);
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Selected ${clinic.name}')),
            );
          },
        );
      },
    );
  }
}

class _ClinicCard extends StatelessWidget {
  final Clinic clinic;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback onSelect;

  const _ClinicCard({
    required this.clinic,
    required this.isSelected,
    required this.onTap,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 80,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(12),
                ),
              ),
              child: Center(
                child: Icon(
                  Icons.location_city,
                  size: 40,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      clinic.name,
                      style: Theme.of(context).textTheme.titleMedium,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${clinic.city}, ${clinic.state}',
                      style: Theme.of(context).textTheme.bodySmall,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const Spacer(),
                    Row(
                      children: [
                        Icon(
                          clinic.isActive
                              ? Icons.check_circle
                              : Icons.cancel,
                          size: 16,
                          color: clinic.isActive ? Colors.green : Colors.red,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          clinic.isActive ? 'Active' : 'Inactive',
                          style: TextStyle(
                            fontSize: 12,
                            color: clinic.isActive ? Colors.green : Colors.red,
                          ),
                        ),
                        const Spacer(),
                        if (isSelected)
                          Icon(
                            Icons.check_circle,
                            color: Theme.of(context).colorScheme.primary,
                            size: 20,
                          )
                        else
                          IconButton(
                            icon: const Icon(Icons.radio_button_unchecked),
                            iconSize: 20,
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            onPressed: onSelect,
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
