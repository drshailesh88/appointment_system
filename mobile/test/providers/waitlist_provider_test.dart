import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../lib/core/providers/waitlist_provider.dart';
import '../helpers/mock_providers.dart';

void main() {
  late MockApiClient mockApiClient;

  setUp(() {
    mockApiClient = MockApiClient();
  });

  group('WaitlistProvider', () {
    test('initial state should be empty', () {
      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final state = container.read(waitlistProvider);

      expect(state.entries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, null);
      expect(state.selectedEntry, null);

      container.dispose();
    });

    test('loadWaitlist should fetch entries', () async {
      final mockEntries = [
        {
          'id': 'wl-1',
          'patient_id': 'patient-1',
          'patient_name': 'John Doe',
          'priority': 'normal',
          'status': 'waiting',
          'queue_position': 1,
          'created_at': '2024-01-01T10:00:00Z',
        },
        {
          'id': 'wl-2',
          'patient_id': 'patient-2',
          'patient_name': 'Jane Smith',
          'priority': 'urgent',
          'status': 'offered',
          'queue_position': 2,
          'created_at': '2024-01-01T10:00:00Z',
          'slot_offer_expires_at': '2024-01-01T12:00:00Z',
        },
      ];

      when(() => mockApiClient.get(any())).thenAnswer((_) async => mockEntries);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);

      await notifier.loadWaitlist();

      final state = container.read(waitlistProvider);

      expect(state.isLoading, false);
      expect(state.entries.length, 2);
      expect(state.entries[0].id, 'wl-1');
      expect(state.entries[0].priority, WaitlistPriority.normal);
      expect(state.entries[1].status, WaitlistStatus.offered);

      verify(() => mockApiClient.get('/waitlist')).called(1);

      container.dispose();
    });

    test('loadWaitlist with filters should include query params', () async {
      when(() => mockApiClient.get(any())).thenAnswer((_) async => []);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);

      await notifier.loadWaitlist(doctorId: 'doctor-1', status: 'waiting');

      verify(() => mockApiClient.get('/waitlist?doctor_id=doctor-1&status=waiting')).called(1);

      container.dispose();
    });

    test('addToWaitlist should add entry and refresh list', () async {
      when(() => mockApiClient.post(any(), any())).thenAnswer((_) async => {'id': 'wl-1'});
      when(() => mockApiClient.get(any())).thenAnswer((_) async => []);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);

      final result = await notifier.addToWaitlist(
        patientId: 'patient-1',
        doctorId: 'doctor-1',
        priority: 'urgent',
      );

      expect(result, true);

      verify(() => mockApiClient.post('/waitlist', {
            'patient_id': 'patient-1',
            'doctor_id': 'doctor-1',
            'priority': 'urgent',
          })).called(1);

      verify(() => mockApiClient.get('/waitlist')).called(1);

      container.dispose();
    });

    test('confirmSlot should confirm entry', () async {
      when(() => mockApiClient.post(any(), any())).thenAnswer((_) async => {'success': true});
      when(() => mockApiClient.get(any())).thenAnswer((_) async => []);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);

      final result = await notifier.confirmSlot('wl-1');

      expect(result, true);

      verify(() => mockApiClient.post('/waitlist/wl-1/confirm', {})).called(1);

      container.dispose();
    });

    test('declineSlot should decline entry', () async {
      when(() => mockApiClient.post(any(), any())).thenAnswer((_) async => {'success': true});
      when(() => mockApiClient.get(any())).thenAnswer((_) async => []);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);

      final result = await notifier.declineSlot('wl-1');

      expect(result, true);

      verify(() => mockApiClient.post('/waitlist/wl-1/decline', {})).called(1);

      container.dispose();
    });

    test('cancelEntry should delete entry', () async {
      when(() => mockApiClient.delete(any())).thenAnswer((_) async => null);
      when(() => mockApiClient.get(any())).thenAnswer((_) async => []);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);

      final result = await notifier.cancelEntry('wl-1');

      expect(result, true);

      verify(() => mockApiClient.delete('/waitlist/wl-1')).called(1);

      container.dispose();
    });

    test('updatePriority should update entry priority', () async {
      when(() => mockApiClient.put(any(), any())).thenAnswer((_) async => {'success': true});
      when(() => mockApiClient.get(any())).thenAnswer((_) async => []);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);

      final result = await notifier.updatePriority('wl-1', 'emergency');

      expect(result, true);

      verify(() => mockApiClient.put('/waitlist/wl-1', {'priority': 'emergency'})).called(1);

      container.dispose();
    });

    test('state getters should filter entries correctly', () async {
      final mockEntries = [
        {
          'id': 'wl-1',
          'patient_id': 'patient-1',
          'patient_name': 'John Doe',
          'priority': 'emergency',
          'status': 'waiting',
          'queue_position': 1,
          'created_at': '2024-01-01T10:00:00Z',
        },
        {
          'id': 'wl-2',
          'patient_id': 'patient-2',
          'patient_name': 'Jane Smith',
          'priority': 'normal',
          'status': 'offered',
          'queue_position': 2,
          'created_at': '2024-01-01T10:00:00Z',
        },
        {
          'id': 'wl-3',
          'patient_id': 'patient-3',
          'patient_name': 'Bob Johnson',
          'priority': 'normal',
          'status': 'waiting',
          'queue_position': 3,
          'created_at': '2024-01-01T10:00:00Z',
        },
      ];

      when(() => mockApiClient.get(any())).thenAnswer((_) async => mockEntries);

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );

      final notifier = container.read(waitlistProvider.notifier);
      await notifier.loadWaitlist();

      final state = container.read(waitlistProvider);

      expect(state.waitingEntries.length, 2);
      expect(state.offeredEntries.length, 1);
      expect(state.emergencyEntries.length, 1);

      container.dispose();
    });
  });

  group('WaitlistEntry', () {
    test('fromJson should parse entry correctly', () {
      final json = {
        'id': 'wl-1',
        'patient_id': 'patient-1',
        'patient_name': 'John Doe',
        'doctor_id': 'doctor-1',
        'doctor_name': 'Dr. Smith',
        'preferred_date': '2024-01-15',
        'preferred_time_slot': 'morning',
        'priority': 'urgent',
        'status': 'offered',
        'queue_position': 5,
        'notes': 'Needs urgent care',
        'created_at': '2024-01-01T10:00:00Z',
        'slot_offer_expires_at': '2024-01-01T12:00:00Z',
      };

      final entry = WaitlistEntry.fromJson(json);

      expect(entry.id, 'wl-1');
      expect(entry.patientName, 'John Doe');
      expect(entry.priority, WaitlistPriority.urgent);
      expect(entry.status, WaitlistStatus.offered);
      expect(entry.queuePosition, 5);
    });

    test('hasActiveOffer should return true for valid offer', () {
      final futureExpiry = DateTime.now().add(const Duration(hours: 1));

      final entry = WaitlistEntry(
        id: 'wl-1',
        patientId: 'patient-1',
        patientName: 'John Doe',
        priority: WaitlistPriority.normal,
        status: WaitlistStatus.offered,
        queuePosition: 1,
        createdAt: DateTime.now(),
        expiresAt: futureExpiry,
      );

      expect(entry.hasActiveOffer, true);
    });

    test('hasActiveOffer should return false for expired offer', () {
      final pastExpiry = DateTime.now().subtract(const Duration(hours: 1));

      final entry = WaitlistEntry(
        id: 'wl-1',
        patientId: 'patient-1',
        patientName: 'John Doe',
        priority: WaitlistPriority.normal,
        status: WaitlistStatus.offered,
        queuePosition: 1,
        createdAt: DateTime.now(),
        expiresAt: pastExpiry,
      );

      expect(entry.hasActiveOffer, false);
    });
  });
}
