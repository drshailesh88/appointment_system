import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../lib/core/providers/sync_provider.dart';
import '../../lib/core/services/offline_sync_service.dart';
import '../helpers/mock_providers.dart';

void main() {
  late MockOfflineSyncService mockSyncService;

  setUp(() {
    mockSyncService = MockOfflineSyncService();
  });

  group('SyncProvider', () {
    test('initial state should be online with no pending items', () async {
      when(() => mockSyncService.isOnline()).thenAnswer((_) async => true);
      when(() => mockSyncService.getPendingItems()).thenReturn([]);

      final container = ProviderContainer(
        overrides: [
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      // Wait for initialization
      await Future.delayed(const Duration(milliseconds: 100));

      final state = container.read(syncProvider);

      expect(state.isOnline, true);
      expect(state.isSyncing, false);
      expect(state.pendingCount, 0);
      expect(state.lastError, null);

      container.dispose();
    });

    test('syncNow should sync pending items', () async {
      final syncResult = SyncResult(
        synced: 5,
        failed: 0,
        pending: 0,
      );

      when(() => mockSyncService.isOnline()).thenAnswer((_) async => true);
      when(() => mockSyncService.getPendingItems()).thenReturn([]);
      when(() => mockSyncService.syncPendingItems())
          .thenAnswer((_) async => syncResult);

      final container = ProviderContainer(
        overrides: [
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      // Wait for initialization
      await Future.delayed(const Duration(milliseconds: 100));

      final notifier = container.read(syncProvider.notifier);

      await notifier.syncNow();

      final state = container.read(syncProvider);

      expect(state.isSyncing, false);
      expect(state.pendingCount, 0);
      expect(state.lastError, null);
      expect(state.lastSyncTime, isNotNull);

      verify(() => mockSyncService.syncPendingItems()).called(1);

      container.dispose();
    });

    test('syncNow should handle failures', () async {
      final syncResult = SyncResult(
        synced: 3,
        failed: 2,
        pending: 2,
      );

      when(() => mockSyncService.isOnline()).thenAnswer((_) async => true);
      when(() => mockSyncService.getPendingItems()).thenReturn([]);
      when(() => mockSyncService.syncPendingItems())
          .thenAnswer((_) async => syncResult);

      final container = ProviderContainer(
        overrides: [
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      // Wait for initialization
      await Future.delayed(const Duration(milliseconds: 100));

      final notifier = container.read(syncProvider.notifier);

      await notifier.syncNow();

      final state = container.read(syncProvider);

      expect(state.pendingCount, 2);
      expect(state.lastError, contains('failed to sync'));

      container.dispose();
    });

    test('syncNow should not sync when offline', () async {
      when(() => mockSyncService.isOnline()).thenAnswer((_) async => false);
      when(() => mockSyncService.getPendingItems()).thenReturn([]);

      final container = ProviderContainer(
        overrides: [
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      // Wait for initialization
      await Future.delayed(const Duration(milliseconds: 100));

      final notifier = container.read(syncProvider.notifier);

      await notifier.syncNow();

      final state = container.read(syncProvider);

      expect(state.isOnline, false);
      expect(state.isSyncing, false);

      verifyNever(() => mockSyncService.syncPendingItems());

      container.dispose();
    });

    test('updatePendingCount should update pending count', () async {
      when(() => mockSyncService.isOnline()).thenAnswer((_) async => true);
      when(() => mockSyncService.getPendingItems())
          .thenReturn(List.filled(5, null));

      final container = ProviderContainer(
        overrides: [
          offlineSyncServiceProvider.overrideWithValue(mockSyncService),
        ],
      );

      // Wait for initialization
      await Future.delayed(const Duration(milliseconds: 100));

      final notifier = container.read(syncProvider.notifier);

      notifier.updatePendingCount();

      final state = container.read(syncProvider);

      expect(state.pendingCount, 5);
      expect(state.hasPendingChanges, true);

      container.dispose();
    });
  });
}
