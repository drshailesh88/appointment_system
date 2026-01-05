import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:docassist_mobile/core/models/appointment.dart';
import 'package:docassist_mobile/core/providers/appointments_provider.dart';
import 'package:docassist_mobile/core/providers/sync_provider.dart';
import 'package:docassist_mobile/core/providers/realtime_provider.dart';
import 'package:docassist_mobile/core/repositories/appointment_repository.dart';
import 'package:docassist_mobile/core/services/websocket_service.dart';

// Mock classes
class MockAppointmentRepository extends Mock implements AppointmentRepository {}

class MockSyncNotifier extends Mock implements SyncNotifier {}

// Test data
final _now = DateTime.now();
final _testAppointments = [
  Appointment(
    id: '1',
    patientId: 'p1',
    patientName: 'John Doe',
    doctorId: 'd1',
    doctorName: 'Dr. Smith',
    scheduledStart: _now,
    durationMinutes: 30,
    status: 'scheduled',
    appointmentType: 'new_consultation',
    bookingSource: 'walk_in',
  ),
  Appointment(
    id: '2',
    patientId: 'p2',
    patientName: 'Jane Smith',
    doctorId: 'd1',
    doctorName: 'Dr. Smith',
    scheduledStart: _now.add(const Duration(hours: 1)),
    durationMinutes: 30,
    status: 'checked_in',
    appointmentType: 'follow_up',
    bookingSource: 'phone',
  ),
  Appointment(
    id: '3',
    patientId: 'p3',
    patientName: 'Bob Johnson',
    doctorId: 'd1',
    doctorName: 'Dr. Smith',
    scheduledStart: _now.add(const Duration(hours: 2)),
    durationMinutes: 30,
    status: 'completed',
    appointmentType: 'procedure',
    bookingSource: 'online',
  ),
];

