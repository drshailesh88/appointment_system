import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/models/appointment.dart';
import '../../../core/providers/appointments_provider.dart';
import '../../../core/providers/auth_provider.dart';
import '../../../core/providers/voice_booking_provider.dart';

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
                    icon: Icons.analytics,
                    label: 'Analytics',
                    onTap: () => context.goNamed('analytics'),
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
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => const _VoiceBookingSheet(),
    );
  }
}

/// Voice booking bottom sheet
class _VoiceBookingSheet extends ConsumerStatefulWidget {
  const _VoiceBookingSheet();

  @override
  ConsumerState<_VoiceBookingSheet> createState() => _VoiceBookingSheetState();
}

class _VoiceBookingSheetState extends ConsumerState<_VoiceBookingSheet> {
  final _textController = TextEditingController();
  bool _useTextInput = false;

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final voiceState = ref.watch(voiceBookingProvider);

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle bar
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 24),

            // Title
            Text(
              'Voice Booking',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              _getStatusText(voiceState.status),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: 32),

            // Voice visualization or text input
            if (_useTextInput) ...[
              TextField(
                controller: _textController,
                decoration: InputDecoration(
                  hintText: 'Type your booking request...',
                  border: const OutlineInputBorder(),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: () {
                      if (_textController.text.isNotEmpty) {
                        ref
                            .read(voiceBookingProvider.notifier)
                            .processTextInput(_textController.text);
                      }
                    },
                  ),
                ),
                maxLines: 2,
                enabled: !voiceState.isProcessing,
              ),
            ] else ...[
              // Microphone button with animation
              GestureDetector(
                onTap: () => _toggleRecording(voiceState),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: voiceState.isListening ? 120 : 100,
                  height: voiceState.isListening ? 120 : 100,
                  decoration: BoxDecoration(
                    color: voiceState.isListening
                        ? Colors.red
                        : voiceState.isProcessing
                            ? Colors.orange
                            : Colors.blue,
                    shape: BoxShape.circle,
                    boxShadow: voiceState.isListening
                        ? [
                            BoxShadow(
                              color: Colors.red.withOpacity(0.3),
                              blurRadius: 20,
                              spreadRadius: voiceState.audioLevel != null
                                  ? voiceState.audioLevel! * 20
                                  : 0,
                            ),
                          ]
                        : null,
                  ),
                  child: Icon(
                    voiceState.isListening
                        ? Icons.stop
                        : voiceState.isProcessing
                            ? Icons.hourglass_top
                            : Icons.mic,
                    color: Colors.white,
                    size: 40,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),

            // Transcript display
            if (voiceState.transcript != null) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'You said:',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      voiceState.transcript!,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Response display
            if (voiceState.response != null) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.smart_toy, size: 16, color: Colors.blue.shade700),
                        const SizedBox(width: 8),
                        Text(
                          'Assistant:',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Colors.blue.shade700,
                              ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      voiceState.response!,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Error display
            if (voiceState.hasError) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  voiceState.errorMessage ?? 'An error occurred',
                  style: TextStyle(color: Colors.red.shade700),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Success result
            if (voiceState.result?.success == true) ...[
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  if (voiceState.result?.appointmentId != null) {
                    context.goNamed(
                      'appointment-detail',
                      pathParameters: {'id': voiceState.result!.appointmentId!},
                    );
                  }
                },
                icon: const Icon(Icons.check_circle),
                label: const Text('View Appointment'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Quick suggestions
            if (!voiceState.isActive && voiceState.transcript == null) ...[
              const SizedBox(height: 8),
              Text(
                'Try saying:',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey,
                    ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: voiceBookingSuggestions.take(3).map((suggestion) {
                  return ActionChip(
                    label: Text(
                      suggestion,
                      style: const TextStyle(fontSize: 12),
                    ),
                    onPressed: () {
                      ref
                          .read(voiceBookingProvider.notifier)
                          .processTextInput(suggestion);
                    },
                  );
                }).toList(),
              ),
            ],
            const SizedBox(height: 16),

            // Toggle text/voice input
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TextButton.icon(
                  onPressed: () {
                    setState(() => _useTextInput = !_useTextInput);
                  },
                  icon: Icon(_useTextInput ? Icons.mic : Icons.keyboard),
                  label: Text(_useTextInput ? 'Use Voice' : 'Type Instead'),
                ),
                const SizedBox(width: 16),
                TextButton(
                  onPressed: () {
                    ref.read(voiceBookingProvider.notifier).cancel();
                    Navigator.pop(context);
                  },
                  child: const Text('Cancel'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _getStatusText(VoiceBookingStatus status) {
    switch (status) {
      case VoiceBookingStatus.idle:
        return 'Tap the microphone to start';
      case VoiceBookingStatus.listening:
        return 'Listening... tap to stop';
      case VoiceBookingStatus.processing:
        return 'Processing your request...';
      case VoiceBookingStatus.responding:
        return 'Here\'s what I found...';
      case VoiceBookingStatus.error:
        return 'Something went wrong';
    }
  }

  void _toggleRecording(VoiceBookingState state) {
    final notifier = ref.read(voiceBookingProvider.notifier);
    if (state.isListening) {
      notifier.stopListening();
    } else if (!state.isProcessing && !state.isResponding) {
      notifier.startListening();
    }
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
