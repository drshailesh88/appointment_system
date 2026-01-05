import 'package:flutter_test/flutter_test.dart';

import '../../lib/core/models/patient.dart';

void main() {
  group('Patient Model', () {
    test('fromJson should correctly parse patient data', () {
      final json = {
        'id': 'patient-1',
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '9876543210',
        'email': 'john.doe@example.com',
        'date_of_birth': '1990-01-15',
        'gender': 'M',
        'address': '123 Main St',
        'city': 'Mumbai',
        'blood_group': 'O+',
        'allergies': 'Penicillin',
        'clinic_id': 'clinic-1',
        'is_active': true,
        'created_at': '2024-01-01T00:00:00Z',
      };

      final patient = Patient.fromJson(json);

      expect(patient.id, 'patient-1');
      expect(patient.firstName, 'John');
      expect(patient.lastName, 'Doe');
      expect(patient.phone, '9876543210');
      expect(patient.email, 'john.doe@example.com');
      expect(patient.gender, 'M');
      expect(patient.bloodGroup, 'O+');
      expect(patient.allergies, 'Penicillin');
      expect(patient.isActive, true);
    });

    test('fullName should combine first and last name', () {
      final patient = Patient(
        id: 'p1',
        firstName: 'John',
        lastName: 'Doe',
        phone: '9876543210',
        clinicId: 'clinic-1',
        isActive: true,
        createdAt: DateTime.now(),
      );

      expect(patient.fullName, 'John Doe');
    });

    test('fullName should return only first name when last name is null', () {
      final patient = Patient(
        id: 'p1',
        firstName: 'John',
        phone: '9876543210',
        clinicId: 'clinic-1',
        isActive: true,
        createdAt: DateTime.now(),
      );

      expect(patient.fullName, 'John');
    });

    test('fullName should return only first name when last name is empty', () {
      final patient = Patient(
        id: 'p1',
        firstName: 'John',
        lastName: '',
        phone: '9876543210',
        clinicId: 'clinic-1',
        isActive: true,
        createdAt: DateTime.now(),
      );

      expect(patient.fullName, 'John');
    });

    test('age should calculate correctly', () {
      final patient = Patient(
        id: 'p1',
        firstName: 'John',
        phone: '9876543210',
        dateOfBirth: DateTime(1990, 1, 15),
        clinicId: 'clinic-1',
        isActive: true,
        createdAt: DateTime.now(),
      );

      final expectedAge = DateTime.now().year - 1990;
      expect(patient.age, expectedAge);
    });

    test('age should return null when date of birth is null', () {
      final patient = Patient(
        id: 'p1',
        firstName: 'John',
        phone: '9876543210',
        clinicId: 'clinic-1',
        isActive: true,
        createdAt: DateTime.now(),
      );

      expect(patient.age, null);
    });

    test('genderDisplay should return formatted gender', () {
      final testCases = {
        'M': 'Male',
        'F': 'Female',
        'O': 'Other',
        null: 'Not specified',
      };

      testCases.forEach((gender, expectedDisplay) {
        final patient = Patient(
          id: 'p1',
          firstName: 'Test',
          phone: '9876543210',
          gender: gender,
          clinicId: 'clinic-1',
          isActive: true,
          createdAt: DateTime.now(),
        );

        expect(patient.genderDisplay, expectedDisplay);
      });
    });
  });
}
