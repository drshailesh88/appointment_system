import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/patient.dart';
import '../../../core/providers/patients_provider.dart';

/// Patients list screen
class PatientsScreen extends ConsumerStatefulWidget {
  const PatientsScreen({super.key});

  @override
  ConsumerState<PatientsScreen> createState() => _PatientsScreenState();
}

class _PatientsScreenState extends ConsumerState<PatientsScreen> {
  final _searchController = TextEditingController();
  bool _isSearching = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String value) {
    if (value.length >= 2) {
      ref.read(patientsProvider.notifier).searchPatients(value);
    } else if (value.isEmpty) {
      ref.read(patientsProvider.notifier).clearSearch();
    }
  }

  @override
  Widget build(BuildContext context) {
    final patientsState = ref.watch(patientsProvider);

    return Scaffold(
      appBar: AppBar(
        title: _isSearching
            ? TextField(
                controller: _searchController,
                autofocus: true,
                decoration: const InputDecoration(
                  hintText: 'Search by name or phone...',
                  border: InputBorder.none,
                ),
                onChanged: _onSearchChanged,
              )
            : const Text('Patients'),
        actions: [
          IconButton(
            icon: Icon(_isSearching ? Icons.close : Icons.search),
            onPressed: () {
              setState(() {
                _isSearching = !_isSearching;
                if (!_isSearching) {
                  _searchController.clear();
                  ref.read(patientsProvider.notifier).clearSearch();
                }
              });
            },
          ),
        ],
      ),
      body: _buildBody(patientsState),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddPatientDialog,
        child: const Icon(Icons.person_add),
      ),
    );
  }

  Widget _buildBody(PatientsState state) {
    if (!_isSearching) {
      return _buildEmptySearchState();
    }

    if (state.isSearching) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
            const SizedBox(height: 16),
            Text('Error: ${state.error}'),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: () => _onSearchChanged(_searchController.text),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.searchResults.isEmpty) {
      if (_searchController.text.length < 2) {
        return _buildEmptySearchState();
      }
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.person_search,
              size: 48,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No patients found',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Try a different search term',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: _showAddPatientDialog,
              icon: const Icon(Icons.person_add),
              label: const Text('Add New Patient'),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: state.searchResults.length,
      itemBuilder: (context, index) {
        final patient = state.searchResults[index];
        return _PatientCard(
          patient: patient,
          onTap: () {
            context.goNamed(
              'patient-detail',
              pathParameters: {'id': patient.id},
            );
          },
        );
      },
    );
  }

  Widget _buildEmptySearchState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.search,
            size: 64,
            color: Colors.grey.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            'Search for patients',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.grey,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Enter at least 2 characters to search',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  void _showAddPatientDialog() {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final emailController = TextEditingController();
    final ageController = TextEditingController();
    String selectedGender = 'male';

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Add New Patient'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(
                    labelText: 'Full Name *',
                    prefixIcon: Icon(Icons.person),
                  ),
                  textCapitalization: TextCapitalization.words,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: phoneController,
                  decoration: const InputDecoration(
                    labelText: 'Phone *',
                    prefixIcon: Icon(Icons.phone),
                    prefixText: '+91 ',
                  ),
                  keyboardType: TextInputType.phone,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: emailController,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    prefixIcon: Icon(Icons.email),
                  ),
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: ageController,
                        decoration: const InputDecoration(
                          labelText: 'Age',
                          prefixIcon: Icon(Icons.cake),
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: selectedGender,
                        decoration: const InputDecoration(
                          labelText: 'Gender',
                        ),
                        items: const [
                          DropdownMenuItem(value: 'male', child: Text('Male')),
                          DropdownMenuItem(
                              value: 'female', child: Text('Female')),
                          DropdownMenuItem(value: 'other', child: Text('Other')),
                        ],
                        onChanged: (value) {
                          setDialogState(() => selectedGender = value ?? 'male');
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                if (nameController.text.isEmpty ||
                    phoneController.text.isEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Name and Phone are required'),
                      backgroundColor: Colors.red,
                    ),
                  );
                  return;
                }

                final patient =
                    await ref.read(patientsProvider.notifier).createPatient({
                  'name': nameController.text,
                  'phone': '+91${phoneController.text.replaceAll(' ', '')}',
                  'email':
                      emailController.text.isEmpty ? null : emailController.text,
                  'gender': selectedGender,
                  'date_of_birth': ageController.text.isNotEmpty
                      ? DateTime.now()
                          .subtract(
                            Duration(
                                days: int.parse(ageController.text) * 365),
                          )
                          .toIso8601String()
                          .split('T')[0]
                      : null,
                });

                if (patient != null && context.mounted) {
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Patient ${patient.name} added'),
                      backgroundColor: Colors.green,
                    ),
                  );
                  // Navigate to patient detail
                  context.goNamed(
                    'patient-detail',
                    pathParameters: {'id': patient.id},
                  );
                }
              },
              child: const Text('Add Patient'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PatientCard extends StatelessWidget {
  final Patient patient;
  final VoidCallback onTap;

  const _PatientCard({
    required this.patient,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Theme.of(context).colorScheme.primaryContainer,
          child: Text(patient.name.substring(0, 1).toUpperCase()),
        ),
        title: Text(patient.name),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (patient.phone != null) Text(patient.phone!),
            if (patient.gender != null || patient.dateOfBirth != null)
              Text(
                [
                  if (patient.gender != null)
                    patient.gender!.substring(0, 1).toUpperCase() +
                        patient.gender!.substring(1),
                  if (patient.dateOfBirth != null) patient.ageDisplay,
                ].join(' • '),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey,
                    ),
              ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
