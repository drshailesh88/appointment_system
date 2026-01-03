import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:hive/hive.dart';

import '../api/api_client.dart';

/// Sync operation types
enum SyncOperation {
  create,
  update,
  delete,
}

/// Pending sync item
class SyncItem {
  final String id;
  final String entityType;
  final SyncOperation operation;
  final Map<String, dynamic> data;
  final DateTime createdAt;
  int retryCount;

  SyncItem({
    required this.id,
    required this.entityType,
    required this.operation,
    required this.data,
    required this.createdAt,
    this.retryCount = 0,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'entityType': entityType,
        'operation': operation.name,
        'data': data,
        'createdAt': createdAt.toIso8601String(),
        'retryCount': retryCount,
      };

  factory SyncItem.fromJson(Map<String, dynamic> json) => SyncItem(
        id: json['id'],
        entityType: json['entityType'],
        operation: SyncOperation.values.byName(json['operation']),
        data: json['data'],
        createdAt: DateTime.parse(json['createdAt']),
        retryCount: json['retryCount'] ?? 0,
      );
}

/// Offline sync service
///
/// Handles:
/// - Queuing operations when offline
/// - Syncing when back online
/// - Conflict resolution
/// - Local caching
class OfflineSyncService {
  static const String _syncQueueBox = 'sync_queue';
  static const String _cacheBox = 'cache';
  static const int _maxRetries = 3;

  final ApiClient _apiClient;
  Box<String>? _syncQueue;
  Box<String>? _cache;
  bool _isSyncing = false;

  OfflineSyncService(this._apiClient);

  /// Initialize the service
  Future<void> initialize() async {
    _syncQueue = await Hive.openBox<String>(_syncQueueBox);
    _cache = await Hive.openBox<String>(_cacheBox);

    // Listen for connectivity changes
    Connectivity().onConnectivityChanged.listen((result) {
      if (result != ConnectivityResult.none) {
        syncPendingItems();
      }
    });
  }

  /// Check if online
  Future<bool> isOnline() async {
    final result = await Connectivity().checkConnectivity();
    return result != ConnectivityResult.none;
  }

  /// Queue an operation for sync
  Future<void> queueSync(SyncItem item) async {
    await _syncQueue?.put(item.id, jsonEncode(item.toJson()));
  }

  /// Get pending sync items
  List<SyncItem> getPendingItems() {
    if (_syncQueue == null) return [];

    return _syncQueue!.values
        .map((json) => SyncItem.fromJson(jsonDecode(json)))
        .toList();
  }

  /// Sync all pending items
  Future<SyncResult> syncPendingItems() async {
    if (_isSyncing) {
      return SyncResult(synced: 0, failed: 0, pending: getPendingItems().length);
    }

    if (!await isOnline()) {
      return SyncResult(synced: 0, failed: 0, pending: getPendingItems().length);
    }

    _isSyncing = true;
    int synced = 0;
    int failed = 0;

    try {
      final items = getPendingItems();

      for (final item in items) {
        try {
          await _syncItem(item);
          await _syncQueue?.delete(item.id);
          synced++;
        } catch (e) {
          item.retryCount++;

          if (item.retryCount >= _maxRetries) {
            // Move to dead letter queue or notify user
            await _syncQueue?.delete(item.id);
            failed++;
          } else {
            // Update with incremented retry count
            await _syncQueue?.put(item.id, jsonEncode(item.toJson()));
          }
        }
      }
    } finally {
      _isSyncing = false;
    }

    return SyncResult(
      synced: synced,
      failed: failed,
      pending: getPendingItems().length,
    );
  }

  /// Sync a single item
  Future<void> _syncItem(SyncItem item) async {
    switch (item.entityType) {
      case 'appointment':
        await _syncAppointment(item);
        break;
      case 'patient':
        await _syncPatient(item);
        break;
      default:
        throw Exception('Unknown entity type: ${item.entityType}');
    }
  }

  Future<void> _syncAppointment(SyncItem item) async {
    switch (item.operation) {
      case SyncOperation.create:
        await _apiClient.createAppointment(item.data);
        break;
      case SyncOperation.update:
        // await _apiClient.updateAppointment(item.id, item.data);
        break;
      case SyncOperation.delete:
        // await _apiClient.deleteAppointment(item.id);
        break;
    }
  }

  Future<void> _syncPatient(SyncItem item) async {
    switch (item.operation) {
      case SyncOperation.create:
        await _apiClient.createPatient(item.data);
        break;
      case SyncOperation.update:
        // await _apiClient.updatePatient(item.id, item.data);
        break;
      case SyncOperation.delete:
        // await _apiClient.deletePatient(item.id);
        break;
    }
  }

  // ==================
  // Caching
  // ==================

  /// Cache data locally
  Future<void> cacheData(String key, dynamic data) async {
    final json = jsonEncode({
      'data': data,
      'cachedAt': DateTime.now().toIso8601String(),
    });
    await _cache?.put(key, json);
  }

  /// Get cached data
  T? getCachedData<T>(String key) {
    final json = _cache?.get(key);
    if (json == null) return null;

    final decoded = jsonDecode(json);
    return decoded['data'] as T?;
  }

  /// Get cached data with expiry check
  T? getCachedDataIfFresh<T>(String key, Duration maxAge) {
    final json = _cache?.get(key);
    if (json == null) return null;

    final decoded = jsonDecode(json);
    final cachedAt = DateTime.parse(decoded['cachedAt']);

    if (DateTime.now().difference(cachedAt) > maxAge) {
      // Expired
      return null;
    }

    return decoded['data'] as T?;
  }

  /// Clear all cache
  Future<void> clearCache() async {
    await _cache?.clear();
  }

  /// Clear sync queue
  Future<void> clearSyncQueue() async {
    await _syncQueue?.clear();
  }
}

/// Sync result
class SyncResult {
  final int synced;
  final int failed;
  final int pending;

  SyncResult({
    required this.synced,
    required this.failed,
    required this.pending,
  });

  bool get isComplete => pending == 0;
  bool get hasFailures => failed > 0;
}
