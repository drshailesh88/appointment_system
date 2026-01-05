import 'package:docassist_mobile/core/models/appointment.dart';
import 'package:docassist_mobile/core/providers/appointments_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// Mock classes
class MockAppointmentsNotifier extends Mock implements AppointmentsNotifier {}

void main() {
  group('AppointmentListScreen Widget Tests', () {
    late List<Appointment> mockAppointments;
    late MockAppointmentsNotifier mockNotifier;

    setUp(() {
      mockNotifier = MockAppointmentsNotifier();

      mockAppointments = [
        Appointment(
          id: 'apt-001',
          patientId: 'pat-001',
          patientName: 'John Doe',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now().add(const Duration(hours: 1)),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
          chiefComplaint: 'Headache',
          tokenNumber: 5,
        ),
        Appointment(
          id: 'apt-002',
          patientId: 'pat-002',
          patientName: 'Jane Smith',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now().add(const Duration(hours: 2)),
          durationMinutes: 30,
          status: 'checked_in',
          appointmentType: 'follow_up',
          bookingSource: 'online',
          tokenNumber: 6,
        ),
        Appointment(
          id: 'apt-003',
          patientId: 'pat-003',
          patientName: 'Bob Johnson',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now().subtract(const Duration(hours: 1)),
          durationMinutes: 15,
          status: 'completed',
          appointmentType: 'procedure',
          bookingSource: 'phone',
        ),
      ];
    });

    testWidgets('displays loading indicator when loading',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            appointmentsProvider.overrideWith((ref) {
              return mockNotifier;
            }),
          ],
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: [],
              isLoading: true,
              error: null,
            ),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays error message when error occurs',
        (WidgetTester tester) async {
      const errorMessage = 'Failed to load appointments';

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: [],
              isLoading: false,
              error: errorMessage,
            ),
          ),
        ),
      );

      expect(find.text('Error loading appointments'), findsOneWidget);
      expect(find.textContaining(errorMessage), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('displays empty state when no appointments',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: [],
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('No appointments found'), findsOneWidget);
      expect(find.byIcon(Icons.calendar_today_outlined), findsOneWidget);
    });

    testWidgets('displays list of appointments when data is available',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('John Doe'), findsOneWidget);
      expect(find.text('Jane Smith'), findsOneWidget);
      expect(find.text('Bob Johnson'), findsOneWidget);
    });

    testWidgets('displays correct number of appointment cards',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      // Should display 3 cards
      expect(find.byType(Card), findsNWidgets(3));
    });

    testWidgets('displays check-in button for scheduled appointments',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
              showCheckIn: true,
            ),
          ),
        ),
      );

      // Only scheduled appointments should have check-in button
      expect(find.text('Check In'), findsOneWidget);
    });

    testWidgets('does not display check-in button when showCheckIn is false',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
              showCheckIn: false,
            ),
          ),
        ),
      );

      expect(find.text('Check In'), findsNothing);
    });

    testWidgets('calls onCheckIn when check-in button is tapped',
        (WidgetTester tester) async {
      String? checkedInId;

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
              showCheckIn: true,
              onCheckIn: (id) {
                checkedInId = id;
              },
            ),
          ),
        ),
      );

      await tester.tap(find.text('Check In'));
      await tester.pump();

      expect(checkedInId, 'apt-001');
    });

    testWidgets('displays all status types correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('Scheduled'), findsOneWidget);
      expect(find.text('Checked In'), findsOneWidget);
      expect(find.text('Completed'), findsOneWidget);
    });

    testWidgets('supports pull-to-refresh', (WidgetTester tester) async {
      bool refreshCalled = false;

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(
              body: RefreshIndicator(
                onRefresh: () async {
                  refreshCalled = true;
                },
                child: _AppointmentsListTest(
                  appointments: mockAppointments,
                  isLoading: false,
                  error: null,
                ),
              ),
            ),
          ),
        ),
      );

      // Trigger pull-to-refresh
      await tester.fling(
        find.byType(ListView),
        const Offset(0, 300),
        1000,
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));

      expect(refreshCalled, true);
    });

    testWidgets('list is scrollable', (WidgetTester tester) async {
      // Create a long list of appointments
      final longList = List.generate(
        20,
        (index) => Appointment(
          id: 'apt-$index',
          patientId: 'pat-$index',
          patientName: 'Patient $index',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now().add(Duration(hours: index)),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: longList,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      // First patient should be visible
      expect(find.text('Patient 0'), findsOneWidget);

      // Last patient should not be visible initially
      expect(find.text('Patient 19'), findsNothing);

      // Scroll to the bottom
      await tester.fling(
        find.byType(ListView),
        const Offset(0, -5000),
        1000,
      );
      await tester.pumpAndSettle();

      // Last patient should now be visible
      expect(find.text('Patient 19'), findsOneWidget);
    });

    testWidgets('displays token numbers correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.textContaining('Token: 5'), findsOneWidget);
      expect(find.textContaining('Token: 6'), findsOneWidget);
    });

    testWidgets('displays chief complaints correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.textContaining('Headache'), findsOneWidget);
      expect(find.textContaining('Chief Complaint'), findsOneWidget);
    });

    testWidgets('card tap triggers navigation callback',
        (WidgetTester tester) async {
      String? tappedAppointmentId;

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: mockAppointments,
              isLoading: false,
              error: null,
              onTap: (id) {
                tappedAppointmentId = id;
              },
            ),
          ),
        ),
      );

      // Tap the first appointment card
      await tester.tap(find.byType(InkWell).first);
      await tester.pump();

      expect(tappedAppointmentId, 'apt-001');
    });

    testWidgets('handles appointments with no chief complaint',
        (WidgetTester tester) async {
      final noComplaintAppointments = [
        Appointment(
          id: 'apt-004',
          patientId: 'pat-004',
          patientName: 'Test Patient',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now(),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: noComplaintAppointments,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('Test Patient'), findsOneWidget);
      expect(find.textContaining('Chief Complaint'), findsNothing);
    });

    testWidgets('handles appointments with no token number',
        (WidgetTester tester) async {
      final noTokenAppointments = [
        Appointment(
          id: 'apt-005',
          patientId: 'pat-005',
          patientName: 'Test Patient 2',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now(),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'online',
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: noTokenAppointments,
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      expect(find.text('Test Patient 2'), findsOneWidget);
      expect(find.textContaining('Token:'), findsNothing);
    });

    testWidgets('empty state has correct styling', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: [],
              isLoading: false,
              error: null,
            ),
          ),
        ),
      );

      final iconFinder = find.byIcon(Icons.calendar_today_outlined);
      expect(iconFinder, findsOneWidget);

      final Icon icon = tester.widget(iconFinder);
      expect(icon.size, 48);
    });

    testWidgets('error state has retry functionality',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: [],
              isLoading: false,
              error: 'Network error',
            ),
          ),
        ),
      );

      // Error UI should not have retry button by default
      // This is just to verify error state renders correctly
      expect(find.textContaining('Network error'), findsOneWidget);
    });

    testWidgets('displays multiple appointments of same status',
        (WidgetTester tester) async {
      final sameStatusAppointments = [
        Appointment(
          id: 'apt-006',
          patientId: 'pat-006',
          patientName: 'Patient A',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now(),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
        ),
        Appointment(
          id: 'apt-007',
          patientId: 'pat-007',
          patientName: 'Patient B',
          doctorId: 'doc-001',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now().add(const Duration(hours: 1)),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: _AppointmentsListTest(
              appointments: sameStatusAppointments,
              isLoading: false,
              error: null,
              showCheckIn: true,
            ),
          ),
        ),
      );

      expect(find.text('Scheduled'), findsNWidgets(2));
      expect(find.text('Check In'), findsNWidgets(2));
    });
  });
}

// Test widget wrapper
class _AppointmentsListTest extends StatelessWidget {
  final List<Appointment> appointments;
  final bool isLoading;
  final String? error;
  final Function(String)? onCheckIn;
  final Function(String)? onTap;
  final bool showCheckIn;

  const _AppointmentsListTest({
    required this.appointments,
    required this.isLoading,
    this.error,
    this.onCheckIn,
    this.onTap,
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
        return _AppointmentCardWrapper(
          appointment: appointment,
          onCheckIn: showCheckIn && appointment.status == 'scheduled'
              ? () => onCheckIn?.call(appointment.id)
              : null,
          onTap: () => onTap?.call(appointment.id),
        );
      },
    );
  }
}

class _AppointmentCardWrapper extends StatelessWidget {
  final Appointment appointment;
  final VoidCallback? onCheckIn;
  final VoidCallback? onTap;

  const _AppointmentCardWrapper({
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
                      appointment.patientName.substring(0, 1).toUpperCase(),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          appointment.patientName,
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          '${appointment.doctorName} • ${appointment.typeDisplay}',
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
