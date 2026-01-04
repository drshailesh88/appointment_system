import '../api/api_client.dart';
import '../models/insurance.dart';

/// Insurance service for managing patient insurance and verification
class InsuranceService {
  final ApiClient _apiClient;

  InsuranceService(this._apiClient);

  // ==================
  // Insurance Info
  // ==================

  /// Create new insurance policy for a patient
  Future<PatientInsurance> createInsurance({
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
    final response = await _apiClient.post('/insurance', {
      'patient_id': patientId,
      'provider_name': providerName,
      'policy_number': policyNumber,
      if (groupNumber != null) 'group_number': groupNumber,
      'insurance_type': insuranceType,
      if (planName != null) 'plan_name': planName,
      if (coverageStartDate != null)
        'coverage_start_date':
            coverageStartDate.toIso8601String().split('T')[0],
      if (coverageEndDate != null)
        'coverage_end_date': coverageEndDate.toIso8601String().split('T')[0],
      'is_primary': isPrimary,
      if (subscriberName != null) 'subscriber_name': subscriberName,
      if (subscriberRelationship != null)
        'subscriber_relationship': subscriberRelationship,
      if (tpaName != null) 'tpa_name': tpaName,
      if (tpaId != null) 'tpa_id': tpaId,
      'cashless_enabled': cashlessEnabled,
      if (networkType != null) 'network_type': networkType,
      if (copayAmount != null) 'copay_amount': copayAmount,
      if (deductibleAmount != null) 'deductible_amount': deductibleAmount,
      if (outOfPocketMax != null) 'out_of_pocket_max': outOfPocketMax,
      if (additionalInfo != null) 'additional_info': additionalInfo,
    });

    return PatientInsurance.fromJson(response as Map<String, dynamic>);
  }

  /// Get all insurance policies for a patient
  Future<List<InsuranceListItem>> getPatientInsurance(
    String patientId, {
    bool activeOnly = true,
  }) async {
    final response = await _apiClient.get(
      '/insurance/patient/$patientId',
      queryParameters: {
        'active_only': activeOnly,
      },
    );

    final data = response as Map<String, dynamic>;
    final insurances = data['insurances'] as List;
    return insurances
        .map((json) => InsuranceListItem.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  /// Get detailed insurance information
  Future<PatientInsurance> getInsurance(String insuranceId) async {
    final response = await _apiClient.get('/insurance/$insuranceId');
    return PatientInsurance.fromJson(response as Map<String, dynamic>);
  }

  /// Update insurance information
  Future<PatientInsurance> updateInsurance(
    String insuranceId,
    Map<String, dynamic> updates,
  ) async {
    final response = await _apiClient.put('/insurance/$insuranceId', updates);
    return PatientInsurance.fromJson(response as Map<String, dynamic>);
  }

  /// Delete (deactivate) insurance
  Future<void> deleteInsurance(String insuranceId) async {
    await _apiClient.delete('/insurance/$insuranceId');
  }

  // ==================
  // Verification
  // ==================

  /// Verify insurance eligibility
  ///
  /// [insuranceId] - Insurance policy to verify
  /// [serviceDate] - Date of service (optional, defaults to today)
  /// [procedureCodes] - List of procedure codes to check (optional)
  /// [forceRefresh] - Force new verification even if cached result exists
  Future<VerificationResult> verifyInsurance({
    required String insuranceId,
    DateTime? serviceDate,
    List<String>? procedureCodes,
    bool forceRefresh = false,
  }) async {
    final response = await _apiClient.post('/insurance/verify', {
      'insurance_id': insuranceId,
      if (serviceDate != null)
        'service_date': serviceDate.toIso8601String().split('T')[0],
      if (procedureCodes != null) 'procedure_codes': procedureCodes,
      'force_refresh': forceRefresh,
    });

    return VerificationResult.fromJson(response as Map<String, dynamic>);
  }

  /// Get verification details by ID
  Future<VerificationResult> getVerification(String verificationId) async {
    final response =
        await _apiClient.get('/insurance/verification/$verificationId');
    return VerificationResult.fromJson(response as Map<String, dynamic>);
  }

  /// Get verification history for an insurance policy
  Future<List<VerificationResult>> getVerificationHistory(
    String insuranceId, {
    int limit = 10,
  }) async {
    final response = await _apiClient.get(
      '/insurance/verification/history/$insuranceId',
      queryParameters: {
        'limit': limit,
      },
    );

    final verifications = response as List;
    return verifications
        .map((json) =>
            VerificationResult.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  // ==================
  // Providers & TPAs
  // ==================

  /// Get list of supported insurance providers
  Future<List<InsuranceProvider>> getProviders({String country = 'IN'}) async {
    final response = await _apiClient.get(
      '/insurance/providers/list',
      queryParameters: {
        'country': country,
      },
    );

    final data = response as Map<String, dynamic>;
    final providers = data['providers'] as List;
    return providers
        .map((json) => InsuranceProvider.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  /// Get list of TPAs (Third-Party Administrators)
  Future<List<TPA>> getTPAs({String country = 'IN'}) async {
    final response = await _apiClient.get(
      '/insurance/providers/tpas',
      queryParameters: {
        'country': country,
      },
    );

    final tpas = response as List;
    return tpas.map((json) => TPA.fromJson(json as Map<String, dynamic>)).toList();
  }
}
