import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Appointment detail screen
class AppointmentDetailScreen extends ConsumerWidget {
  final String appointmentId;

  const AppointmentDetailScreen({
    super.key,
    required this.appointmentId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Appointment Details'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              // Handle menu actions
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'reschedule',
                child: ListTile(
                  leading: Icon(Icons.schedule),
                  title: Text('Reschedule'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              const PopupMenuItem(
                value: 'cancel',
                child: ListTile(
                  leading: Icon(Icons.cancel, color: Colors.red),
                  title: Text('Cancel', style: TextStyle(color: Colors.red)),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Patient card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const CircleAvatar(
                      radius: 30,
                      child: Text('JS'),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'John Smith',
                            style: Theme.of(context)
                                .textTheme
                                .titleLarge
                                ?.copyWith(fontWeight: FontWeight.bold),
                          ),
                          const Text('Male, 35 years'),
                          const Text('+91 98765 43210'),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.phone),
                      onPressed: () {
                        // TODO: Call patient
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Appointment info
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Appointment Info',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 16),
                    _InfoRow(
                      icon: Icons.calendar_today,
                      label: 'Date',
                      value: 'Today, Jan 3, 2026',
                    ),
                    _InfoRow(
                      icon: Icons.access_time,
                      label: 'Time',
                      value: '10:00 AM - 10:15 AM',
                    ),
                    _InfoRow(
                      icon: Icons.person,
                      label: 'Doctor',
                      value: 'Dr. Priya Sharma',
                    ),
                    _InfoRow(
                      icon: Icons.medical_services,
                      label: 'Type',
                      value: 'New Consultation',
                    ),
                    _InfoRow(
                      icon: Icons.confirmation_number,
                      label: 'Token',
                      value: '#5',
                    ),
                    const Divider(height: 24),
                    _InfoRow(
                      icon: Icons.info,
                      label: 'Status',
                      value: 'Checked In',
                      valueColor: Colors.orange,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Chief complaint
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Chief Complaint',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Headache and fever for 2 days. Patient also reports mild body ache and fatigue.',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Notes
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Notes',
                          style:
                              Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.edit, size: 20),
                          onPressed: () {
                            // TODO: Edit notes
                          },
                        ),
                      ],
                    ),
                    const Text('No notes added yet.'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Action buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      // TODO: View EMR
                    },
                    icon: const Icon(Icons.folder_open),
                    label: const Text('View EMR'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      // TODO: Start consultation
                    },
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey),
          const SizedBox(width: 12),
          Text(
            '$label: ',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey,
                ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w500,
                  color: valueColor,
                ),
          ),
        ],
      ),
    );
  }
}
