import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/insurance.dart';
import '../services/insurance_service.dart';

// ==================
// Services
// ==================

final insuranceServiceProvider = Provider<InsuranceService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return InsuranceService(apiClient);
});

// ==================
// State
// ==================

/// Insurance state for a specific patient
class InsuranceState {
  final List<InsuranceListItem> insurances;
  final bool isLoading;
  final String? error;

  const InsuranceState({
    this.insurances = const [],
    this.isLoading = false,
    this.error,
  });

  InsuranceState copyWith({
    List<InsuranceListItem>? insurances,
    bool? isLoading,
    String? error,
  }) {
    return InsuranceState(
      insurances: insurances ?? this.insurances,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Insurance state notifier
class InsuranceNotifier extends StateNotifier<InsuranceState> {
  final InsuranceService _service;
  String? _currentPatientId;

  InsuranceNotifier(this._service) : super(const InsuranceState());

  /// Load insurance policies for a patient
  Future<void> loadPatientInsurance(
    String patientId, {
    bool activeOnly = true,
  }) async {
    _currentPatientId = patientId;
    state = state.copyWith(isLoading: true, error: null);

    try {
      final insurances = await _service.getPatientInsurance(
        patientId,
        activeOnly: activeOnly,
      );
      state = state.copyWith(insurances: insurances, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Create new insurance policy
  Future<PatientInsurance?> createInsurance({
    required String patientId,
    required String providerName,
    required String policyNumber,
    String? groupNumber,
    String insuranceType = 'health',
    String? planName,
    DateTime? coverageStartDate,
    DateTime? coverageEndDate,
    bool isPrimary = false,
    String? subscriberName,
    String? subscriberRelationship,
    String? tpaName,
    String? tpaId,
    bool cashlessEnabled = false,
    String? networkType,
    double? copayAmount,
    double? deductibleAmount,
    double? outOfPocketMax,
    Map<String, dynamic>? additionalInfo,
  }) async {
    try {
      final insurance = await _service.createInsurance(
        patientId: patientId,
        providerName: providerName,
        policyNumber: policyNumber,
        groupNumber: groupNumber,
        insuranceType: insuranceType,
        planName: planName,
        coverageStartDate: coverageStartDate,
        coverageEndDate: coverageEndDate,
        isPrimary: isPrimary,
        subscriberName: subscriberName,
        subscriberRelationship: subscriberRelationship,
        tpaName: tpaName,
        tpaId: tpaId,
        cashlessEnabled: cashlessEnabled,
        networkType: networkType,
        copayAmount: copayAmount,
        deductibleAmount: deductibleAmount,
        outOfPocketMax: outOfPocketMax,
        additionalInfo: additionalInfo,
      );

      // Reload list
      if (_currentPatientId == patientId) {
        await loadPatientInsurance(patientId);
      }

      return insurance;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Update insurance policy
  Future<PatientInsurance?> updateInsurance(
    String insuranceId,
    Map<String, dynamic> updates,
  ) async {
    try {
      final insurance = await _service.updateInsurance(insuranceId, updates);

      // Reload list
      if (_currentPatientId != null) {
        await loadPatientInsurance(_currentPatientId!);
      }

      return insurance;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  /// Delete insurance policy
  Future<bool> deleteInsurance(String insuranceId) async {
    try {
      await _service.deleteInsurance(insuranceId);

      // Reload list
      if (_currentPatientId != null) {
        await loadPatientInsurance(_currentPatientId!);
      }

      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

// ==================
// Providers
// ==================

/// Insurance state provider
final insuranceProvider =
    StateNotifierProvider<InsuranceNotifier, InsuranceState>((ref) {
  final service = ref.watch(insuranceServiceProvider);
  return InsuranceNotifier(service);
});

/// Get detailed insurance information
final insuranceDetailsProvider =
    FutureProvider.family<PatientInsurance, String>((ref, insuranceId) async {
  final service = ref.watch(insuranceServiceProvider);
  return service.getInsurance(insuranceId);
});

// ==================
// Verification Providers
// ==================

/// Verification state
class VerificationState {
  final VerificationResult? result;
  final bool isVerifying;
  final String? error;

  const VerificationState({
    this.result,
    this.isVerifying = false,
    this.error,
  });

  VerificationState copyWith({
    VerificationResult? result,
    bool? isVerifying,
    String? error,
  }) {
    return VerificationState(
      result: result ?? this.result,
      isVerifying: isVerifying ?? this.isVerifying,
      error: error,
    );
  }
}

/// Verification state notifier
class VerificationNotifier extends StateNotifier<VerificationState> {
  final InsuranceService _service;

  VerificationNotifier(this._service) : super(const VerificationState());

  /// Verify insurance eligibility
  Future<VerificationResult?> verifyInsurance({
    required String insuranceId,
    DateTime? serviceDate,
    List<String>? procedureCodes,
    bool forceRefresh = false,
  }) async {
    state = state.copyWith(isVerifying: true, error: null);

    try {
      final result = await _service.verifyInsurance(
        insuranceId: insuranceId,
        serviceDate: serviceDate,
        procedureCodes: procedureCodes,
        forceRefresh: forceRefresh,
      );

      state = state.copyWith(result: result, isVerifying: false);
      return result;
    } catch (e) {
      state = state.copyWith(
        isVerifying: false,
        error: e.toString(),
      );
      return null;
    }
  }

  /// Clear verification result
  void clearResult() {
    state = const VerificationState();
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Verification state provider
final verificationProvider =
    StateNotifierProvider<VerificationNotifier, VerificationState>((ref) {
  final service = ref.watch(insuranceServiceProvider);
  return VerificationNotifier(service);
});

/// Get verification details by ID
final verificationDetailsProvider =
    FutureProvider.family<VerificationResult, String>((ref, verificationId) async {
  final service = ref.watch(insuranceServiceProvider);
  return service.getVerification(verificationId);
});

/// Get verification history for an insurance policy
final verificationHistoryProvider = FutureProvider.family<
    List<VerificationResult>,
    ({String insuranceId, int limit})>((ref, params) async {
  final service = ref.watch(insuranceServiceProvider);
  return service.getVerificationHistory(
    params.insuranceId,
    limit: params.limit,
  );
});

// ==================
// Provider List Providers
// ==================

/// Insurance providers list
final insuranceProvidersProvider =
    FutureProvider.family<List<InsuranceProvider>, String>((ref, country) async {
  final service = ref.watch(insuranceServiceProvider);
  return service.getProviders(country: country);
});

/// TPAs list
final tpasProvider = FutureProvider.family<List<TPA>, String>((ref, country) async {
  final service = ref.watch(insuranceServiceProvider);
  return service.getTPAs(country: country);
});
