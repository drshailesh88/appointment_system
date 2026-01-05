import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../lib/core/providers/appointments_provider.dart';
import '../../lib/core/providers/sync_provider.dart';
import '../../lib/core/models/appointment.dart';
import '../helpers/mock_providers.dart';
import '../helpers/test_data.dart';

void main() {
  late MockAppointmentRepository mockRepository;
  late MockOfflineSyncService mockSyncService;

  setUp(() {
    mockRepository = MockAppointmentRepository();
    mockSyncService = MockOfflineSyncService();
  });

  group('AppointmentsProvider', () {
    test('initial state should be empty', () {
      final container = ProviderContainer(
        overrides: [
          appointmentRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final state = container.read(appointmentsProvider);

      expect(state.appointments, isEmpty);
      expect(state.todayAppointments, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, null);

      container.dispose();
    });

    test('loadTodayAppointments should update state with appointments', () async {
      when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
          .thenAnswer((_) async => TestData.sampleAppointments);

      final container = ProviderContainer(
        overrides: [
          appointmentRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(appointmentsProvider.notifier);

      // Trigger load
      await notifier.loadTodayAppointments();

      final state = container.read(appointmentsProvider);

      expect(state.isLoading, false);
      expect(state.todayAppointments.length, 3);
      expect(state.error, null);

      verify(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId'))).called(1);

      container.dispose();
    });

    test('loadTodayAppointments should handle errors', () async {
      when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
          .thenThrow(Exception('Network error'));

      final container = ProviderContainer(
        overrides: [
          appointmentRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(appointmentsProvider.notifier);

      await notifier.loadTodayAppointments();

      final state = container.read(appointmentsProvider);

      expect(state.isLoading, false);
      expect(state.error, contains('Network error'));
      expect(state.todayAppointments, isEmpty);

      container.dispose();
    });

    test('loadAppointments with filters should fetch appointments', () async {
      when(() => mockRepository.getAppointments(
            doctorId: any(named: 'doctorId'),
            patientId: any(named: 'patientId'),
            dateFrom: any(named: 'dateFrom'),
            dateTo: any(named: 'dateTo'),
            status: any(named: 'status'),
          )).thenAnswer((_) async => [TestData.sampleAppointment]);

      final container = ProviderContainer(
        overrides: [
          appointmentRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(appointmentsProvider.notifier);

      await notifier.loadAppointments(
        doctorId: 'doctor-1',
        status: 'scheduled',
      );

      final state = container.read(appointmentsProvider);

      expect(state.appointments.length, 1);
      expect(state.appointments.first.status, 'scheduled');

      container.dispose();
    });

    test('createAppointment should create and refresh list', () async {
      final appointmentData = {
        'patient_id': 'patient-1',
        'doctor_id': 'doctor-1',
        'scheduled_start': DateTime.now().toIso8601String(),
        'duration_minutes': 30,
      };

      when(() => mockRepository.createAppointment(any()))
          .thenAnswer((_) async => TestData.sampleAppointment);
      when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
          .thenAnswer((_) async => [TestData.sampleAppointment]);
      when(() => mockSyncService.getPendingItems()).thenReturn([]);

      final container = ProviderContainer(
        overrides: [
          appointmentRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(appointmentsProvider.notifier);

      final result = await notifier.createAppointment(appointmentData);

      expect(result, isNotNull);
      expect(result?.id, 'appt-1');

      verify(() => mockRepository.createAppointment(appointmentData)).called(1);
      verify(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId'))).called(1);

      container.dispose();
    });

    test('checkInPatient should check in and refresh', () async {
      when(() => mockRepository.checkInPatient(any(), tokenNumber: any(named: 'tokenNumber')))
          .thenAnswer((_) async => {});
      when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
          .thenAnswer((_) async => [TestData.checkedInAppointment]);
      when(() => mockSyncService.getPendingItems()).thenReturn([]);

      final container = ProviderContainer(
        overrides: [
          appointmentRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      final notifier = container.read(appointmentsProvider.notifier);

      final result = await notifier.checkInPatient('appt-1', tokenNumber: 5);

      expect(result, true);

      verify(() => mockRepository.checkInPatient('appt-1', tokenNumber: 5)).called(1);

      container.dispose();
    });

    test('stats should calculate correctly', () {
      final container = ProviderContainer(
        overrides: [
          appointmentRepositoryProvider.overrideWithValue(mockRepository),
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
          .thenAnswer((_) async => TestData.sampleAppointments);

      final notifier = container.read(appointmentsProvider.notifier);

      notifier.loadTodayAppointments().then((_) {
        final state = container.read(appointmentsProvider);

        expect(state.scheduledCount, 1);
        expect(state.checkedInCount, 1);
        expect(state.completedCount, 1);
        expect(state.cancelledCount, 0);
      });

      container.dispose();
    });
  });
}
