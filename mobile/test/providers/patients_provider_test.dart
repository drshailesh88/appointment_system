import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../lib/core/providers/patients_provider.dart';
import '../../lib/core/providers/sync_provider.dart';
import '../helpers/mock_providers.dart';
import '../helpers/test_data.dart';

void main() {
  late MockPatientRepository mockRepository;
  late MockOfflineSyncService mockSyncService;

  setUp(() {
    mockRepository = MockPatientRepository();
    mockSyncService = MockOfflineSyncService();
  });

  group('PatientsProvider', () {
    test('initial state should be empty', () {
      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final state = container.read(patientsProvider);

      expect(state.patients, isEmpty);
      expect(state.searchResults, isEmpty);
      expect(state.selectedPatient, null);
      expect(state.isLoading, false);
      expect(state.isSearching, false);
      expect(state.error, null);

      container.dispose();
    });

    test('searchPatients should update search results', () async {
      when(() => mockRepository.searchPatients(
            query: any(named: 'query'),
            clinicId: any(named: 'clinicId'),
          )).thenAnswer((_) async => TestData.samplePatients);

      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(patientsProvider.notifier);

      await notifier.searchPatients('John');

      final state = container.read(patientsProvider);

      expect(state.isSearching, false);
      expect(state.searchResults.length, 2);
      expect(state.error, null);

      verify(() => mockRepository.searchPatients(
            query: 'John',
            clinicId: any(named: 'clinicId'),
          )).called(1);

      container.dispose();
    });

    test('searchPatients with short query should clear results', () async {
      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(patientsProvider.notifier);

      await notifier.searchPatients('J'); // Only 1 character

      final state = container.read(patientsProvider);

      expect(state.searchResults, isEmpty);
      verifyNever(() => mockRepository.searchPatients(
            query: any(named: 'query'),
            clinicId: any(named: 'clinicId'),
          ));

      container.dispose();
    });

    test('searchPatients should handle errors', () async {
      when(() => mockRepository.searchPatients(
            query: any(named: 'query'),
            clinicId: any(named: 'clinicId'),
          )).thenThrow(Exception('Search failed'));

      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(patientsProvider.notifier);

      await notifier.searchPatients('John');

      final state = container.read(patientsProvider);

      expect(state.isSearching, false);
      expect(state.error, contains('Search failed'));

      container.dispose();
    });

    test('loadPatient should load patient details', () async {
      when(() => mockRepository.getPatient(any()))
          .thenAnswer((_) async => TestData.samplePatient);

      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(patientsProvider.notifier);

      await notifier.loadPatient('patient-1');

      final state = container.read(patientsProvider);

      expect(state.selectedPatient, isNotNull);
      expect(state.selectedPatient?.id, 'patient-1');
      expect(state.isLoading, false);

      verify(() => mockRepository.getPatient('patient-1')).called(1);

      container.dispose();
    });

    test('createPatient should create new patient', () async {
      final patientData = {
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '9876543210',
      };

      when(() => mockRepository.createPatient(any()))
          .thenAnswer((_) async => TestData.samplePatient);
      when(() => mockSyncService.getPendingItems()).thenReturn([]);

      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(patientsProvider.notifier);

      final result = await notifier.createPatient(patientData);

      expect(result, isNotNull);
      expect(result?.id, 'patient-1');

      verify(() => mockRepository.createPatient(patientData)).called(1);

      container.dispose();
    });

    test('clearSearch should clear search results', () {
      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(patientsProvider.notifier);

      notifier.clearSearch();

      final state = container.read(patientsProvider);

      expect(state.searchResults, isEmpty);

      container.dispose();
    });

    test('clearSelectedPatient should clear selected patient', () {
      final container = ProviderContainer(
        overrides: [
          patientRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(patientsProvider.notifier);

      notifier.clearSelectedPatient();

      final state = container.read(patientsProvider);

      expect(state.selectedPatient, null);

      container.dispose();
    });
  });
}
