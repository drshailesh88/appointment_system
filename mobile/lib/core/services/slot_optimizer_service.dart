import '../api/api_client.dart';

/// Slot optimizer service for AI-powered scheduling recommendations
class SlotOptimizerService {
  final ApiClient _apiClient;

  SlotOptimizerService(this._apiClient);

  /// Get optimal available slots for a doctor
  ///
  /// [doctorId] - Doctor to find slots for
  /// [dateFrom] - Start of date range
  /// [dateTo] - End of date range
  /// [durationMinutes] - Appointment duration
  /// [appointmentType] - Type of appointment (optional)
  /// [patientId] - Patient ID for preference matching (optional)
  /// [maxRecommendations] - Number of recommendations (1-20)
  Future<Map<String, dynamic>> getOptimalSlots({
    required String doctorId,
    required String dateFrom,
    required String dateTo,
    int durationMinutes = 15,
    String? appointmentType,
    String? patientId,
    int maxRecommendations = 5,
  }) async {
    final queryParams = {
      'date_from': dateFrom,
      'date_to': dateTo,
      'duration_minutes': durationMinutes.toString(),
      'max_recommendations': maxRecommendations.toString(),
      if (appointmentType != null) 'appointment_type': appointmentType,
      if (patientId != null) 'patient_id': patientId,
    };

    final queryString = queryParams.entries
        .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
        .join('&');

    final response = await _apiClient.get('/slots/optimal/$doctorId?$queryString');
    return response as Map<String, dynamic>;
  }

  /// Get slot recommendations with advanced filtering
  ///
  /// [request] - Complex recommendation request with constraints
  Future<Map<String, dynamic>> getSlotRecommendations(
    Map<String, dynamic> request,
  ) async {
    final response = await _apiClient.post('/slots/recommendations', request);
    return response as Map<String, dynamic>;
  }

  /// Analyze current schedule efficiency
  ///
  /// [doctorId] - Doctor to analyze
  /// [targetDate] - Date to analyze
  Future<Map<String, dynamic>> analyzeSchedule({
    required String doctorId,
    required String targetDate,
  }) async {
    final response = await _apiClient.post(
      '/slots/analyze-schedule?doctor_id=$doctorId&target_date=$targetDate',
      {},
    );
    return response as Map<String, dynamic>;
  }

  /// Get utilization metrics for a doctor
  ///
  /// [doctorId] - Doctor to analyze
  /// [dateFrom] - Start of analysis period
  /// [dateTo] - End of analysis period
  Future<Map<String, dynamic>> getUtilizationMetrics({
    required String doctorId,
    required String dateFrom,
    required String dateTo,
  }) async {
    final response = await _apiClient.get(
      '/slots/utilization/$doctorId?date_from=$dateFrom&date_to=$dateTo',
    );
    return response as Map<String, dynamic>;
  }

  /// Identify gaps in schedule
  ///
  /// [doctorId] - Doctor to analyze
  /// [targetDate] - Date to analyze
  Future<Map<String, dynamic>> identifyGaps({
    required String doctorId,
    required String targetDate,
  }) async {
    final response = await _apiClient.get(
      '/slots/gaps/$doctorId?target_date=$targetDate',
    );
    return response as Map<String, dynamic>;
  }

  /// Get schedule optimization suggestions
  ///
  /// [doctorId] - Doctor to optimize for
  /// [dateFrom] - Analysis start date
  /// [dateTo] - Analysis end date
  Future<Map<String, dynamic>> suggestAdjustments({
    required String doctorId,
    required String dateFrom,
    required String dateTo,
  }) async {
    final response = await _apiClient.post(
      '/slots/suggest-adjustments?doctor_id=$doctorId&date_from=$dateFrom&date_to=$dateTo',
      {},
    );
    return response as Map<String, dynamic>;
  }
}
