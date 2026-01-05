import '../../lib/core/models/appointment.dart';
import '../../lib/core/models/patient.dart';
import '../../lib/core/models/doctor.dart';

/// Test data helpers
class TestData {
  /// Sample patient
  static Patient get samplePatient => Patient(
        id: 'patient-1',
        firstName: 'John',
        lastName: 'Doe',
        phone: '9876543210',
        email: 'john.doe@example.com',
        dateOfBirth: DateTime(1990, 1, 15),
        gender: 'M',
        address: '123 Main St',
        city: 'Mumbai',
        bloodGroup: 'O+',
        allergies: 'None',
        clinicId: 'clinic-1',
        isActive: true,
        createdAt: DateTime(2024, 1, 1),
      );

  /// Sample patient 2
  static Patient get samplePatient2 => Patient(
        id: 'patient-2',
        firstName: 'Jane',
        lastName: 'Smith',
        phone: '9876543211',
        email: 'jane.smith@example.com',
        dateOfBirth: DateTime(1985, 6, 20),
        gender: 'F',
        clinicId: 'clinic-1',
        isActive: true,
        createdAt: DateTime(2024, 1, 2),
      );

  /// Sample doctor
  static Doctor get sampleDoctor => Doctor(
        id: 'doctor-1',
        name: 'Dr. Sarah Wilson',
        specialization: 'Cardiologist',
        phone: '9876543220',
        email: 'sarah.wilson@example.com',
        clinicId: 'clinic-1',
        consultationFee: 500.0,
        slotDuration: 15,
        isActive: true,
        acceptingNewPatients: true,
      );

  /// Sample appointment
  static Appointment get sampleAppointment => Appointment(
        id: 'appt-1',
        patientId: 'patient-1',
        patientName: 'John Doe',
        doctorId: 'doctor-1',
        doctorName: 'Dr. Sarah Wilson',
        scheduledStart: DateTime.now().add(const Duration(hours: 2)),
        durationMinutes: 30,
        status: 'scheduled',
        appointmentType: 'new_consultation',
        bookingSource: 'mobile',
        chiefComplaint: 'Chest pain',
      );

  /// Sample appointment (checked in)
  static Appointment get checkedInAppointment => Appointment(
        id: 'appt-2',
        patientId: 'patient-2',
        patientName: 'Jane Smith',
        doctorId: 'doctor-1',
        doctorName: 'Dr. Sarah Wilson',
        scheduledStart: DateTime.now().add(const Duration(hours: 1)),
        durationMinutes: 15,
        status: 'checked_in',
        appointmentType: 'follow_up',
        bookingSource: 'mobile',
        tokenNumber: 5,
        checkInTime: DateTime.now(),
      );

  /// Sample appointment (completed)
  static Appointment get completedAppointment => Appointment(
        id: 'appt-3',
        patientId: 'patient-1',
        patientName: 'John Doe',
        doctorId: 'doctor-1',
        doctorName: 'Dr. Sarah Wilson',
        scheduledStart: DateTime.now().subtract(const Duration(hours: 2)),
        durationMinutes: 30,
        status: 'completed',
        appointmentType: 'new_consultation',
        bookingSource: 'mobile',
        startTime: DateTime.now().subtract(const Duration(hours: 2)),
        endTime: DateTime.now().subtract(const Duration(hours: 1, minutes: 30)),
      );

  /// Sample list of appointments
  static List<Appointment> get sampleAppointments => [
        sampleAppointment,
        checkedInAppointment,
        completedAppointment,
      ];

  /// Sample list of patients
  static List<Patient> get samplePatients => [
        samplePatient,
        samplePatient2,
      ];

  /// Sample auth response data
  static Map<String, dynamic> get authResponseData => {
        'access_token': 'test-access-token',
        'refresh_token': 'test-refresh-token',
        'token_type': 'bearer',
        'expires_in': 3600,
      };

  /// Sample user payload (JWT decoded)
  static Map<String, dynamic> get userPayload => {
        'sub': 'user-1',
        'role': 'doctor',
        'clinic_id': 'clinic-1',
      };
}
