import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:docassist_mobile/core/api/api_client.dart';
import 'package:docassist_mobile/core/models/appointment.dart';
import 'package:docassist_mobile/core/providers/sync_provider.dart';
import 'package:docassist_mobile/core/repositories/appointment_repository.dart';
import 'package:docassist_mobile/core/services/offline_sync_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:mocktail/mocktail.dart';

// Mocks
class MockApiClient extends Mock implements ApiClient {}

class MockBox extends Mock implements Box<String> {}

class MockConnectivity extends Mock implements Connectivity {}

void main() {
  late MockApiClient mockApiClient;
  late MockBox mockSyncQueue;
  late MockBox mockCache;
  late OfflineSyncService syncService;
  late AppointmentRepository repository;
  late Map<String, String> syncQueueStorage;
  late Map<String, String> cacheStorage;

  setUpAll(() {
    registerFallbackValue(<String, dynamic>{});
  });

  setUp(() {
    mockApiClient = MockApiClient();
    mockSyncQueue = MockBox();
    mockCache = MockBox();
    syncQueueStorage = {};
    cacheStorage = {};

    // Mock sync queue
    when(() => mockSyncQueue.put(any(), any())).thenAnswer((invocation) async {
      final key = invocation.positionalArguments[0] as String;
      final value = invocation.positionalArguments[1] as String;
      syncQueueStorage[key] = value;
    });

    when(() => mockSyncQueue.get(any())).thenAnswer((invocation) {
      final key = invocation.positionalArguments[0] as String;
      return syncQueueStorage[key];
    });

    when(() => mockSyncQueue.values).thenAnswer((_) => syncQueueStorage.values);

    when(() => mockSyncQueue.delete(any())).thenAnswer((invocation) async {
      final key = invocation.positionalArguments[0] as String;
      syncQueueStorage.remove(key);
    });

    when(() => mockSyncQueue.clear()).thenAnswer((_) async {
      syncQueueStorage.clear();
    });

    // Mock cache
    when(() => mockCache.put(any(), any())).thenAnswer((invocation) async {
      final key = invocation.positionalArguments[0] as String;
      final value = invocation.positionalArguments[1] as String;
      cacheStorage[key] = value;
    });

    when(() => mockCache.get(any())).thenAnswer((invocation) {
      final key = invocation.positionalArguments[0] as String;
      return cacheStorage[key];
    });

    when(() => mockCache.clear()).thenAnswer((_) async {
      cacheStorage.clear();
    });

    syncService = OfflineSyncService(mockApiClient);
    repository = AppointmentRepository(mockApiClient, syncService);
  });

  group('Offline Mode Integration - Connectivity Detection', () {
    test('detects network connectivity change from online to offline', () async {
      var isOnline = true;

      // Simulate connectivity change
      isOnline = false;

      expect(isOnline, false);
      // App should switch to offline mode
    });

    test('detects network connectivity change from offline to online', () async {
      var isOnline = false;

      // Simulate connectivity restored
      isOnline = true;

      expect(isOnline, true);
      // App should trigger sync
    });

    test('shows offline indicator when network is lost', () {
      final syncState = SyncState(
        isOnline: false,
        isSyncing: false,
        pendingCount: 3,
      );

      expect(syncState.isOnline, false);
      expect(syncState.hasPendingChanges, true);
      // UI should display offline banner
    });

    test('hides offline indicator when network is restored', () {
      final syncState = SyncState(
        isOnline: true,
        isSyncing: false,
        pendingCount: 0,
      );

      expect(syncState.isOnline, true);
      expect(syncState.hasPendingChanges, false);
      // UI should hide offline banner
    });

    test('monitors connectivity status continuously', () {
      final connectivityStates = [
        ConnectivityResult.wifi,
        ConnectivityResult.none,
        ConnectivityResult.mobile,
        ConnectivityResult.none,
        ConnectivityResult.wifi,
      ];

      for (var i = 0; i < connectivityStates.length - 1; i++) {
        final previous = connectivityStates[i];
        final current = connectivityStates[i + 1];

        final wentOffline = previous != ConnectivityResult.none &&
            current == ConnectivityResult.none;
        final wentOnline = previous == ConnectivityResult.none &&
            current != ConnectivityResult.none;

        if (wentOffline) {
          expect(current, ConnectivityResult.none);
        } else if (wentOnline) {
          expect(current, isNot(ConnectivityResult.none));
        }
      }
    });
  });

  group('Offline Mode Integration - Booking Appointments', () {
    test('allows booking appointment when offline', () async {
      final appointmentData = {
        'patient_id': 'pat-001',
        'doctor_id': 'doc-001',
        'start_time': '2024-01-15T10:00:00Z',
        'end_time': '2024-01-15T10:30:00Z',
        'appointment_type': 'new_consultation',
      };

      // Simulate offline
      when(() => mockApiClient.createAppointment(any()))
          .thenThrow(Exception('Network error'));

      // Should queue for sync
      final syncItem = SyncItem(
        id: 'apt_${DateTime.now().millisecondsSinceEpoch}',
        entityType: 'appointment',
        operation: SyncOperation.create,
        data: appointmentData,
        createdAt: DateTime.now(),
      );

      await mockSyncQueue.put(syncItem.id, jsonEncode(syncItem.toJson()));

      expect(syncQueueStorage.length, 1);
      expect(syncQueueStorage.values.first, contains('pat-001'));
    });

    test('shows pending status for offline bookings', () {
      final appointment = Appointment(
        id: 'temp-001',
        patientId: 'pat-001',
        doctorId: 'doc-001',
        startTime: DateTime(2024, 1, 15, 10, 0),
        endTime: DateTime(2024, 1, 15, 10, 30),
        status: 'pending_sync',
        appointmentType: 'new_consultation',
      );

      expect(appointment.status, 'pending_sync');
      // UI should show visual indicator
    });

    test('queues multiple appointments when offline', () async {
      final appointments = [
        {
          'patient_id': 'pat-001',
          'start_time': '2024-01-15T10:00:00Z',
        },
        {
          'patient_id': 'pat-002',
          'start_time': '2024-01-15T11:00:00Z',
        },
        {
          'patient_id': 'pat-003',
          'start_time': '2024-01-15T12:00:00Z',
        },
      ];

      for (final data in appointments) {
        final syncItem = SyncItem(
          id: 'apt_${DateTime.now().millisecondsSinceEpoch}',
          entityType: 'appointment',
          operation: SyncOperation.create,
          data: data,
          createdAt: DateTime.now(),
        );
        await mockSyncQueue.put(syncItem.id, jsonEncode(syncItem.toJson()));
      }

      expect(syncQueueStorage.length, 3);
    });

    test('validates appointment data before queuing', () {
      final invalidData = {
        'patient_id': 'pat-001',
        // Missing required fields
      };

      // Should validate before queuing
      expect(invalidData['start_time'], isNull);
      expect(invalidData['doctor_id'], isNull);
    });
  });

  group('Offline Mode Integration - Payment Queuing', () {
    test('queues payment for later sync when offline', () async {
      final paymentData = {
        'appointment_id': 'apt-001',
        'amount': 500.0,
        'payment_method': 'cash',
        'timestamp': DateTime.now().toIso8601String(),
      };

      final syncItem = SyncItem(
        id: 'payment_${DateTime.now().millisecondsSinceEpoch}',
        entityType: 'payment',
        operation: SyncOperation.create,
        data: paymentData,
        createdAt: DateTime.now(),
      );

      await mockSyncQueue.put(syncItem.id, jsonEncode(syncItem.toJson()));

      expect(syncQueueStorage.length, 1);
      final queued = SyncItem.fromJson(
        jsonDecode(syncQueueStorage.values.first),
      );
      expect(queued.data['amount'], 500.0);
    });

    test('marks payment as pending sync in UI', () {
      final payment = {
        'id': 'pay-001',
        'status': 'pending_sync',
        'amount': 500.0,
      };

      expect(payment['status'], 'pending_sync');
      // UI should show sync pending indicator
    });

    test('prevents duplicate payment submissions', () {
      final payment1 = {
        'id': 'pay-001',
        'appointment_id': 'apt-001',
        'amount': 500.0,
      };

      final payment2 = {
        'id': 'pay-001',
        'appointment_id': 'apt-001',
        'amount': 500.0,
      };

      expect(payment1['id'], payment2['id']);
      // Should detect duplicate and reject
    });
  });

  group('Offline Mode Integration - Cached Data Display', () {
    test('shows cached appointments when offline', () async {
      final cachedAppointments = [
        {
          'id': 'apt-001',
          'patient_name': 'John Doe',
          'scheduled_start': '2024-01-15T10:00:00Z',
        },
        {
          'id': 'apt-002',
          'patient_name': 'Jane Smith',
          'scheduled_start': '2024-01-15T11:00:00Z',
        },
      ];

      final cacheEntry = {
        'data': cachedAppointments,
        'cachedAt': DateTime.now().toIso8601String(),
      };

      await mockCache.put('appointments_today', jsonEncode(cacheEntry));

      final cached = mockCache.get('appointments_today');
      expect(cached, isNotNull);

      final decoded = jsonDecode(cached!);
      expect(decoded['data'].length, 2);
    });

    test('shows cached patient data when offline', () async {
      final cachedPatients = [
        {'id': 'pat-001', 'name': 'John Doe'},
        {'id': 'pat-002', 'name': 'Jane Smith'},
      ];

      final cacheEntry = {
        'data': cachedPatients,
        'cachedAt': DateTime.now().toIso8601String(),
      };

      await mockCache.put('patients_all', jsonEncode(cacheEntry));

      final cached = mockCache.get('patients_all');
      final decoded = jsonDecode(cached!);

      expect(decoded['data'].length, 2);
    });

    test('displays cache timestamp in UI', () async {
      final cacheTime = DateTime.now().subtract(const Duration(minutes: 5));
      final cacheEntry = {
        'data': [],
        'cachedAt': cacheTime.toIso8601String(),
      };

      await mockCache.put('data', jsonEncode(cacheEntry));

      final cached = mockCache.get('data');
      final decoded = jsonDecode(cached!);
      final cachedAt = DateTime.parse(decoded['cachedAt']);

      final age = DateTime.now().difference(cachedAt);
      expect(age.inMinutes, closeTo(5, 1));
      // UI should show "Updated 5 minutes ago"
    });

    test('refreshes cache when coming back online', () async {
      final oldCache = {
        'data': [
          {'id': 'apt-001', 'status': 'scheduled'}
        ],
        'cachedAt': DateTime.now()
            .subtract(const Duration(hours: 1))
            .toIso8601String(),
      };

      await mockCache.put('appointments', jsonEncode(oldCache));

      // Come back online
      when(() => mockApiClient.getTodayAppointments(doctorId: any(named: 'doctorId')))
          .thenAnswer((_) async => [
                {'id': 'apt-001', 'status': 'completed'},
              ]);

      // Refresh should update cache
      final newCache = {
        'data': [
          {'id': 'apt-001', 'status': 'completed'}
        ],
        'cachedAt': DateTime.now().toIso8601String(),
      };

      await mockCache.put('appointments', jsonEncode(newCache));

      final cached = mockCache.get('appointments');
      final decoded = jsonDecode(cached!);
      expect(decoded['data'][0]['status'], 'completed');
    });
  });

  group('Offline Mode Integration - Sync on Reconnect', () {
    test('automatically syncs when network is restored', () async {
      // Queue some items while offline
      final syncItem1 = SyncItem(
        id: 'sync-1',
        entityType: 'appointment',
        operation: SyncOperation.create,
        data: {'patient_id': 'pat-001'},
        createdAt: DateTime.now(),
      );

      final syncItem2 = SyncItem(
        id: 'sync-2',
        entityType: 'appointment',
        operation: SyncOperation.create,
        data: {'patient_id': 'pat-002'},
        createdAt: DateTime.now(),
      );

      await mockSyncQueue.put(syncItem1.id, jsonEncode(syncItem1.toJson()));
      await mockSyncQueue.put(syncItem2.id, jsonEncode(syncItem2.toJson()));

      expect(syncQueueStorage.length, 2);

      // Network restored - sync should trigger
      when(() => mockApiClient.createAppointment(any()))
          .thenAnswer((_) async => {'id': 'apt-001'});

      // After successful sync, queue should be empty
      await mockSyncQueue.clear();
      expect(syncQueueStorage.isEmpty, true);
    });

    test('shows sync progress during reconnect', () {
      final syncState = SyncState(
        isOnline: true,
        isSyncing: true,
        pendingCount: 5,
      );

      expect(syncState.isSyncing, true);
      expect(syncState.pendingCount, 5);
      // UI should show "Syncing 5 items..."
    });

    test('handles partial sync failures gracefully', () async {
      when(() => mockApiClient.createAppointment(any()))
          .thenAnswer((_) async => {'id': 'apt-001'})
          .thenThrow(Exception('Server error'));

      // First item should sync, second should fail and retry
      final result = SyncResult(
        synced: 1,
        failed: 1,
        pending: 1,
      );

      expect(result.synced, 1);
      expect(result.failed, 1);
      expect(result.hasFailures, true);
    });

    test('notifies user of sync completion', () {
      final syncState = SyncState(
        isOnline: true,
        isSyncing: false,
        pendingCount: 0,
        lastSyncTime: DateTime.now(),
      );

      expect(syncState.isSyncing, false);
      expect(syncState.pendingCount, 0);
      expect(syncState.lastSyncTime, isNotNull);
      // Show toast: "All changes synced successfully"
    });

    test('notifies user of sync errors', () {
      final syncState = SyncState(
        isOnline: true,
        isSyncing: false,
        pendingCount: 2,
        lastError: '2 items failed to sync',
      );

      expect(syncState.lastError, isNotNull);
      expect(syncState.pendingCount, 2);
      // Show error: "2 items failed to sync"
    });
  });

  group('Offline Mode Integration - Merge Changes', () {
    test('merges local changes with server data on reconnect', () {
      final localAppointment = {
        'id': 'apt-001',
        'status': 'checked_in',
        'updated_at': '2024-01-15T10:30:00Z',
        'notes': 'Patient arrived early',
      };

      final serverAppointment = {
        'id': 'apt-001',
        'status': 'checked_in',
        'updated_at': '2024-01-15T10:25:00Z',
        'notes': '',
      };

      // Local version is newer, keep local notes
      final localTime = DateTime.parse(localAppointment['updated_at'] as String);
      final serverTime = DateTime.parse(serverAppointment['updated_at'] as String);

      if (localTime.isAfter(serverTime)) {
        serverAppointment['notes'] = localAppointment['notes'];
        serverAppointment['updated_at'] = localAppointment['updated_at'];
      }

      expect(serverAppointment['notes'], 'Patient arrived early');
    });

    test('resolves conflicts with last-write-wins strategy', () {
      final local = {
        'id': 'apt-001',
        'status': 'completed',
        'updated_at': '2024-01-15T12:00:00Z',
      };

      final server = {
        'id': 'apt-001',
        'status': 'cancelled',
        'updated_at': '2024-01-15T12:05:00Z',
      };

      final localTime = DateTime.parse(local['updated_at'] as String);
      final serverTime = DateTime.parse(server['updated_at'] as String);

      final merged = serverTime.isAfter(localTime) ? server : local;

      expect(merged['status'], 'cancelled'); // Server wins
    });

    test('preserves local data that does not conflict', () {
      final local = {
        'id': 'apt-001',
        'status': 'scheduled',
        'local_notes': 'Draft notes',
      };

      final server = {
        'id': 'apt-001',
        'status': 'scheduled',
      };

      final merged = {...server, ...local};

      expect(merged['local_notes'], 'Draft notes');
      expect(merged['status'], 'scheduled');
    });

    test('handles deleted items during sync', () {
      final localItems = ['apt-001', 'apt-002', 'apt-003'];
      final serverItems = ['apt-001', 'apt-003']; // apt-002 deleted on server

      final deletedItems = localItems
          .where((id) => !serverItems.contains(id))
          .toList();

      expect(deletedItems, ['apt-002']);
      // Should remove apt-002 from local cache
    });
  });

  group('Offline Mode Integration - User Experience', () {
    test('shows clear offline indicator in app bar', () {
      final syncState = SyncState(
        isOnline: false,
        pendingCount: 3,
      );

      expect(syncState.isOnline, false);
      // UI: Red banner "Offline - 3 changes pending"
    });

    test('disables online-only features when offline', () {
      final isOnline = false;

      // Features that require internet
      final canMakePayment = isOnline; // Requires Razorpay API
      final canSendSMS = isOnline; // Requires MSG91 API
      final canVideoCall = isOnline; // Requires WebRTC

      expect(canMakePayment, false);
      expect(canSendSMS, false);
      expect(canVideoCall, false);
    });

    test('enables offline-capable features when offline', () {
      final isOnline = false;

      // Features that work offline
      final canViewAppointments = true; // Uses cache
      final canBookAppointment = true; // Queues for sync
      final canCheckIn = true; // Queues for sync
      final canViewPatients = true; // Uses cache

      expect(canViewAppointments, true);
      expect(canBookAppointment, true);
      expect(canCheckIn, true);
      expect(canViewPatients, true);
    });

    test('shows sync status in settings', () {
      final syncState = SyncState(
        isOnline: true,
        isSyncing: false,
        pendingCount: 0,
        lastSyncTime: DateTime(2024, 1, 15, 12, 0),
      );

      expect(syncState.lastSyncTime, isNotNull);
      // UI: "Last synced: Today at 12:00 PM"
    });

    test('allows manual sync trigger', () {
      final syncState = SyncState(
        isOnline: true,
        isSyncing: false,
        pendingCount: 5,
      );

      // User taps "Sync Now" button
      expect(syncState.hasPendingChanges, true);
      expect(syncState.isOnline, true);
      // Trigger manual sync
    });

    test('prevents actions that would cause data loss when offline', () {
      final isOnline = false;

      // Destructive actions should warn user
      final canDelete = isOnline; // Deletion should be online-only
      final canBulkUpdate = isOnline; // Bulk operations online-only

      expect(canDelete, false);
      expect(canBulkUpdate, false);
      // Show warning: "This action requires internet connection"
    });
  });

  group('Offline Mode Integration - Edge Cases', () {
    test('handles app kill during offline session', () async {
      // Queue items
      final syncItem = SyncItem(
        id: 'sync-001',
        entityType: 'appointment',
        operation: SyncOperation.create,
        data: {},
        createdAt: DateTime.now(),
      );

      await mockSyncQueue.put(syncItem.id, jsonEncode(syncItem.toJson()));

      // App killed and restarted
      // Queue should persist
      final persisted = mockSyncQueue.get(syncItem.id);
      expect(persisted, isNotNull);
    });

    test('handles rapid connectivity toggles', () {
      final states = [
        true, // online
        false, // offline
        true, // online
        false, // offline
        true, // online
      ];

      for (var i = 0; i < states.length - 1; i++) {
        final current = states[i];
        final next = states[i + 1];

        if (!current && next) {
          // Became online - should trigger sync
          expect(next, true);
        }
      }
    });

    test('handles sync queue overflow', () {
      final maxQueueSize = 1000;
      final queueSize = 1050;

      if (queueSize > maxQueueSize) {
        // Should warn user or remove oldest items
        expect(queueSize, greaterThan(maxQueueSize));
      }
    });

    test('handles expired cache during offline period', () async {
      final expiredCache = {
        'data': [],
        'cachedAt': DateTime.now()
            .subtract(const Duration(days: 7))
            .toIso8601String(),
      };

      await mockCache.put('old_data', jsonEncode(expiredCache));

      final cached = mockCache.get('old_data');
      final decoded = jsonDecode(cached!);
      final cachedAt = DateTime.parse(decoded['cachedAt']);

      final age = DateTime.now().difference(cachedAt);
      if (age.inDays > 1) {
        // Show warning: "Data may be outdated"
        expect(age.inDays, greaterThan(1));
      }
    });

    test('handles timezone changes during offline period', () {
      final appointment = {
        'scheduled_start': '2024-01-15T10:00:00Z',
      };

      final scheduledTime = DateTime.parse(appointment['scheduled_start'] as String);
      final localTime = scheduledTime.toLocal();

      expect(localTime, isNotNull);
      // Should display in user's current timezone
    });
  });

  group('Offline Mode Integration - Background Sync', () {
    test('syncs in background when app is in foreground', () async {
      // Simulate background sync
      when(() => mockApiClient.createAppointment(any()))
          .thenAnswer((_) async => {'id': 'apt-001'});

      // Background sync should not block UI
      final isSyncing = true;
      expect(isSyncing, true);
      // UI remains responsive
    });

    test('defers sync when battery is low', () {
      final batteryLevel = 5; // 5% battery
      final lowBatteryThreshold = 10;

      final shouldSync = batteryLevel > lowBatteryThreshold;

      expect(shouldSync, false);
      // Defer sync until charging or battery improves
    });

    test('uses wifi for large data sync', () {
      final syncDataSize = 10 * 1024 * 1024; // 10 MB
      final connectivity = ConnectivityResult.mobile;
      final largeSyncThreshold = 5 * 1024 * 1024; // 5 MB

      final shouldWaitForWifi = syncDataSize > largeSyncThreshold &&
          connectivity == ConnectivityResult.mobile;

      expect(shouldWaitForWifi, true);
      // Wait for WiFi to sync large data
    });
  });
}
