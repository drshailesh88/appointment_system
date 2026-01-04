import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';

/// Sync operation types
enum SyncOperation {
  create,
  update,
  delete,
}

/// Sync status for tracking
enum SyncStatus {
  pending,
  syncing,
  completed,
  failed,
}

/// A queued sync item waiting to be synced
class SyncQueueItem {
  final String id;
  final String entityType; // 'appointment', 'patient', 'waitlist'
  final String entityId;
  final SyncOperation operation;
  final Map<String, dynamic> data;
  final DateTime createdAt;
  final int retryCount;
  final String? errorMessage;
  SyncStatus status;

  SyncQueueItem({
    required this.id,
    required this.entityType,
    required this.entityId,
    required this.operation,
    required this.data,
    required this.createdAt,
    this.retryCount = 0,
    this.errorMessage,
    this.status = SyncStatus.pending,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'entityType': entityType,
        'entityId': entityId,
        'operation': operation.name,
        'data': data,
        'createdAt': createdAt.toIso8601String(),
        'retryCount': retryCount,
        'errorMessage': errorMessage,
        'status': status.name,
      };

  factory SyncQueueItem.fromJson(Map<String, dynamic> json) {
    return SyncQueueItem(
      id: json['id'],
      entityType: json['entityType'],
      entityId: json['entityId'],
      operation: SyncOperation.values.byName(json['operation']),
      data: Map<String, dynamic>.from(json['data']),
      createdAt: DateTime.parse(json['createdAt']),
      retryCount: json['retryCount'] ?? 0,
      errorMessage: json['errorMessage'],
      status: SyncStatus.values.byName(json['status'] ?? 'pending'),
    );
  }

  SyncQueueItem copyWith({
    int? retryCount,
    String? errorMessage,
    SyncStatus? status,
  }) {
    return SyncQueueItem(
      id: id,
      entityType: entityType,
      entityId: entityId,
      operation: operation,
      data: data,
      createdAt: createdAt,
      retryCount: retryCount ?? this.retryCount,
      errorMessage: errorMessage ?? this.errorMessage,
      status: status ?? this.status,
    );
  }
}

/// Sync state for UI updates
class SyncState {
  final bool isSyncing;
  final int pendingCount;
  final int failedCount;
  final DateTime? lastSyncTime;
  final String? lastError;
  final List<SyncQueueItem> queue;

  const SyncState({
    this.isSyncing = false,
    this.pendingCount = 0,
    this.failedCount = 0,
    this.lastSyncTime,
    this.lastError,
    this.queue = const [],
  });

  SyncState copyWith({
    bool? isSyncing,
    int? pendingCount,
    int? failedCount,
    DateTime? lastSyncTime,
    String? lastError,
    List<SyncQueueItem>? queue,
  }) {
    return SyncState(
      isSyncing: isSyncing ?? this.isSyncing,
      pendingCount: pendingCount ?? this.pendingCount,
      failedCount: failedCount ?? this.failedCount,
      lastSyncTime: lastSyncTime ?? this.lastSyncTime,
      lastError: lastError,
      queue: queue ?? this.queue,
    );
  }

  bool get hasPendingItems => pendingCount > 0;
  bool get hasFailedItems => failedCount > 0;
}

/// Background sync service for offline-first operations
class BackgroundSyncService {
  static const String _queueKey = 'sync_queue';
  static const String _lastSyncKey = 'last_sync_time';
  static const int _maxRetries = 3;
  static const Duration _retryDelay = Duration(seconds: 5);
  static const Duration _syncInterval = Duration(minutes: 5);

  final ApiClient _apiClient;
  SharedPreferences? _prefs;
  Timer? _syncTimer;
  bool _isSyncing = false;

  final _stateController = StreamController<SyncState>.broadcast();
  Stream<SyncState> get stateStream => _stateController.stream;

  SyncState _state = const SyncState();
  SyncState get state => _state;

  BackgroundSyncService(this._apiClient);

  /// Initialize the sync service
  Future<void> initialize() async {
    _prefs = await SharedPreferences.getInstance();
    await _loadQueue();
    _startPeriodicSync();
    debugPrint('[BackgroundSync] Initialized with ${_state.pendingCount} pending items');
  }

  /// Start periodic sync timer
  void _startPeriodicSync() {
    _syncTimer?.cancel();
    _syncTimer = Timer.periodic(_syncInterval, (_) => syncNow());
  }

  /// Stop the sync service
  void dispose() {
    _syncTimer?.cancel();
    _stateController.close();
  }

  /// Load queue from persistent storage
  Future<void> _loadQueue() async {
    final queueJson = _prefs?.getString(_queueKey);
    if (queueJson != null) {
      try {
        final List<dynamic> items = jsonDecode(queueJson);
        final queue = items.map((e) => SyncQueueItem.fromJson(e)).toList();
        _updateState(queue: queue);
      } catch (e) {
        debugPrint('[BackgroundSync] Error loading queue: $e');
      }
    }

    final lastSyncStr = _prefs?.getString(_lastSyncKey);
    if (lastSyncStr != null) {
      _updateState(lastSyncTime: DateTime.parse(lastSyncStr));
    }
  }

  /// Save queue to persistent storage
  Future<void> _saveQueue() async {
    final queueJson = jsonEncode(_state.queue.map((e) => e.toJson()).toList());
    await _prefs?.setString(_queueKey, queueJson);
  }

