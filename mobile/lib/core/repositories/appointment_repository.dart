import '../api/api_client.dart';
import '../models/appointment.dart';
import '../services/offline_sync_service.dart';

/// Repository for appointment operations with offline support
class AppointmentRepository {
  final ApiClient _apiClient;
  final OfflineSyncService _syncService;

  static const String _cacheKeyToday = 'appointments_today';
  static const Duration _cacheMaxAge = Duration(minutes: 5);

  AppointmentRepository(this._apiClient, this._syncService);

  /// Get today's appointments with caching
  Future<List<Appointment>> getTodayAppointments({String? doctorId}) async {
    // Try to get from cache first if offline
    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<List<dynamic>>(
        _cacheKeyToday,
        _cacheMaxAge,
      );
      if (cached != null) {
        return cached
            .map((json) => Appointment.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
    }

    try {
      final data = await _apiClient.getTodayAppointments(doctorId: doctorId);
      final appointments = data.map((json) => Appointment.fromJson(json)).toList();

      // Cache the results
      await _syncService.cacheData(_cacheKeyToday, data);

      return appointments;
    } catch (e) {
      // On error, try to return cached data even if stale
      final cached = _syncService.getCachedData<List<dynamic>>(_cacheKeyToday);
      if (cached != null) {
        return cached
            .map((json) => Appointment.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
      rethrow;
    }
  }

  /// Get appointments with filters
  Future<List<Appointment>> getAppointments({
    String? doctorId,
    String? patientId,
    String? dateFrom,
    String? dateTo,
    String? status,
  }) async {
    final cacheKey = 'appointments_${doctorId ?? ''}_${dateFrom ?? ''}_${dateTo ?? ''}';

    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<List<dynamic>>(
        cacheKey,
        _cacheMaxAge,
      );
      if (cached != null) {
        return cached
            .map((json) => Appointment.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
    }

    try {
      final data = await _apiClient.getAppointments(
        doctorId: doctorId,
        patientId: patientId,
        dateFrom: dateFrom,
        dateTo: dateTo,
        status: status,
      );
      final appointments = data.map((json) => Appointment.fromJson(json)).toList();

      await _syncService.cacheData(cacheKey, data);

      return appointments;
    } catch (e) {
      final cached = _syncService.getCachedData<List<dynamic>>(cacheKey);
      if (cached != null) {
        return cached
            .map((json) => Appointment.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
      rethrow;
    }
  }

  /// Create appointment with offline support
  Future<Appointment?> createAppointment(Map<String, dynamic> data) async {
    if (!await _syncService.isOnline()) {
      // Queue for sync when online
      final syncItem = SyncItem(
        id: 'appointment_${DateTime.now().millisecondsSinceEpoch}',
        entityType: 'appointment',
        operation: SyncOperation.create,
        data: data,
        createdAt: DateTime.now(),
      );
      await _syncService.queueSync(syncItem);

      // Return a temporary appointment for UI
      return Appointment(
        id: syncItem.id,
        patientId: data['patient_id'] ?? '',
        doctorId: data['doctor_id'] ?? '',
        startTime: DateTime.parse(data['start_time']),
        endTime: DateTime.parse(data['end_time']),
        status: 'pending_sync',
        appointmentType: data['appointment_type'] ?? 'new_consultation',
        chiefComplaint: data['chief_complaint'],
      );
    }

    try {
      final result = await _apiClient.createAppointment(data);
      return Appointment.fromJson(result);
    } catch (e) {
      // If online but request fails, queue for retry
      final syncItem = SyncItem(
        id: 'appointment_${DateTime.now().millisecondsSinceEpoch}',
        entityType: 'appointment',
        operation: SyncOperation.create,
        data: data,
        createdAt: DateTime.now(),
      );
      await _syncService.queueSync(syncItem);
      rethrow;
    }
  }

  /// Check in patient
  Future<bool> checkInPatient(String appointmentId, {int? tokenNumber}) async {
    if (!await _syncService.isOnline()) {
      final syncItem = SyncItem(
        id: 'checkin_${appointmentId}_${DateTime.now().millisecondsSinceEpoch}',
        entityType: 'appointment',
        operation: SyncOperation.update,
        data: {
          'appointment_id': appointmentId,
          'action': 'check_in',
          'token_number': tokenNumber,
        },
        createdAt: DateTime.now(),
      );
      await _syncService.queueSync(syncItem);
      return true; // Optimistic update
    }

    await _apiClient.checkInPatient(appointmentId, tokenNumber: tokenNumber);
    return true;
  }

  /// Get pending sync items count
  int getPendingSyncCount() {
    return _syncService.getPendingItems().length;
  }

  /// Sync pending items
  Future<SyncResult> syncPending() async {
    return await _syncService.syncPendingItems();
  }
}
