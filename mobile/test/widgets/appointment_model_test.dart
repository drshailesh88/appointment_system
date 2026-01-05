import 'package:flutter_test/flutter_test.dart';

import '../../lib/core/models/appointment.dart';

void main() {
  group('Appointment Model', () {
    test('fromJson should correctly parse appointment data', () {
      final json = {
        'id': 'appt-1',
        'patient_id': 'patient-1',
        'patient_name': 'John Doe',
        'doctor_id': 'doctor-1',
        'doctor_name': 'Dr. Sarah Wilson',
        'scheduled_start': '2024-01-15T10:00:00Z',
        'scheduled_end': '2024-01-15T10:30:00Z',
        'duration_minutes': 30,
        'status': 'scheduled',
        'appointment_type': 'new_consultation',
        'booking_source': 'mobile',
        'chief_complaint': 'Headache',
        'notes': 'Follow-up needed',
        'token_number': 5,
      };

      final appointment = Appointment.fromJson(json);

      expect(appointment.id, 'appt-1');
      expect(appointment.patientName, 'John Doe');
      expect(appointment.doctorName, 'Dr. Sarah Wilson');
      expect(appointment.status, 'scheduled');
      expect(appointment.durationMinutes, 30);
      expect(appointment.chiefComplaint, 'Headache');
      expect(appointment.tokenNumber, 5);
    });

    test('fromJson should handle missing optional fields', () {
      final json = {
        'id': 'appt-1',
        'patient_id': 'patient-1',
        'doctor_id': 'doctor-1',
        'scheduled_start': '2024-01-15T10:00:00Z',
      };

      final appointment = Appointment.fromJson(json);

      expect(appointment.id, 'appt-1');
      expect(appointment.patientName, 'Unknown');
      expect(appointment.doctorName, 'Unknown');
      expect(appointment.status, 'scheduled');
      expect(appointment.durationMinutes, 15);
      expect(appointment.bookingSource, 'walk_in');
      expect(appointment.chiefComplaint, null);
    });

    test('status getters should return correct values', () {
      final scheduled = Appointment(
        id: '1',
        patientId: 'p1',
        patientName: 'John',
        doctorId: 'd1',
        doctorName: 'Dr. Smith',
        scheduledStart: DateTime.now(),
        durationMinutes: 30,
        status: 'scheduled',
        appointmentType: 'new_consultation',
        bookingSource: 'mobile',
      );

      expect(scheduled.isScheduled, true);
      expect(scheduled.isCheckedIn, false);
      expect(scheduled.isCompleted, false);
      expect(scheduled.isCancelled, false);

      final checkedIn = Appointment(
        id: '2',
        patientId: 'p1',
        patientName: 'John',
        doctorId: 'd1',
        doctorName: 'Dr. Smith',
        scheduledStart: DateTime.now(),
        durationMinutes: 30,
        status: 'checked_in',
        appointmentType: 'new_consultation',
        bookingSource: 'mobile',
      );

      expect(checkedIn.isCheckedIn, true);
      expect(checkedIn.isScheduled, false);
    });

    test('statusDisplay should return formatted status', () {
      final testCases = {
        'scheduled': 'Scheduled',
        'confirmed': 'Confirmed',
        'checked_in': 'Checked In',
        'in_progress': 'In Progress',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'no_show': 'No Show',
      };

      testCases.forEach((status, expectedDisplay) {
        final appointment = Appointment(
          id: '1',
          patientId: 'p1',
          patientName: 'John',
          doctorId: 'd1',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now(),
          durationMinutes: 30,
          status: status,
          appointmentType: 'new_consultation',
          bookingSource: 'mobile',
        );

        expect(appointment.statusDisplay, expectedDisplay);
      });
    });

    test('typeDisplay should return formatted type', () {
      final testCases = {
        'new_consultation': 'New',
        'follow_up': 'Follow-up',
        'procedure': 'Procedure',
        'emergency': 'Emergency',
        'teleconsultation': 'Tele',
      };

      testCases.forEach((type, expectedDisplay) {
        final appointment = Appointment(
          id: '1',
          patientId: 'p1',
          patientName: 'John',
          doctorId: 'd1',
          doctorName: 'Dr. Smith',
          scheduledStart: DateTime.now(),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: type,
          bookingSource: 'mobile',
        );

        expect(appointment.typeDisplay, expectedDisplay);
      });
    });

    test('toJson should correctly serialize appointment', () {
      final appointment = Appointment(
        id: 'appt-1',
        patientId: 'patient-1',
        patientName: 'John Doe',
        doctorId: 'doctor-1',
        doctorName: 'Dr. Sarah Wilson',
        scheduledStart: DateTime(2024, 1, 15, 10, 0),
        durationMinutes: 30,
        status: 'scheduled',
        appointmentType: 'new_consultation',
        bookingSource: 'mobile',
        chiefComplaint: 'Headache',
        notes: 'Follow-up needed',
      );

      final json = appointment.toJson();

      expect(json['id'], 'appt-1');
      expect(json['patient_id'], 'patient-1');
      expect(json['doctor_id'], 'doctor-1');
      expect(json['duration_minutes'], 30);
      expect(json['appointment_type'], 'new_consultation');
      expect(json['booking_source'], 'mobile');
      expect(json['chief_complaint'], 'Headache');
      expect(json['notes'], 'Follow-up needed');
    });
  });
}
