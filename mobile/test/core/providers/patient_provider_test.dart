import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:docassist_mobile/core/models/patient.dart';
import 'package:docassist_mobile/core/providers/patients_provider.dart';
import 'package:docassist_mobile/core/providers/sync_provider.dart';
import 'package:docassist_mobile/core/repositories/patient_repository.dart';

// Mock classes
class MockPatientRepository extends Mock implements PatientRepository {}

class MockSyncNotifier extends Mock implements SyncNotifier {}

// Test data
final _testPatients = [
  Patient(
    id: 'p1',
    firstName: 'John',
    lastName: 'Doe',
    phone: '1234567890',
    email: 'john@example.com',
    dateOfBirth: DateTime(1980, 5, 15),
    gender: 'M',
    address: '123 Main St',
    city: 'Mumbai',
    bloodGroup: 'O+',
    allergies: 'Penicillin',
    clinicId: 'c1',
    isActive: true,
    createdAt: DateTime.now().subtract(const Duration(days: 30)),
  ),
  Patient(
    id: 'p2',
    firstName: 'Jane',
    lastName: 'Smith',
    phone: '9876543210',
    email: 'jane@example.com',
    dateOfBirth: DateTime(1990, 8, 22),
    gender: 'F',
    address: '456 Oak Ave',
    city: 'Delhi',
    bloodGroup: 'A+',
    clinicId: 'c1',
    isActive: true,
    createdAt: DateTime.now().subtract(const Duration(days: 15)),
  ),
  Patient(
    id: 'p3',
    firstName: 'Bob',
    lastName: 'Johnson',
    phone: '5555555555',
    dateOfBirth: DateTime(1975, 3, 10),
    gender: 'M',
    city: 'Bangalore',
    bloodGroup: 'B+',
    clinicId: 'c1',
    isActive: true,
    createdAt: DateTime.now().subtract(const Duration(days: 5)),
  ),
];

