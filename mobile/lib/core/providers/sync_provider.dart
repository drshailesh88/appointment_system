import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../repositories/appointment_repository.dart';
import '../repositories/doctor_repository.dart';
import '../repositories/patient_repository.dart';
import '../services/offline_sync_service.dart';
import 'auth_provider.dart';

/// Sync state
class SyncState {
  final bool isOnline;
  final bool isSyncing;
  final int pendingCount;
  final String? lastError;
  final DateTime? lastSyncTime;

  const SyncState({
    this.isOnline = true,
    this.isSyncing = false,
    this.pendingCount = 0,
    this.lastError,
    this.lastSyncTime,
  });

  SyncState copyWith({
    bool? isOnline,
    bool? isSyncing,
    int? pendingCount,
    String? lastError,
    DateTime? lastSyncTime,
  }) {
    return SyncState(
      isOnline: isOnline ?? this.isOnline,
      isSyncing: isSyncing ?? this.isSyncing,
      pendingCount: pendingCount ?? this.pendingCount,
      lastError: lastError,
      lastSyncTime: lastSyncTime ?? this.lastSyncTime,
    );
  }

  bool get hasPendingChanges => pendingCount > 0;
}

/// Sync notifier
class SyncNotifier extends StateNotifier<SyncState> {
  final OfflineSyncService _syncService;

  SyncNotifier(this._syncService) : super(const SyncState()) {
    _init();
  }

  Future<void> _init() async {
    // Check initial connectivity
    final isOnline = await _syncService.isOnline();
    state = state.copyWith(
      isOnline: isOnline,
      pendingCount: _syncService.getPendingItems().length,
    );

    // Listen for connectivity changes
    Connectivity().onConnectivityChanged.listen((result) {
      final online = result != ConnectivityResult.none;
      state = state.copyWith(isOnline: online);

      if (online) {
        syncNow();
      }
    });
  }

  Future<void> syncNow() async {
    if (state.isSyncing || !state.isOnline) return;

    state = state.copyWith(isSyncing: true, lastError: null);

    try {
      final result = await _syncService.syncPendingItems();

      state = state.copyWith(
        isSyncing: false,
        pendingCount: result.pending,
        lastSyncTime: DateTime.now(),
        lastError: result.hasFailures ? '${result.failed} items failed to sync' : null,
      );
    } catch (e) {
      state = state.copyWith(
        isSyncing: false,
        lastError: e.toString(),
      );
    }
  }

  void updatePendingCount() {
    state = state.copyWith(
      pendingCount: _syncService.getPendingItems().length,
    );
  }
}

/// Offline sync service provider
final offlineSyncServiceProvider = Provider<OfflineSyncService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OfflineSyncService(apiClient);
});

/// Sync state provider
final syncProvider = StateNotifierProvider<SyncNotifier, SyncState>((ref) {
  final syncService = ref.watch(offlineSyncServiceProvider);
  return SyncNotifier(syncService);
});

/// Repository providers

final appointmentRepositoryProvider = Provider<AppointmentRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final syncService = ref.watch(offlineSyncServiceProvider);
  return AppointmentRepository(apiClient, syncService);
});

final patientRepositoryProvider = Provider<PatientRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final syncService = ref.watch(offlineSyncServiceProvider);
  return PatientRepository(apiClient, syncService);
});

final doctorRepositoryProvider = Provider<DoctorRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final syncService = ref.watch(offlineSyncServiceProvider);
  return DoctorRepository(apiClient, syncService);
});
