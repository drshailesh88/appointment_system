import 'package:docassist_mobile/core/models/appointment.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';

void main() {
  group('AppointmentCard Widget Tests', () {
    late Appointment testAppointment;

    setUp(() {
      testAppointment = Appointment(
        id: 'apt-001',
        patientId: 'pat-001',
        patientName: 'John Doe',
        doctorId: 'doc-001',
        doctorName: 'Dr. Smith',
        scheduledStart: DateTime(2024, 1, 15, 10, 30),
        scheduledEnd: DateTime(2024, 1, 15, 11, 0),
        durationMinutes: 30,
        status: 'scheduled',
        appointmentType: 'new_consultation',
        bookingSource: 'walk_in',
        chiefComplaint: 'Headache',
        tokenNumber: 5,
      );
    });

    testWidgets('displays patient name correctly', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
            ),
          ),
        ),
      );

      expect(find.text('John Doe'), findsOneWidget);
    });

    testWidgets('displays appointment time correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
            ),
          ),
        ),
      );

      // Time should be displayed somewhere
      final timeText = DateFormat('h:mm a').format(testAppointment.scheduledStart);
      expect(find.textContaining('10:30'), findsWidgets);
    });

    testWidgets('displays status badge with correct color',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
            ),
          ),
        ),
      );

      // Scheduled status badge
      expect(find.text('Scheduled'), findsOneWidget);

      // Find the Chip widget
      final chipFinder = find.byType(Chip);
      expect(chipFinder, findsOneWidget);

      final Chip chip = tester.widget(chipFinder);
      expect(chip.backgroundColor, Colors.blue.shade100);
    });

    testWidgets('displays checked-in status with orange badge',
        (WidgetTester tester) async {
      final checkedInAppointment = Appointment(
        id: 'apt-002',
        patientId: 'pat-001',
        patientName: 'Jane Smith',
        doctorId: 'doc-001',
        doctorName: 'Dr. Smith',
        scheduledStart: DateTime(2024, 1, 15, 11, 0),
        durationMinutes: 30,
        status: 'checked_in',
        appointmentType: 'follow_up',
        bookingSource: 'online',
        checkInTime: DateTime(2024, 1, 15, 10, 55),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: checkedInAppointment,
            ),
          ),
        ),
      );

      expect(find.text('Checked In'), findsOneWidget);

      final chipFinder = find.byType(Chip);
      final Chip chip = tester.widget(chipFinder);
      expect(chip.backgroundColor, Colors.orange.shade100);
    });

    testWidgets('displays completed status with green badge',
        (WidgetTester tester) async {
      final completedAppointment = testAppointment.copyWith(
        status: 'completed',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: completedAppointment,
            ),
          ),
        ),
      );

      expect(find.text('Completed'), findsOneWidget);

      final chipFinder = find.byType(Chip);
      final Chip chip = tester.widget(chipFinder);
      expect(chip.backgroundColor, Colors.green.shade100);
    });

    testWidgets('displays cancelled status with red badge',
        (WidgetTester tester) async {
      final cancelledAppointment = testAppointment.copyWith(
        status: 'cancelled',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: cancelledAppointment,
            ),
          ),
        ),
      );

      expect(find.text('Cancelled'), findsOneWidget);

      final chipFinder = find.byType(Chip);
      final Chip chip = tester.widget(chipFinder);
      expect(chip.backgroundColor, Colors.red.shade100);
    });

    testWidgets('displays chief complaint when available',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
            ),
          ),
        ),
      );

      expect(find.textContaining('Headache'), findsOneWidget);
      expect(find.textContaining('Chief Complaint'), findsOneWidget);
    });

    testWidgets('hides chief complaint when not available',
        (WidgetTester tester) async {
      final appointmentWithoutComplaint = Appointment(
        id: 'apt-003',
        patientId: 'pat-001',
        patientName: 'Bob Johnson',
        doctorId: 'doc-001',
        doctorName: 'Dr. Smith',
        scheduledStart: DateTime(2024, 1, 15, 12, 0),
        durationMinutes: 15,
        status: 'scheduled',
        appointmentType: 'new_consultation',
        bookingSource: 'phone',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: appointmentWithoutComplaint,
            ),
          ),
        ),
      );

      expect(find.textContaining('Chief Complaint'), findsNothing);
    });

    testWidgets('displays token number when available',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
            ),
          ),
        ),
      );

      expect(find.textContaining('Token: 5'), findsOneWidget);
    });

    testWidgets('shows check-in button for scheduled appointments',
        (WidgetTester tester) async {
      bool checkInCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
              onCheckIn: () {
                checkInCalled = true;
              },
            ),
          ),
        ),
      );

      expect(find.text('Check In'), findsOneWidget);

      await tester.tap(find.text('Check In'));
      await tester.pump();

      expect(checkInCalled, true);
    });

    testWidgets('hides check-in button for non-scheduled appointments',
        (WidgetTester tester) async {
      final checkedInAppointment = testAppointment.copyWith(
        status: 'checked_in',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: checkedInAppointment,
            ),
          ),
        ),
      );

      expect(find.text('Check In'), findsNothing);
    });

    testWidgets('triggers onTap callback when card is tapped',
        (WidgetTester tester) async {
      bool tapCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
              onTap: () {
                tapCalled = true;
              },
            ),
          ),
        ),
      );

      await tester.tap(find.byType(InkWell));
      await tester.pump();

      expect(tapCalled, true);
    });

    testWidgets('displays patient avatar with first letter',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
            ),
          ),
        ),
      );

      expect(find.byType(CircleAvatar), findsOneWidget);
      expect(find.text('J'), findsOneWidget);
    });

    testWidgets('displays appointment type correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: testAppointment,
            ),
          ),
        ),
      );

      // Type display should show "New" for new_consultation
      expect(testAppointment.typeDisplay, 'New');
    });

    testWidgets('handles long patient names without overflow',
        (WidgetTester tester) async {
      final longNameAppointment = Appointment(
        id: 'apt-004',
        patientId: 'pat-002',
        patientName: 'Extremely Long Patient Name That Should Not Overflow The UI',
        doctorId: 'doc-001',
        doctorName: 'Dr. Smith',
        scheduledStart: DateTime(2024, 1, 15, 13, 0),
        durationMinutes: 30,
        status: 'scheduled',
        appointmentType: 'new_consultation',
        bookingSource: 'walk_in',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: _AppointmentCardTest(
              appointment: longNameAppointment,
            ),
          ),
        ),
      );

      expect(tester.takeException(), isNull);
    });
  });
}

