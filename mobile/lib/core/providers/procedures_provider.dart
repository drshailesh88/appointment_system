import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../models/procedure.dart';

/// Procedures provider for managing procedure data
///
/// Phase 9: Procedure & Intervention Tracking
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// Procedures list state
class ProceduresState {
  final List<Procedure> procedures;
  final bool isLoading;
  final String? error;
  final ProcedureStats? stats;
  final List<ProcedureTypeCount> typeCounts;
  final List<ProcedureTemplate> templates;
  final String selectedCategory;

  ProceduresState({
    this.procedures = const [],
    this.isLoading = false,
    this.error,
    this.stats,
    this.typeCounts = const [],
    this.templates = const [],
    this.selectedCategory = 'All',
  });

  ProceduresState copyWith({
    List<Procedure>? procedures,
    bool? isLoading,
    String? error,
    ProcedureStats? stats,
    List<ProcedureTypeCount>? typeCounts,
    List<ProcedureTemplate>? templates,
    String? selectedCategory,
  }) {
    return ProceduresState(
      procedures: procedures ?? this.procedures,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      stats: stats ?? this.stats,
      typeCounts: typeCounts ?? this.typeCounts,
      templates: templates ?? this.templates,
      selectedCategory: selectedCategory ?? this.selectedCategory,
    );
  }
}

/// Procedures notifier for state management
class ProceduresNotifier extends StateNotifier<ProceduresState> {
  final ApiClient _api;
  final String clinicId;

  ProceduresNotifier(this._api, this.clinicId) : super(ProceduresState());

  /// Load procedures with optional filters
  Future<void> loadProcedures({
    String? doctorId,
    String? patientId,
    String? category,
    DateTime? startDate,
    DateTime? endDate,
    int limit = 50,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final params = <String, dynamic>{
        'clinic_id': clinicId,
        'limit': limit,
      };

      if (doctorId != null) params['doctor_id'] = doctorId;
      if (patientId != null) params['patient_id'] = patientId;
      if (category != null && category != 'All') params['category'] = category;
      if (startDate != null) {
        params['start_date'] = DateFormat('yyyy-MM-dd').format(startDate);
      }
      if (endDate != null) {
        params['end_date'] = DateFormat('yyyy-MM-dd').format(endDate);
      }

      final response = await _api.get('/procedures', queryParameters: params);
      final items = response['items'] as List;
      final procedures = items
          .map((json) => Procedure.fromJson(json as Map<String, dynamic>))
          .toList();

      state = state.copyWith(
        procedures: procedures,
        isLoading: false,
        selectedCategory: category ?? 'All',
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load procedures: $e',
      );
    }
  }

  /// Load procedure statistics
  Future<void> loadStats({
    DateTime? startDate,
    DateTime? endDate,
    String? doctorId,
  }) async {
    try {
      final now = DateTime.now();
      final start = startDate ?? DateTime(now.year, now.month, 1);
      final end = endDate ?? now;

      final params = <String, dynamic>{
        'clinic_id': clinicId,
        'start_date': DateFormat('yyyy-MM-dd').format(start),
        'end_date': DateFormat('yyyy-MM-dd').format(end),
      };

      if (doctorId != null) params['doctor_id'] = doctorId;

      final response = await _api.get(
        '/procedures/analytics/stats',
        queryParameters: params,
      );

      state = state.copyWith(
        stats: ProcedureStats.fromJson(response as Map<String, dynamic>),
      );
    } catch (e) {
      // Stats are optional, don't fail the whole view
    }
  }

  /// Load procedure type counts
  Future<void> loadTypeCounts({
    DateTime? startDate,
    DateTime? endDate,
    String? doctorId,
  }) async {
    try {
      final now = DateTime.now();
      final start = startDate ?? DateTime(now.year, now.month, 1);
      final end = endDate ?? now;

      final params = <String, dynamic>{
        'clinic_id': clinicId,
        'start_date': DateFormat('yyyy-MM-dd').format(start),
        'end_date': DateFormat('yyyy-MM-dd').format(end),
      };

      if (doctorId != null) params['doctor_id'] = doctorId;

      final response = await _api.get(
        '/procedures/analytics/types',
        queryParameters: params,
      );

      final counts = (response as List)
          .map((json) => ProcedureTypeCount.fromJson(json as Map<String, dynamic>))
          .toList();

      state = state.copyWith(typeCounts: counts);
    } catch (e) {
      // Type counts are optional
    }
  }

