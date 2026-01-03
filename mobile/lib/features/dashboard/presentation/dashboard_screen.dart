import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/appointment.dart';
import '../../../core/providers/appointments_provider.dart';
import '../../../core/providers/auth_provider.dart';

/// Dashboard screen
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    // Load today's appointments when screen initializes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(appointmentsProvider.notifier).loadTodayAppointments();
    });
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider);
    final appointmentsState = ref.watch(appointmentsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {
              // TODO: Show notifications
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(appointmentsProvider.notifier).loadTodayAppointments();
        },
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Welcome card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 30,
                        backgroundColor:
                            Theme.of(context).colorScheme.primaryContainer,
                        child: Text(
                          authState.user?.name?.substring(0, 1).toUpperCase() ??
                              'U',
                          style: const TextStyle(fontSize: 24),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Welcome back,',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                            Text(
                              authState.user?.name ?? 'User',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Quick stats
              Text(
                'Today\'s Overview',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 12),

              if (appointmentsState.isLoading)
                const Center(child: CircularProgressIndicator())
              else ...[
                Row(
                  children: [
                    Expanded(
                      child: _StatCard(
                        title: 'Appointments',
                        value: '${appointmentsState.todayAppointments.length}',
                        icon: Icons.calendar_today,
                        color: Colors.blue,
                        onTap: () => context.goNamed('appointments'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _StatCard(
                        title: 'Checked In',
                        value: '${appointmentsState.checkedInCount}',
                        icon: Icons.people,
                        color: Colors.green,
                        onTap: () => context.goNamed('appointments'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _StatCard(
                        title: 'Scheduled',
                        value: '${appointmentsState.scheduledCount}',
                        icon: Icons.pending_actions,
                        color: Colors.orange,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _StatCard(
                        title: 'Completed',
                        value: '${appointmentsState.completedCount}',
                        icon: Icons.check_circle,
                        color: Colors.teal,
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 24),

              // Quick actions
              Text(
                'Quick Actions',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _QuickAction(
                    icon: Icons.add_circle,
                    label: 'Book',
                    onTap: () => context.goNamed('book-appointment'),
                  ),
                  _QuickAction(
                    icon: Icons.person_add,
                    label: 'New Patient',
                    onTap: () => context.goNamed('patients'),
                  ),
                  _QuickAction(
                    icon: Icons.mic,
                    label: 'Voice',
                    onTap: () {
                      _showVoiceBookingDialog(context);
                    },
                  ),
                  _QuickAction(
                    icon: Icons.search,
                    label: 'Search',
                    onTap: () => context.goNamed('patients'),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Upcoming appointments
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Upcoming Appointments',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  TextButton(
                    onPressed: () => context.goNamed('appointments'),
                    child: const Text('View All'),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              if (appointmentsState.error != null)
                Card(
                  color: Colors.red.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      'Error: ${appointmentsState.error}',
                      style: TextStyle(color: Colors.red.shade700),
                    ),
                  ),
                )
              else if (appointmentsState.todayAppointments.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Center(
                      child: Text('No appointments for today'),
                    ),
                  ),
                )
              else
                ...appointmentsState.todayAppointments
                    .where((a) => a.status == 'scheduled' || a.status == 'checked_in')
                    .take(5)
                    .map((appointment) => _AppointmentCard(
                          appointment: appointment,
                          onCheckIn: () => _checkInPatient(appointment.id),
                        )),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.goNamed('book-appointment'),
        icon: const Icon(Icons.add),
        label: const Text('Book Appointment'),
      ),
    );
  }

  Future<void> _checkInPatient(String appointmentId) async {
    final success = await ref
        .read(appointmentsProvider.notifier)
        .checkInPatient(appointmentId);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            success ? 'Patient checked in successfully' : 'Failed to check in patient',
          ),
          backgroundColor: success ? Colors.green : Colors.red,
        ),
      );
    }
  }

  void _showVoiceBookingDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Voice Booking'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.mic, size: 64, color: Colors.blue),
            const SizedBox(height: 16),
            const Text(
              'Speak your booking request',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Example: "Book an appointment with Dr. Sharma for tomorrow at 10 AM"',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              // TODO: Implement voice recording
              Navigator.pop(context);
            },
            icon: const Icon(Icons.mic),
            label: const Text('Start Recording'),
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color, size: 28),
              const SizedBox(height: 8),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              Text(
                title,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _QuickAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
            const SizedBox(height: 8),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _AppointmentCard extends StatelessWidget {
  final Appointment appointment;
  final VoidCallback? onCheckIn;

  const _AppointmentCard({
    required this.appointment,
    this.onCheckIn,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Theme.of(context).colorScheme.primaryContainer,
          child: Text(
            appointment.patientName?.substring(0, 1).toUpperCase() ?? 'P',
          ),
        ),
        title: Text(appointment.patientName ?? 'Unknown Patient'),
        subtitle: Text('${appointment.timeDisplay} • ${appointment.typeDisplay}'),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (appointment.status == 'scheduled' && onCheckIn != null)
              IconButton(
                icon: const Icon(Icons.login),
                onPressed: onCheckIn,
                tooltip: 'Check In',
              ),
            Chip(
              label: Text(
                appointment.statusDisplay,
                style: const TextStyle(fontSize: 12),
              ),
              backgroundColor: _getStatusColor(appointment.status),
            ),
          ],
        ),
        onTap: () {
          context.goNamed(
            'appointment-detail',
            pathParameters: {'id': appointment.id},
          );
        },
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'scheduled':
        return Colors.blue.shade100;
      case 'checked_in':
        return Colors.orange.shade100;
      case 'in_progress':
        return Colors.purple.shade100;
      case 'completed':
        return Colors.green.shade100;
      case 'cancelled':
        return Colors.red.shade100;
      default:
        return Colors.grey.shade100;
    }
  }
}