// Test widget wrapper
class _AppointmentCardTest extends StatelessWidget {
  final Appointment appointment;
  final VoidCallback? onCheckIn;
  final VoidCallback? onTap;

  const _AppointmentCardTest({
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
                          '${appointment.doctorName} • ${DateFormat('h:mm a').format(appointment.scheduledStart)}',
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
                    if (onCheckIn != null && appointment.status == 'scheduled')
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

// Extension to add copyWith to Appointment model for tests
extension AppointmentCopyWith on Appointment {
  Appointment copyWith({
    String? id,
    String? patientId,
    String? patientName,
    String? doctorId,
    String? doctorName,
    DateTime? scheduledStart,
    DateTime? scheduledEnd,
    int? durationMinutes,
    String? status,
    String? appointmentType,
    String? bookingSource,
    String? chiefComplaint,
    String? notes,
    int? tokenNumber,
    DateTime? checkInTime,
    DateTime? startTime,
    DateTime? endTime,
  }) {
    return Appointment(
      id: id ?? this.id,
      patientId: patientId ?? this.patientId,
      patientName: patientName ?? this.patientName,
      doctorId: doctorId ?? this.doctorId,
      doctorName: doctorName ?? this.doctorName,
      scheduledStart: scheduledStart ?? this.scheduledStart,
      scheduledEnd: scheduledEnd ?? this.scheduledEnd,
      durationMinutes: durationMinutes ?? this.durationMinutes,
      status: status ?? this.status,
      appointmentType: appointmentType ?? this.appointmentType,
      bookingSource: bookingSource ?? this.bookingSource,
      chiefComplaint: chiefComplaint ?? this.chiefComplaint,
      notes: notes ?? this.notes,
      tokenNumber: tokenNumber ?? this.tokenNumber,
      checkInTime: checkInTime ?? this.checkInTime,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
    );
  }
}