  /// Load procedure templates
  Future<void> loadTemplates() async {
    try {
      final response = await _api.get('/procedures/templates');
      final templates = (response as List)
          .map((json) => ProcedureTemplate.fromJson(json as Map<String, dynamic>))
          .toList();

      state = state.copyWith(templates: templates);
    } catch (e) {
      // Templates are optional
    }
  }

  /// Create a new procedure
  Future<Procedure?> createProcedure({
    required String patientId,
    required String doctorId,
    String? appointmentId,
    required String category,
    required String procedureType,
    String? subType,
    required DateTime procedureDate,
    Map<String, dynamic>? consumables,
    Map<String, dynamic>? customFields,
    String? icdCode,
    String? cptCode,
    String outcome = 'successful',
    String? notes,
    double? billedAmount,
  }) async {
    try {
      final data = {
        'patient_id': patientId,
        'doctor_id': doctorId,
        'clinic_id': clinicId,
        'category': category,
        'procedure_type': procedureType,
        'procedure_date': DateFormat('yyyy-MM-dd').format(procedureDate),
        'outcome': outcome,
      };

      if (appointmentId != null) data['appointment_id'] = appointmentId;
      if (subType != null) data['sub_type'] = subType;
      if (consumables != null) data['consumables'] = consumables;
      if (customFields != null) data['custom_fields'] = customFields;
      if (icdCode != null) data['icd_code'] = icdCode;
      if (cptCode != null) data['cpt_code'] = cptCode;
      if (notes != null) data['notes'] = notes;
      if (billedAmount != null) data['billed_amount'] = billedAmount;

      final response = await _api.post('/procedures', data);
      final procedure = Procedure.fromJson(response as Map<String, dynamic>);

      // Add to local list
      state = state.copyWith(
        procedures: [procedure, ...state.procedures],
      );

      return procedure;
    } catch (e) {
      state = state.copyWith(error: 'Failed to create procedure: $e');
      return null;
    }
  }

  /// Quick log a procedure
  Future<Procedure?> quickLog({
    required String patientId,
    required String doctorId,
    required String category,
    required String procedureType,
    String outcome = 'successful',
    String? notes,
    double? billedAmount,
  }) async {
    try {
      final data = {
        'patient_id': patientId,
        'doctor_id': doctorId,
        'clinic_id': clinicId,
        'category': category,
        'procedure_type': procedureType,
        'outcome': outcome,
      };

      if (notes != null) data['notes'] = notes;
      if (billedAmount != null) data['billed_amount'] = billedAmount;

      final response = await _api.post('/procedures/quick', data);
      final procedure = Procedure.fromJson(response as Map<String, dynamic>);

      // Add to local list
      state = state.copyWith(
        procedures: [procedure, ...state.procedures],
      );

      return procedure;
    } catch (e) {
      state = state.copyWith(error: 'Failed to log procedure: $e');
      return null;
    }
  }

  /// Update a procedure
  Future<bool> updateProcedure(String procedureId, Map<String, dynamic> updates) async {
    try {
      final response = await _api.put('/procedures/$procedureId', updates);
      final updated = Procedure.fromJson(response as Map<String, dynamic>);

      state = state.copyWith(
        procedures: state.procedures.map((p) {
          return p.id == procedureId ? updated : p;
        }).toList(),
      );

      return true;
    } catch (e) {
      state = state.copyWith(error: 'Failed to update procedure: $e');
      return false;
    }
  }

  /// Delete a procedure
  Future<bool> deleteProcedure(String procedureId) async {
    try {
      await _api.delete('/procedures/$procedureId');

      state = state.copyWith(
        procedures: state.procedures.where((p) => p.id != procedureId).toList(),
      );

      return true;
    } catch (e) {
      state = state.copyWith(error: 'Failed to delete procedure: $e');
      return false;
    }
  }

  /// Set selected category filter
  void setCategory(String category) {
    state = state.copyWith(selectedCategory: category);
    loadProcedures(category: category == 'All' ? null : category);
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Provider for procedures state
final proceduresProvider = StateNotifierProvider.family<
    ProceduresNotifier, ProceduresState, String>(
  (ref, clinicId) => ProceduresNotifier(ref.read(apiClientProvider), clinicId),
);
