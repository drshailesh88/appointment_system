import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/models/appointment.dart';
import '../../../core/providers/appointments_provider.dart';

/// Appointments list screen
class AppointmentsScreen extends ConsumerStatefulWidget {
  const AppointmentsScreen({super.key});

  @override
  ConsumerState<AppointmentsScreen> createState() => _AppointmentsScreenState();
}

class _AppointmentsScreenState extends ConsumerState<AppointmentsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String? _statusFilter;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(_onTabChanged);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAppointments();
    });
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _tabController.dispose();
    super.dispose();
  }

  void _onTabChanged() {
    if (!_tabController.indexIsChanging) {
      _loadAppointments();
    }
  }

  Future<void> _loadAppointments() async {
    final now = DateTime.now();
    final today = DateFormat('yyyy-MM-dd').format(now);

    switch (_tabController.index) {
      case 0: // Today
        await ref.read(appointmentsProvider.notifier).loadTodayAppointments();
        break;
      case 1: // Upcoming
        final nextWeek = DateFormat('yyyy-MM-dd')
            .format(now.add(const Duration(days: 7)));
        await ref.read(appointmentsProvider.notifier).loadAppointments(
              dateFrom: today,
              dateTo: nextWeek,
              status: _statusFilter,
            );
        break;
      case 2: // Past
        final lastMonth = DateFormat('yyyy-MM-dd')
            .format(now.subtract(const Duration(days: 30)));
        await ref.read(appointmentsProvider.notifier).loadAppointments(
              dateFrom: lastMonth,
              dateTo: today,
              status: _statusFilter,
            );
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final appointmentsState = ref.watch(appointmentsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Appointments'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
          IconButton(
            icon: const Icon(Icons.calendar_month),
            onPressed: () {
              // TODO: Show calendar view
            },
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Today'),
            Tab(text: 'Upcoming'),
            Tab(text: 'Past'),
          ],
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadAppointments,
        child: TabBarView(
          controller: _tabController,
          children: [
            _AppointmentsList(
              appointments: appointmentsState.todayAppointments,
              isLoading: appointmentsState.isLoading,
              error: appointmentsState.error,
              onCheckIn: _checkInPatient,
            ),
            _AppointmentsList(
              appointments: appointmentsState.appointments,
              isLoading: appointmentsState.isLoading,
              error: appointmentsState.error,
              onCheckIn: _checkInPatient,
            ),
            _AppointmentsList(
              appointments: appointmentsState.appointments,
              isLoading: appointmentsState.isLoading,
              error: appointmentsState.error,
              showCheckIn: false,
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.goNamed('book-appointment'),
        child: const Icon(Icons.add),
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
            success
                ? 'Patient checked in successfully'
                : 'Failed to check in patient',
          ),
          backgroundColor: success ? Colors.green : Colors.red,
        ),
      );
    }
  }

  void _showFilterDialog() {
    showModalBottomSheet(
      context: context,
      builder: (context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Filter by Status',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              children: [
                FilterChip(
                  label: const Text('All'),
                  selected: _statusFilter == null,
                  onSelected: (selected) {
                    setState(() => _statusFilter = null);
                    Navigator.pop(context);
                    _loadAppointments();
                  },
                ),
                FilterChip(
                  label: const Text('Scheduled'),
                  selected: _statusFilter == 'scheduled',
                  onSelected: (selected) {
                    setState(() => _statusFilter = 'scheduled');
                    Navigator.pop(context);
                    _loadAppointments();
                  },
                ),
                FilterChip(
                  label: const Text('Checked In'),
                  selected: _statusFilter == 'checked_in',
                  onSelected: (selected) {
                    setState(() => _statusFilter = 'checked_in');
                    Navigator.pop(context);
                    _loadAppointments();
                  },
                ),
                FilterChip(
                  label: const Text('Completed'),
                  selected: _statusFilter == 'completed',
                  onSelected: (selected) {
                    setState(() => _statusFilter = 'completed');
                    Navigator.pop(context);
                    _loadAppointments();
                  },
                ),
                FilterChip(
                  label: const Text('Cancelled'),
                  selected: _statusFilter == 'cancelled',
                  onSelected: (selected) {
                    setState(() => _statusFilter = 'cancelled');
                    Navigator.pop(context);
                    _loadAppointments();
                  },
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _AppointmentsList extends StatelessWidget {
  final List<Appointment> appointments;
  final bool isLoading;
  final String? error;
  final Function(String)? onCheckIn;
  final bool showCheckIn;

  const _AppointmentsList({
    required this.appointments,
    required this.isLoading,
    this.error,
    this.onCheckIn,
    this.showCheckIn = true,
  });

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
            const SizedBox(height: 16),
            Text(
              'Error loading appointments',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              error!,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    if (appointments.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.calendar_today_outlined,
              size: 48,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No appointments found',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.grey,
                  ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: appointments.length,
      itemBuilder: (context, index) {
        final appointment = appointments[index];
        return _AppointmentCard(
          appointment: appointment,
          onCheckIn: showCheckIn && appointment.status == 'scheduled'
              ? () => onCheckIn?.call(appointment.id)
              : null,
          onTap: () {
            context.goNamed(
              'appointment-detail',
              pathParameters: {'id': appointment.id},
            );
          },
        );
      },
    );
  }
}

class _AppointmentCard extends StatelessWidget {
  final Appointment appointment;
  final VoidCallback? onCheckIn;
  final VoidCallback? onTap;

  const _AppointmentCard({
    required this.appointment,
    this.onCheckIn,
    this.onTap,
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor:
                        Theme.of(context).colorScheme.primaryContainer,
                    child: Text(
                      appointment.patientName?.substring(0, 1).toUpperCase() ??
                          'P',
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          appointment.patientName ?? 'Unknown Patient',
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          '${appointment.doctorName ?? 'Doctor'} • ${appointment.timeDisplay}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  _StatusChip(status: appointment.status),
                ],
              ),
              if (appointment.chiefComplaint != null &&
                  appointment.chiefComplaint!.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  'Chief Complaint: ${appointment.chiefComplaint}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey,
                      ),
                ),
              ],
              if (onCheckIn != null || appointment.tokenNumber != null) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    if (onCheckIn != null)
                      OutlinedButton.icon(
                        onPressed: onCheckIn,
                        icon: const Icon(Icons.login, size: 18),
                        label: const Text('Check In'),
                      ),
                    if (appointment.tokenNumber != null) ...[
                      if (onCheckIn != null) const SizedBox(width: 8),
                      Chip(
                        avatar: const Icon(Icons.confirmation_number, size: 16),
                        label: Text('Token: ${appointment.tokenNumber}'),
                      ),
                    ],
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;

  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color backgroundColor;
    String label;

    switch (status) {
      case 'scheduled':
        backgroundColor = Colors.blue.shade100;
        label = 'Scheduled';
        break;
      case 'checked_in':
        backgroundColor = Colors.orange.shade100;
        label = 'Checked In';
        break;
      case 'in_progress':
        backgroundColor = Colors.purple.shade100;
        label = 'In Progress';
        break;
      case 'completed':
        backgroundColor = Colors.green.shade100;
        label = 'Completed';
        break;
      case 'cancelled':
        backgroundColor = Colors.red.shade100;
        label = 'Cancelled';
        break;
      case 'no_show':
        backgroundColor = Colors.grey.shade300;
        label = 'No Show';
        break;
      default:
        backgroundColor = Colors.grey.shade100;
        label = status;
    }

    return Chip(
      label: Text(
        label,
        style: const TextStyle(fontSize: 12),
      ),
      backgroundColor: backgroundColor,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }
}
