import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../models/organization.dart';
import '../models/clinic.dart';

/// Service for managing organizations and clinics
class OrganizationService {
  final ApiClient _apiClient;

  OrganizationService(this._apiClient);

  /// Get all organizations
  Future<List<Organization>> getOrganizations() async {
    final response = await _apiClient.get('/api/v1/organizations');
    return (response as List)
        .map((json) => Organization.fromJson(json))
        .toList();
  }

  /// Get organization by ID
  Future<Organization> getOrganization(String organizationId) async {
    final response = await _apiClient.get('/api/v1/organizations/$organizationId');
    return Organization.fromJson(response);
  }

  /// Create organization
  Future<Organization> createOrganization(Map<String, dynamic> data) async {
    final response = await _apiClient.post('/api/v1/organizations', data);
    return Organization.fromJson(response);
  }

  /// Update organization
  Future<Organization> updateOrganization(
    String organizationId,
    Map<String, dynamic> data,
  ) async {
    final response = await _apiClient.put(
      '/api/v1/organizations/$organizationId',
      data,
    );
    return Organization.fromJson(response);
  }

  /// Delete organization
  Future<void> deleteOrganization(String organizationId) async {
    await _apiClient.delete('/api/v1/organizations/$organizationId');
  }

  /// Get clinics for an organization
  Future<List<Clinic>> getClinics(String organizationId) async {
    final response = await _apiClient.get(
      '/api/v1/organizations/$organizationId/clinics',
    );
    return (response as List).map((json) => Clinic.fromJson(json)).toList();
  }

  /// Get clinic by ID
  Future<Clinic> getClinic(String organizationId, String clinicId) async {
    final response = await _apiClient.get(
      '/api/v1/organizations/$organizationId/clinics/$clinicId',
    );
    return Clinic.fromJson(response);
  }

  /// Create clinic
  Future<Clinic> createClinic(
    String organizationId,
    Map<String, dynamic> data,
  ) async {
    final response = await _apiClient.post(
      '/api/v1/organizations/$organizationId/clinics',
      data,
    );
    return Clinic.fromJson(response);
  }

  /// Update clinic
  Future<Clinic> updateClinic(
    String organizationId,
    String clinicId,
    Map<String, dynamic> data,
  ) async {
    final response = await _apiClient.put(
      '/api/v1/organizations/$organizationId/clinics/$clinicId',
      data,
    );
    return Clinic.fromJson(response);
  }

  /// Delete clinic
  Future<void> deleteClinic(String organizationId, String clinicId) async {
    await _apiClient.delete(
      '/api/v1/organizations/$organizationId/clinics/$clinicId',
    );
  }

  /// Get consolidated analytics across all clinics
  Future<Map<String, dynamic>> getConsolidatedAnalytics(
    String organizationId, {
    String? startDate,
    String? endDate,
  }) async {
    final response = await _apiClient.get(
      '/api/v1/organizations/$organizationId/analytics',
      queryParameters: {
        if (startDate != null) 'start_date': startDate,
        if (endDate != null) 'end_date': endDate,
      },
    );
    return response;
  }
}

/// Provider for OrganizationService
final organizationServiceProvider = Provider<OrganizationService>((ref) {
  // TODO: Inject ApiClient properly
  final apiClient = ApiClient();
  return OrganizationService(apiClient);
});
