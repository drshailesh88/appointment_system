import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Patient detail screen
class PatientDetailScreen extends ConsumerWidget {
  final String patientId;

  const PatientDetailScreen({
    super.key,
    required this.patientId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Patient Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () {
              // TODO: Edit patient
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Patient info card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    const CircleAvatar(
                      radius: 40,
                      child: Text('JS', style: TextStyle(fontSize: 24)),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'John Smith',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 4),
                    const Text('Male, 35 years'),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _ActionButton(
                          icon: Icons.phone,
                          label: 'Call',
                          onTap: () {},
                        ),
                        _ActionButton(
                          icon: Icons.message,
                          label: 'SMS',
                          onTap: () {},
                        ),
                        _ActionButton(
                          icon: Icons.calendar_today,
                          label: 'Book',
                          onTap: () {},
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Contact info
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Contact Information',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _InfoTile(Icons.phone, '+91 98765 43210'),
                    _InfoTile(Icons.email, 'john.smith@email.com'),
                    _InfoTile(Icons.location_on, '123 Main Street, Mumbai'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Medical info
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Medical Information',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    _InfoTile(Icons.bloodtype, 'Blood Group: B+'),
                    _InfoTile(Icons.warning_amber, 'Allergies: Penicillin'),
                    _InfoTile(Icons.emergency, 'Emergency: Spouse (98765 00000)'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Appointment history
            Text(
              'Recent Visits',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            ...List.generate(
              3,
              (index) => Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor:
                        Theme.of(context).colorScheme.primaryContainer,
                    child: const Icon(Icons.calendar_today, size: 20),
                  ),
                  title: Text('Jan ${index + 1}, 2026'),
                  subtitle: Text('Dr. Sharma • ${index == 0 ? "Follow-up" : "Consultation"}'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () {
                    // TODO: View visit details
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Icon(icon, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 4),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoTile(this.icon, this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey),
          const SizedBox(width: 12),
          Text(text),
        ],
      ),
    );
  }
}
