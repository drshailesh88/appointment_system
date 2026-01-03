import '../api/api_client.dart';
import '../models/patient.dart';
import '../services/offline_sync_service.dart';

/// Repository for patient operations with offline support
class PatientRepository {
  final ApiClient _apiClient;
  final OfflineSyncService _syncService;

  static const Duration _cacheMaxAge = Duration(minutes: 10);

  PatientRepository(this._apiClient, this._syncService);

  /// Search patients with caching
  Future<List<Patient>> searchPatients({
    required String query,
    String? clinicId,
  }) async {
    final cacheKey = 'patients_search_$query';

    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<List<dynamic>>(
        cacheKey,
        _cacheMaxAge,
      );
      if (cached != null) {
        return cached
            .map((json) => Patient.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
      throw Exception('No cached search results available');
    }

    try {
      final data = await _apiClient.searchPatients(
        query: query,
        clinicId: clinicId,
      );
      final patients = data.map((json) => Patient.fromJson(json)).toList();

      await _syncService.cacheData(cacheKey, data);

      return patients;
    } catch (e) {
      final cached = _syncService.getCachedData<List<dynamic>>(cacheKey);
      if (cached != null) {
        return cached
            .map((json) => Patient.fromJson(Map<String, dynamic>.from(json)))
            .toList();
      }
      rethrow;
    }
  }

  /// Get patient by ID
  Future<Patient> getPatient(String patientId) async {
    final cacheKey = 'patient_$patientId';

    if (!await _syncService.isOnline()) {
      final cached = _syncService.getCachedDataIfFresh<Map<String, dynamic>>(
        cacheKey,
        _cacheMaxAge,
      );
      if (cached != null) {
        return Patient.fromJson(cached);
      }
      throw Exception('Patient data not available offline');
    }

    try {
      final data = await _apiClient.getPatient(patientId);
      final patient = Patient.fromJson(data);

      await _syncService.cacheData(cacheKey, data);

      return patient;
    } catch (e) {
      final cached = _syncService.getCachedData<Map<String, dynamic>>(cacheKey);
      if (cached != null) {
        return Patient.fromJson(cached);
      }
      rethrow;
    }
  }

  /// Create patient with offline support
  Future<Patient?> createPatient(Map<String, dynamic> data) async {
    if (!await _syncService.isOnline()) {
      // Queue for sync when online
      final syncItem = SyncItem(
        id: 'patient_${DateTime.now().millisecondsSinceEpoch}',
        entityType: 'patient',
        operation: SyncOperation.create,
        data: data,
        createdAt: DateTime.now(),
      );
      await _syncService.queueSync(syncItem);

      // Return a temporary patient for UI
      return Patient(
        id: syncItem.id,
        name: data['name'] ?? 'Unknown',
        phone: data['phone'],
        email: data['email'],
        gender: data['gender'],
        dateOfBirth: data['date_of_birth'] != null
            ? DateTime.parse(data['date_of_birth'])
            : null,
        clinicId: data['clinic_id'] ?? '',
      );
    }

    try {
      final result = await _apiClient.createPatient(data);
      return Patient.fromJson(result);
    } catch (e) {
      // Queue for retry
      final syncItem = SyncItem(
        id: 'patient_${DateTime.now().millisecondsSinceEpoch}',
        entityType: 'patient',
        operation: SyncOperation.create,
        data: data,
        createdAt: DateTime.now(),
      );
      await _syncService.queueSync(syncItem);
      rethrow;
    }
  }
}
