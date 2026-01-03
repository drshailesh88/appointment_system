import '../api/api_client.dart';
import '../models/doctor.dart';
import '../services/offline_sync_service.dart';

/// Repository for doctor operations with offline support
class DoctorRepository {
  final ApiClient _apiClient;
  final OfflineSyncService _syncService;

  static const String _cacheKeyDoctors = 'doctors_list';
  static const Duration _cacheMaxAge = Duration(hours: 1);

  DoctorRepository(this._apiClient, this._syncService);

  /// Get all doctors with caching
  Future<List<Doctor>> getDoctors({
    String? clinicId,
    String? specialization,
  }) async {
    final cacheKey = '${_cacheKeyDoctors}_${clinicId ?? ''}_${specialization ?? ''}';

    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<List<dynamic>>(
        cacheKey,
        _cacheMaxAge,
      );
      if (cached != null) {
        return cached
            .map((json) => Doctor.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
    }

    try {
      final data = await _apiClient.getDoctors(
        clinicId: clinicId,
        specialization: specialization,
      );
      final doctors = data.map((json) => Doctor.fromJson(json)).toList();

      await _syncService.cacheData(cacheKey, data);

      return doctors;
    } catch (e) {
      final cached = _syncService.getCachedData<List<dynamic>>(cacheKey);
      if (cached != null) {
        return cached
            .map((json) => Doctor.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
      rethrow;
    }
  }

  /// Get doctor by ID
  Future<Doctor> getDoctor(String doctorId) async {
    final cacheKey = 'doctor_$doctorId';

    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<Map<String, dynamic>>(
        cacheKey,
        _cacheMaxAge,
      );
      if (cached != null) {
        return Doctor.fromJson(cached);
      }
    }

    try {
      final data = await _apiClient.getDoctor(doctorId);
      final doctor = Doctor.fromJson(data);

      await _syncService.cacheData(cacheKey, data);

      return doctor;
    } catch (e) {
      final cached = _syncService.getCachedData<Map<String, dynamic>>(cacheKey);
      if (cached != null) {
        return Doctor.fromJson(cached);
      }
      rethrow;
    }
  }

  /// Get doctor schedule
  Future<Map<String, dynamic>> getDoctorSchedule(
    String doctorId, {
    String? date,
  }) async {
    final cacheKey = 'doctor_schedule_${doctorId}_$date';

    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<Map<String, dynamic>>(
        cacheKey,
        const Duration(minutes: 5),
      );
      if (cached != null) {
        return cached;
      }
    }

    try {
      final data = await _apiClient.getDoctorSchedule(doctorId, date: date);
      await _syncService.cacheData(cacheKey, data);
      return data;
    } catch (e) {
      final cached = _syncService.getCachedData<Map<String, dynamic>>(cacheKey);
      if (cached != null) {
        return cached;
      }
      rethrow;
    }
  }

  /// Get available slots
  Future<Map<String, dynamic>> getAvailableSlots({
    required String doctorId,
    required String date,
    int durationMinutes = 15,
  }) async {
    final cacheKey = 'slots_${doctorId}_${date}_$durationMinutes';

    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<Map<String, dynamic>>(
        cacheKey,
        const Duration(minutes: 2),
      );
      if (cached != null) {
        return cached;
      }
      throw Exception('Slot availability not available offline');
    }

    try {
      final data = await _apiClient.getAvailableSlots(
        doctorId: doctorId,
        date: date,
        durationMinutes: durationMinutes,
      );
      await _syncService.cacheData(cacheKey, data);
      return data;
    } catch (e) {
      final cached = _syncService.getCachedData<Map<String, dynamic>>(cacheKey);
      if (cached != null) {
        return cached;
      }
      rethrow;
    }
  }
}