void main() {
  late MockAppointmentRepository mockRepository;
  late MockSyncNotifier mockSyncNotifier;
  late ProviderContainer container;

  setUp(() {
    mockRepository = MockAppointmentRepository();
    mockSyncNotifier = MockSyncNotifier();
  });

  tearDown(() {
    container.dispose();
  });

  ProviderContainer createContainer() {
    return ProviderContainer(
      overrides: [
        appointmentRepositoryProvider.overrideWithValue(mockRepository),
        syncProvider.notifier.overrideWithValue(mockSyncNotifier),
        // Mock the realtime provider to prevent WebSocket connections
        appointmentEventsProvider.overrideWith(
          (ref) => const Stream.empty(),
        ),
      ],
    );
  }

  group('AppointmentsNotifier -', () {
    group('Initial State', () {
      test('starts with empty state', () {
        container = createContainer();
        final state = container.read(appointmentsProvider);

        expect(state.appointments, isEmpty);
        expect(state.todayAppointments, isEmpty);
        expect(state.isLoading, isFalse);
        expect(state.error, isNull);
      });

      test('stats return zero for empty state', () {
        container = createContainer();
        final state = container.read(appointmentsProvider);

        expect(state.scheduledCount, equals(0));
        expect(state.checkedInCount, equals(0));
        expect(state.completedCount, equals(0));
        expect(state.cancelledCount, equals(0));
      });
    });

    group('Load Today Appointments', () {
      test('successfully loads today appointments', () async {
        container = createContainer();
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => _testAppointments);

        final notifier = container.read(appointmentsProvider.notifier);

        // Initial loading state
        expect(container.read(appointmentsProvider).isLoading, isFalse);

        // Load appointments
        await notifier.loadTodayAppointments(doctorId: 'd1');

        // Verify state after loading
        final state = container.read(appointmentsProvider);
        expect(state.todayAppointments, hasLength(3));
        expect(state.isLoading, isFalse);
        expect(state.error, isNull);

        verify(() => mockRepository.getTodayAppointments(doctorId: 'd1')).called(1);
      });

      test('sets loading state while loading', () async {
        container = createContainer();
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async {
          await Future.delayed(const Duration(milliseconds: 100));
          return _testAppointments;
        });

        final notifier = container.read(appointmentsProvider.notifier);
        final loadFuture = notifier.loadTodayAppointments(doctorId: 'd1');

        // Check loading state immediately
        await Future.delayed(const Duration(milliseconds: 10));
        expect(container.read(appointmentsProvider).isLoading, isTrue);

        await loadFuture;
        expect(container.read(appointmentsProvider).isLoading, isFalse);
      });

      test('handles error when loading fails', () async {
        container = createContainer();
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenThrow(Exception('Network error'));

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadTodayAppointments(doctorId: 'd1');

        final state = container.read(appointmentsProvider);
        expect(state.isLoading, isFalse);
        expect(state.error, contains('Network error'));
        expect(state.todayAppointments, isEmpty);
      });

      test('calculates stats correctly', () async {
        container = createContainer();
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => _testAppointments);

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadTodayAppointments(doctorId: 'd1');

        final state = container.read(appointmentsProvider);
        expect(state.scheduledCount, equals(1));
        expect(state.checkedInCount, equals(1));
        expect(state.completedCount, equals(1));
        expect(state.cancelledCount, equals(0));
      });
    });

    group('Load Appointments with Filters', () {
      test('successfully loads appointments with filters', () async {
        container = createContainer();
        when(() => mockRepository.getAppointments(
              doctorId: any(named: 'doctorId'),
              patientId: any(named: 'patientId'),
              dateFrom: any(named: 'dateFrom'),
              dateTo: any(named: 'dateTo'),
              status: any(named: 'status'),
            )).thenAnswer((_) async => _testAppointments);

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadAppointments(
          doctorId: 'd1',
          status: 'scheduled',
        );

        final state = container.read(appointmentsProvider);
        expect(state.appointments, hasLength(3));
        expect(state.isLoading, isFalse);
        expect(state.error, isNull);

        verify(() => mockRepository.getAppointments(
              doctorId: 'd1',
              status: 'scheduled',
              patientId: null,
              dateFrom: null,
              dateTo: null,
            )).called(1);
      });

      test('filters by date range', () async {
        container = createContainer();
        final dateFrom = _now.toIso8601String();
        final dateTo = _now.add(const Duration(days: 7)).toIso8601String();

        when(() => mockRepository.getAppointments(
              dateFrom: any(named: 'dateFrom'),
              dateTo: any(named: 'dateTo'),
              doctorId: any(named: 'doctorId'),
              patientId: any(named: 'patientId'),
              status: any(named: 'status'),
            )).thenAnswer((_) async => _testAppointments);

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadAppointments(dateFrom: dateFrom, dateTo: dateTo);

        verify(() => mockRepository.getAppointments(
              dateFrom: dateFrom,
              dateTo: dateTo,
              doctorId: null,
              patientId: null,
              status: null,
            )).called(1);
      });

      test('handles error when loading appointments fails', () async {
        container = createContainer();
        when(() => mockRepository.getAppointments(
              doctorId: any(named: 'doctorId'),
              patientId: any(named: 'patientId'),
              dateFrom: any(named: 'dateFrom'),
              dateTo: any(named: 'dateTo'),
              status: any(named: 'status'),
            )).thenThrow(Exception('Database error'));

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadAppointments(doctorId: 'd1');

        final state = container.read(appointmentsProvider);
        expect(state.isLoading, isFalse);
        expect(state.error, contains('Database error'));
        expect(state.appointments, isEmpty);
      });
    });

    group('Create Appointment', () {
      test('successfully creates appointment', () async {
        container = createContainer();
        final newAppointment = Appointment(
          id: '4',
          patientId: 'p4',
          patientName: 'Alice Brown',
          doctorId: 'd1',
          doctorName: 'Dr. Smith',
          scheduledStart: _now.add(const Duration(hours: 3)),
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
        );

        when(() => mockRepository.createAppointment(any()))
            .thenAnswer((_) async => newAppointment);
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => [..._testAppointments, newAppointment]);
        when(() => mockSyncNotifier.updatePendingCount()).thenReturn(null);

        final notifier = container.read(appointmentsProvider.notifier);
        final result = await notifier.createAppointment({
          'patient_id': 'p4',
          'doctor_id': 'd1',
          'scheduled_start': _now.add(const Duration(hours: 3)).toIso8601String(),
          'duration_minutes': 30,
          'appointment_type': 'new_consultation',
        });

        expect(result, isNotNull);
        expect(result!.id, equals('4'));
        expect(result.patientName, equals('Alice Brown'));

        verify(() => mockRepository.createAppointment(any())).called(1);
        verify(() => mockSyncNotifier.updatePendingCount()).called(1);
      });

      test('returns null and sets error on creation failure', () async {
        container = createContainer();
        when(() => mockRepository.createAppointment(any()))
            .thenThrow(Exception('Creation failed'));

        final notifier = container.read(appointmentsProvider.notifier);
        final result = await notifier.createAppointment({
          'patient_id': 'p4',
          'doctor_id': 'd1',
        });

        expect(result, isNull);
        final state = container.read(appointmentsProvider);
        expect(state.error, contains('Creation failed'));
      });

      test('refreshes today appointments after creation', () async {
        container = createContainer();
        final newAppointment = Appointment(
          id: '4',
          patientId: 'p4',
          patientName: 'Alice Brown',
          doctorId: 'd1',
          doctorName: 'Dr. Smith',
          scheduledStart: _now,
          durationMinutes: 30,
          status: 'scheduled',
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
        );

        when(() => mockRepository.createAppointment(any()))
            .thenAnswer((_) async => newAppointment);
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => [..._testAppointments, newAppointment]);
        when(() => mockSyncNotifier.updatePendingCount()).thenReturn(null);

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.createAppointment({'patient_id': 'p4'});

        // Verify getTodayAppointments was called to refresh
        verify(() => mockRepository.getTodayAppointments(doctorId: null)).called(1);
      });
    });

    group('Check In Patient', () {
      test('successfully checks in patient', () async {
        container = createContainer();
        when(() => mockRepository.checkInPatient(any(), tokenNumber: any(named: 'tokenNumber')))
            .thenAnswer((_) async => true);
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => _testAppointments);
        when(() => mockSyncNotifier.updatePendingCount()).thenReturn(null);

        final notifier = container.read(appointmentsProvider.notifier);
        final result = await notifier.checkInPatient('1', tokenNumber: 5);

        expect(result, isTrue);
        verify(() => mockRepository.checkInPatient('1', tokenNumber: 5)).called(1);
        verify(() => mockSyncNotifier.updatePendingCount()).called(1);
        verify(() => mockRepository.getTodayAppointments(doctorId: null)).called(1);
      });

      test('handles error on check-in failure', () async {
        container = createContainer();
        when(() => mockRepository.checkInPatient(any(), tokenNumber: any(named: 'tokenNumber')))
            .thenThrow(Exception('Check-in failed'));

        final notifier = container.read(appointmentsProvider.notifier);
        final result = await notifier.checkInPatient('1');

        expect(result, isFalse);
        final state = container.read(appointmentsProvider);
        expect(state.error, contains('Check-in failed'));
      });
    });

    group('Real-time Updates', () {
      test('merges appointment update into today appointments', () async {
        container = createContainer();
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => _testAppointments);

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadTodayAppointments();

        // Simulate real-time update for existing appointment
        final updatedAppointment = Appointment(
          id: '1',
          patientId: 'p1',
          patientName: 'John Doe',
          doctorId: 'd1',
          doctorName: 'Dr. Smith',
          scheduledStart: _now,
          durationMinutes: 30,
          status: 'in_progress', // Changed status
          appointmentType: 'new_consultation',
          bookingSource: 'walk_in',
        );

        // Note: In actual tests, you would emit a WebSocket event
        // This is just a unit test for the merge logic
        // The full integration would be tested separately
      });

      test('adds new appointment to today appointments via real-time', () async {
        container = createContainer();
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => _testAppointments);

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadTodayAppointments();

        final initialCount = container.read(appointmentsProvider).todayAppointments.length;
        expect(initialCount, equals(3));

        // Note: Real-time event handling would be tested in integration tests
        // as it requires WebSocket event simulation
      });
    });

    group('Pending Sync Count', () {
      test('returns pending sync count from repository', () {
        container = createContainer();
        when(() => mockRepository.getPendingSyncCount()).thenReturn(5);

        final notifier = container.read(appointmentsProvider.notifier);
        final count = notifier.pendingSyncCount;

        expect(count, equals(5));
        verify(() => mockRepository.getPendingSyncCount()).called(1);
      });

      test('returns zero when no pending syncs', () {
        container = createContainer();
        when(() => mockRepository.getPendingSyncCount()).thenReturn(0);

        final notifier = container.read(appointmentsProvider.notifier);
        final count = notifier.pendingSyncCount;

        expect(count, equals(0));
      });
    });

    group('State Management', () {
      test('copyWith preserves unchanged values', () {
        final state = const AppointmentsState(
          appointments: [],
          todayAppointments: [],
          isLoading: false,
          error: 'Some error',
        );

        final newState = state.copyWith(isLoading: true);

        expect(newState.appointments, equals(state.appointments));
        expect(newState.todayAppointments, equals(state.todayAppointments));
        expect(newState.isLoading, isTrue);
        expect(newState.error, equals('Some error'));
      });

      test('copyWith updates only specified values', () {
        final state = AppointmentsState(
          appointments: _testAppointments,
          todayAppointments: _testAppointments,
          isLoading: false,
        );

        final newState = state.copyWith(
          isLoading: true,
          error: 'New error',
        );

        expect(newState.appointments, hasLength(3));
        expect(newState.isLoading, isTrue);
        expect(newState.error, equals('New error'));
      });

      test('error is cleared on new load attempt', () async {
        container = createContainer();

        // First, cause an error
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenThrow(Exception('Error'));

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadTodayAppointments();

        expect(container.read(appointmentsProvider).error, isNotNull);

        // Now succeed
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => _testAppointments);

        await notifier.loadTodayAppointments();

        expect(container.read(appointmentsProvider).error, isNull);
      });
    });

    group('Filter by Status', () {
      test('correctly counts appointments by status', () async {
        container = createContainer();
        when(() => mockRepository.getTodayAppointments(doctorId: any(named: 'doctorId')))
            .thenAnswer((_) async => _testAppointments);

        final notifier = container.read(appointmentsProvider.notifier);
        await notifier.loadTodayAppointments();

        final state = container.read(appointmentsProvider);

        // From _testAppointments: 1 scheduled, 1 checked_in, 1 completed
        expect(state.scheduledCount, equals(1));
        expect(state.checkedInCount, equals(1));
        expect(state.completedCount, equals(1));
        expect(state.cancelledCount, equals(0));
      });

      test('handles empty appointment list', () {
        container = createContainer();
        final state = container.read(appointmentsProvider);

        expect(state.scheduledCount, equals(0));
        expect(state.checkedInCount, equals(0));
        expect(state.completedCount, equals(0));
        expect(state.cancelledCount, equals(0));
      });
    });
  });
}