  /// Update state and notify listeners
  void _updateState({
    bool? isSyncing,
    DateTime? lastSyncTime,
    String? lastError,
    List<SyncQueueItem>? queue,
  }) {
    final newQueue = queue ?? _state.queue;
    final pendingCount = newQueue.where((e) => e.status == SyncStatus.pending).length;
    final failedCount = newQueue.where((e) => e.status == SyncStatus.failed).length;

    _state = _state.copyWith(
      isSyncing: isSyncing,
      pendingCount: pendingCount,
      failedCount: failedCount,
      lastSyncTime: lastSyncTime,
      lastError: lastError,
      queue: newQueue,
    );

    _stateController.add(_state);
  }

  /// Queue an operation for sync
  Future<void> queueOperation({
    required String entityType,
    required String entityId,
    required SyncOperation operation,
    required Map<String, dynamic> data,
  }) async {
    final item = SyncQueueItem(
      id: '${entityType}_${entityId}_${DateTime.now().millisecondsSinceEpoch}',
      entityType: entityType,
      entityId: entityId,
      operation: operation,
      data: data,
      createdAt: DateTime.now(),
    );

    final newQueue = [..._state.queue, item];
    _updateState(queue: newQueue);
    await _saveQueue();

    debugPrint('[BackgroundSync] Queued ${operation.name} for $entityType:$entityId');

    // Try to sync immediately if online
    syncNow();
  }

  /// Sync all pending items
  Future<void> syncNow() async {
    if (_isSyncing) {
      debugPrint('[BackgroundSync] Sync already in progress');
      return;
    }

    final pendingItems = _state.queue.where((e) =>
        e.status == SyncStatus.pending ||
        (e.status == SyncStatus.failed && e.retryCount < _maxRetries)
    ).toList();

    if (pendingItems.isEmpty) {
      debugPrint('[BackgroundSync] No pending items to sync');
      return;
    }

    _isSyncing = true;
    _updateState(isSyncing: true);
    debugPrint('[BackgroundSync] Starting sync of ${pendingItems.length} items');

    for (final item in pendingItems) {
      await _syncItem(item);
    }

    // Clean up completed items
    final activeQueue = _state.queue.where((e) =>
        e.status != SyncStatus.completed
    ).toList();

    _updateState(
      isSyncing: false,
      lastSyncTime: DateTime.now(),
      queue: activeQueue,
    );
    await _saveQueue();
    await _prefs?.setString(_lastSyncKey, DateTime.now().toIso8601String());

    _isSyncing = false;
    debugPrint('[BackgroundSync] Sync completed');
  }

  /// Sync a single item
  Future<void> _syncItem(SyncQueueItem item) async {
    debugPrint('[BackgroundSync] Syncing ${item.operation.name} ${item.entityType}:${item.entityId}');

    try {
      final endpoint = _getEndpoint(item.entityType, item.entityId, item.operation);

      switch (item.operation) {
        case SyncOperation.create:
          await _apiClient.post(endpoint, item.data);
          break;
        case SyncOperation.update:
          await _apiClient.put(endpoint, item.data);
          break;
        case SyncOperation.delete:
          await _apiClient.delete(endpoint);
          break;
      }

      // Mark as completed
      _updateItemStatus(item.id, SyncStatus.completed);
      debugPrint('[BackgroundSync] Successfully synced ${item.entityType}:${item.entityId}');
    } catch (e) {
      debugPrint('[BackgroundSync] Failed to sync ${item.entityType}:${item.entityId}: $e');

      final newRetryCount = item.retryCount + 1;
      final newStatus = newRetryCount >= _maxRetries
          ? SyncStatus.failed
          : SyncStatus.pending;

      _updateItemStatus(
        item.id,
        newStatus,
        retryCount: newRetryCount,
        errorMessage: e.toString(),
      );

      // Wait before next item if failed
      if (newStatus == SyncStatus.pending) {
        await Future.delayed(_retryDelay);
      }
    }
  }

  /// Get the API endpoint for an entity
  String _getEndpoint(String entityType, String entityId, SyncOperation operation) {
    switch (entityType) {
      case 'appointment':
        return operation == SyncOperation.create
            ? '/appointments'
            : '/appointments/$entityId';
      case 'patient':
        return operation == SyncOperation.create
            ? '/patients'
            : '/patients/$entityId';
      case 'waitlist':
        return operation == SyncOperation.create
            ? '/waitlist'
            : '/waitlist/$entityId';
      default:
        throw Exception('Unknown entity type: $entityType');
    }
  }

  /// Update status of a queue item
  void _updateItemStatus(
    String itemId,
    SyncStatus status, {
    int? retryCount,
    String? errorMessage,
  }) {
    final newQueue = _state.queue.map((item) {
      if (item.id == itemId) {
        return item.copyWith(
          status: status,
          retryCount: retryCount,
          errorMessage: errorMessage,
        );
      }
      return item;
    }).toList();

    _updateState(queue: newQueue);
  }

  /// Retry a failed item
  Future<void> retryItem(String itemId) async {
    _updateItemStatus(itemId, SyncStatus.pending, retryCount: 0);
    await _saveQueue();
    syncNow();
  }

  /// Remove an item from the queue
  Future<void> removeItem(String itemId) async {
    final newQueue = _state.queue.where((e) => e.id != itemId).toList();
    _updateState(queue: newQueue);
    await _saveQueue();
  }

  /// Clear all failed items
  Future<void> clearFailedItems() async {
    final newQueue = _state.queue.where((e) => e.status != SyncStatus.failed).toList();
    _updateState(queue: newQueue);
    await _saveQueue();
  }

  /// Clear all items (use with caution)
  Future<void> clearAll() async {
    _updateState(queue: []);
    await _saveQueue();
  }

  /// Check if we have connectivity (simple check)
  Future<bool> hasConnectivity() async {
    try {
      await _apiClient.get('/health');
      return true;
    } catch (e) {
      return false;
    }
  }
}