void main() {
  late MockPatientRepository mockRepository;
  late MockSyncNotifier mockSyncNotifier;
  late ProviderContainer container;

  setUp(() {
    mockRepository = MockPatientRepository();
    mockSyncNotifier = MockSyncNotifier();
  });

  tearDown(() {
    container.dispose();
  });

  ProviderContainer createContainer() {
    return ProviderContainer(
      overrides: [
        patientRepositoryProvider.overrideWithValue(mockRepository),
        syncProvider.notifier.overrideWithValue(mockSyncNotifier),
      ],
    );
  }

  group('PatientsNotifier -', () {
    group('Initial State', () {
      test('starts with empty state', () {
        container = createContainer();
        final state = container.read(patientsProvider);

        expect(state.patients, isEmpty);
        expect(state.searchResults, isEmpty);
        expect(state.selectedPatient, isNull);
        expect(state.isLoading, isFalse);
        expect(state.isSearching, isFalse);
        expect(state.error, isNull);
      });
    });

    group('Search Patients', () {
      test('successfully searches patients', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenAnswer((_) async => _testPatients);

        final notifier = container.read(patientsProvider.notifier);
        await notifier.searchPatients('John', clinicId: 'c1');

        final state = container.read(patientsProvider);
        expect(state.searchResults, hasLength(3));
        expect(state.isSearching, isFalse);
        expect(state.error, isNull);

        verify(() => mockRepository.searchPatients(
              query: 'John',
              clinicId: 'c1',
            )).called(1);
      });

      test('sets searching state while searching', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenAnswer((_) async {
          await Future.delayed(const Duration(milliseconds: 100));
          return _testPatients;
        });

        final notifier = container.read(patientsProvider.notifier);
        final searchFuture = notifier.searchPatients('Jane');

        // Check searching state
        await Future.delayed(const Duration(milliseconds: 10));
        expect(container.read(patientsProvider).isSearching, isTrue);

        await searchFuture;
        expect(container.read(patientsProvider).isSearching, isFalse);
      });

      test('does not search if query is less than 2 characters', () async {
        container = createContainer();

        final notifier = container.read(patientsProvider.notifier);
        await notifier.searchPatients('J');

        final state = container.read(patientsProvider);
        expect(state.searchResults, isEmpty);

        verifyNever(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            ));
      });

      test('clears search results if query is too short', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenAnswer((_) async => _testPatients);

        final notifier = container.read(patientsProvider.notifier);

        // First, do a valid search
        await notifier.searchPatients('John');
        expect(container.read(patientsProvider).searchResults, hasLength(3));

        // Then search with short query
        await notifier.searchPatients('J');
        expect(container.read(patientsProvider).searchResults, isEmpty);
      });

      test('handles error when search fails', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenThrow(Exception('Search failed'));

        final notifier = container.read(patientsProvider.notifier);
        await notifier.searchPatients('John');

        final state = container.read(patientsProvider);
        expect(state.isSearching, isFalse);
        expect(state.error, contains('Search failed'));
        expect(state.searchResults, isEmpty);
      });

      test('searches without clinic filter', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenAnswer((_) async => _testPatients);

        final notifier = container.read(patientsProvider.notifier);
        await notifier.searchPatients('Smith');

        verify(() => mockRepository.searchPatients(
              query: 'Smith',
              clinicId: null,
            )).called(1);
      });

      test('filters results by clinic ID', () async {
        container = createContainer();
        final clinicFilteredPatients = [_testPatients[0]];

        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: 'c1',
            )).thenAnswer((_) async => clinicFilteredPatients);

        final notifier = container.read(patientsProvider.notifier);
        await notifier.searchPatients('John', clinicId: 'c1');

        final state = container.read(patientsProvider);
        expect(state.searchResults, hasLength(1));
      });
    });

    group('Load Patient', () {
      test('successfully loads patient by ID', () async {
        container = createContainer();
        final patient = _testPatients[0];

        when(() => mockRepository.getPatient(any()))
            .thenAnswer((_) async => patient);

        final notifier = container.read(patientsProvider.notifier);
        await notifier.loadPatient('p1');

        final state = container.read(patientsProvider);
        expect(state.selectedPatient, isNotNull);
        expect(state.selectedPatient!.id, equals('p1'));
        expect(state.selectedPatient!.firstName, equals('John'));
        expect(state.isLoading, isFalse);
        expect(state.error, isNull);

        verify(() => mockRepository.getPatient('p1')).called(1);
      });

      test('sets loading state while loading patient', () async {
        container = createContainer();
        when(() => mockRepository.getPatient(any())).thenAnswer((_) async {
          await Future.delayed(const Duration(milliseconds: 100));
          return _testPatients[0];
        });

        final notifier = container.read(patientsProvider.notifier);
        final loadFuture = notifier.loadPatient('p1');

        // Check loading state
        await Future.delayed(const Duration(milliseconds: 10));
        expect(container.read(patientsProvider).isLoading, isTrue);

        await loadFuture;
        expect(container.read(patientsProvider).isLoading, isFalse);
      });

      test('handles error when loading patient fails', () async {
        container = createContainer();
        when(() => mockRepository.getPatient(any()))
            .thenThrow(Exception('Patient not found'));

        final notifier = container.read(patientsProvider.notifier);
        await notifier.loadPatient('p999');

        final state = container.read(patientsProvider);
        expect(state.isLoading, isFalse);
        expect(state.error, contains('Patient not found'));
        expect(state.selectedPatient, isNull);
      });
    });

    group('Create Patient', () {
      test('successfully creates patient', () async {
        container = createContainer();
        final newPatient = Patient(
          id: 'p4',
          firstName: 'Alice',
          lastName: 'Brown',
          phone: '1112223333',
          email: 'alice@example.com',
          clinicId: 'c1',
          isActive: true,
          createdAt: DateTime.now(),
        );

        when(() => mockRepository.createPatient(any()))
            .thenAnswer((_) async => newPatient);
        when(() => mockSyncNotifier.updatePendingCount()).thenReturn(null);

        final notifier = container.read(patientsProvider.notifier);
        final result = await notifier.createPatient({
          'first_name': 'Alice',
          'last_name': 'Brown',
          'phone': '1112223333',
          'email': 'alice@example.com',
          'clinic_id': 'c1',
        });

        expect(result, isNotNull);
        expect(result!.id, equals('p4'));
        expect(result.firstName, equals('Alice'));
        expect(result.lastName, equals('Brown'));

        verify(() => mockRepository.createPatient(any())).called(1);
        verify(() => mockSyncNotifier.updatePendingCount()).called(1);

        final state = container.read(patientsProvider);
        expect(state.isLoading, isFalse);
        expect(state.error, isNull);
      });

      test('sets loading state while creating patient', () async {
        container = createContainer();
        final newPatient = Patient(
          id: 'p4',
          firstName: 'Alice',
          phone: '1112223333',
          clinicId: 'c1',
          isActive: true,
          createdAt: DateTime.now(),
        );

        when(() => mockRepository.createPatient(any())).thenAnswer((_) async {
          await Future.delayed(const Duration(milliseconds: 100));
          return newPatient;
        });
        when(() => mockSyncNotifier.updatePendingCount()).thenReturn(null);

        final notifier = container.read(patientsProvider.notifier);
        final createFuture = notifier.createPatient({'first_name': 'Alice'});

        // Check loading state
        await Future.delayed(const Duration(milliseconds: 10));
        expect(container.read(patientsProvider).isLoading, isTrue);

        await createFuture;
        expect(container.read(patientsProvider).isLoading, isFalse);
      });

      test('returns null and sets error on creation failure', () async {
        container = createContainer();
        when(() => mockRepository.createPatient(any()))
            .thenThrow(Exception('Validation error'));

        final notifier = container.read(patientsProvider.notifier);
        final result = await notifier.createPatient({
          'first_name': 'Alice',
        });

        expect(result, isNull);

        final state = container.read(patientsProvider);
        expect(state.isLoading, isFalse);
        expect(state.error, contains('Validation error'));
      });

      test('updates sync pending count after creation', () async {
        container = createContainer();
        final newPatient = Patient(
          id: 'p4',
          firstName: 'Alice',
          phone: '1112223333',
          clinicId: 'c1',
          isActive: true,
          createdAt: DateTime.now(),
        );

        when(() => mockRepository.createPatient(any()))
            .thenAnswer((_) async => newPatient);
        when(() => mockSyncNotifier.updatePendingCount()).thenReturn(null);

        final notifier = container.read(patientsProvider.notifier);
        await notifier.createPatient({'first_name': 'Alice'});

        verify(() => mockSyncNotifier.updatePendingCount()).called(1);
      });
    });

    group('Clear Search', () {
      test('clears search results', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenAnswer((_) async => _testPatients);

        final notifier = container.read(patientsProvider.notifier);

        // First, do a search
        await notifier.searchPatients('John');
        expect(container.read(patientsProvider).searchResults, hasLength(3));

        // Then clear search
        notifier.clearSearch();
        expect(container.read(patientsProvider).searchResults, isEmpty);
      });

      test('does not affect other state properties', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenAnswer((_) async => _testPatients);
        when(() => mockRepository.getPatient(any()))
            .thenAnswer((_) async => _testPatients[0]);

        final notifier = container.read(patientsProvider.notifier);

        // Load a patient
        await notifier.loadPatient('p1');

        // Do a search
        await notifier.searchPatients('John');

        // Clear search
        notifier.clearSearch();

        final state = container.read(patientsProvider);
        expect(state.searchResults, isEmpty);
        expect(state.selectedPatient, isNotNull); // Should still be there
      });
    });

    group('Clear Selected Patient', () {
      test('clears selected patient', () async {
        container = createContainer();
        when(() => mockRepository.getPatient(any()))
            .thenAnswer((_) async => _testPatients[0]);

        final notifier = container.read(patientsProvider.notifier);

        // First, load a patient
        await notifier.loadPatient('p1');
        expect(container.read(patientsProvider).selectedPatient, isNotNull);

        // Then clear selected patient
        notifier.clearSelectedPatient();
        expect(container.read(patientsProvider).selectedPatient, isNull);
      });

      test('does not affect search results', () async {
        container = createContainer();
        when(() => mockRepository.searchPatients(
              query: any(named: 'query'),
              clinicId: any(named: 'clinicId'),
            )).thenAnswer((_) async => _testPatients);
        when(() => mockRepository.getPatient(any()))
            .thenAnswer((_) async => _testPatients[0]);

        final notifier = container.read(patientsProvider.notifier);

        // Do a search
        await notifier.searchPatients('John');

        // Load a patient
        await notifier.loadPatient('p1');

        // Clear selected patient
        notifier.clearSelectedPatient();

        final state = container.read(patientsProvider);
        expect(state.selectedPatient, isNull);
        expect(state.searchResults, hasLength(3)); // Should still be there
      });
    });

    group('State Management', () {
      test('copyWith preserves unchanged values', () {
        final state = PatientsState(
          patients: _testPatients,
          searchResults: [_testPatients[0]],
          selectedPatient: _testPatients[0],
          isLoading: false,
          isSearching: false,
          error: 'Some error',
        );

        final newState = state.copyWith(isLoading: true);

        expect(newState.patients, equals(state.patients));
        expect(newState.searchResults, equals(state.searchResults));
        expect(newState.selectedPatient, equals(state.selectedPatient));
        expect(newState.isLoading, isTrue);
        expect(newState.isSearching, isFalse);
        expect(newState.error, equals('Some error'));
      });

      test('copyWith updates only specified values', () {
        final state = const PatientsState();

        final newState = state.copyWith(
          isLoading: true,
          error: 'New error',
        );

        expect(newState.patients, isEmpty);
        expect(newState.searchResults, isEmpty);
        expect(newState.isLoading, isTrue);
        expect(newState.error, equals('New error'));
      });

      test('error is cleared on new operation', () async {
        container = createContainer();

        // First, cause an error
        when(() => mockRepository.getPatient(any()))
            .thenThrow(Exception('Error'));

        final notifier = container.read(patientsProvider.notifier);
        await notifier.loadPatient('p1');

        expect(container.read(patientsProvider).error, isNotNull);

        // Now succeed
        when(() => mockRepository.getPatient(any()))
            .thenAnswer((_) async => _testPatients[0]);

        await notifier.loadPatient('p1');

        expect(container.read(patientsProvider).error, isNull);
      });
    });

    group('Patient Model Helpers', () {
      test('fullName concatenates first and last name', () {
        final patient = _testPatients[0];
        expect(patient.fullName, equals('John Doe'));
      });

      test('fullName returns only first name if last name is null', () {
        final patient = Patient(
          id: 'p99',
          firstName: 'SingleName',
          phone: '1234567890',
          clinicId: 'c1',
          isActive: true,
          createdAt: DateTime.now(),
        );
        expect(patient.fullName, equals('SingleName'));
      });

      test('age calculation is correct', () {
        final patient = _testPatients[0]; // DOB: 1980-05-15
        final age = patient.age;

        expect(age, isNotNull);
        expect(age! >= 43 && age <= 45, isTrue); // Approximate age range
      });

      test('age is null when date of birth is null', () {
        final patient = Patient(
          id: 'p99',
          firstName: 'NoAge',
          phone: '1234567890',
          clinicId: 'c1',
          isActive: true,
          createdAt: DateTime.now(),
        );
        expect(patient.age, isNull);
      });

      test('genderDisplay returns correct display text', () {
        expect(_testPatients[0].genderDisplay, equals('Male'));
        expect(_testPatients[1].genderDisplay, equals('Female'));
      });
    });

    group('EMR Sync', () {
      test('patient creation triggers sync update', () async {
        container = createContainer();
        final newPatient = Patient(
          id: 'p4',
          firstName: 'EMR',
          lastName: 'Patient',
          phone: '9999999999',
          clinicId: 'c1',
          isActive: true,
          createdAt: DateTime.now(),
        );

        when(() => mockRepository.createPatient(any()))
            .thenAnswer((_) async => newPatient);
        when(() => mockSyncNotifier.updatePendingCount()).thenReturn(null);

        final notifier = container.read(patientsProvider.notifier);
        await notifier.createPatient({
          'first_name': 'EMR',
          'last_name': 'Patient',
          'phone': '9999999999',
        });

        // Verify sync notifier was called (EMR sync integration)
        verify(() => mockSyncNotifier.updatePendingCount()).called(1);
      });
    });
  });
}
