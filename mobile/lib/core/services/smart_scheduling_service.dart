import '../api/api_client.dart';

/// Smart scheduling service for AI-powered appointment suggestions
class SmartSchedulingService {
  final ApiClient _apiClient;

  SmartSchedulingService(this._apiClient);

  /// Get smart slot suggestions for a patient
  ///
  /// [patientId] - Patient to book for
  /// [doctorId] - Doctor to see
  /// [appointmentType] - Type of appointment (new_consultation, follow_up, etc.)
  /// [preferredDate] - Optional preferred date (YYYY-MM-DD format)
  /// [durationMinutes] - Required appointment duration
  /// [maxSuggestions] - Maximum number of suggestions to return (1-10)
  ///
  /// Returns a map with:
  /// - patient_id: String
  /// - doctor_id: String
  /// - suggestions: List of slot suggestions
  /// - total_analyzed: Number of slots analyzed
  Future<Map<String, dynamic>> getSlotSuggestions({
    required String patientId,
    required String doctorId,
    String appointmentType = 'new_consultation',
    String? preferredDate,
    int durationMinutes = 15,
    int maxSuggestions = 5,
  }) async {
    final queryParams = <String, dynamic>{
      'doctor_id': doctorId,
      'appointment_type': appointmentType,
      'duration_minutes': durationMinutes.toString(),
      'max_suggestions': maxSuggestions.toString(),
    };

    if (preferredDate != null) {
      queryParams['preferred_date'] = preferredDate;
    }

    final response = await _apiClient.get(
      '/scheduling/suggestions/$patientId',
      queryParameters: queryParams,
    );

    return response as Map<String, dynamic>;
  }

  /// Post slot suggestions request (alternative to GET)
  ///
  /// Useful when you need to send more complex request data
  Future<Map<String, dynamic>> postSlotSuggestions({
    required String patientId,
    required String doctorId,
    String appointmentType = 'new_consultation',
    String? preferredDate,
    int durationMinutes = 15,
    int maxSuggestions = 5,
  }) async {
    final response = await _apiClient.post('/scheduling/suggestions', {
      'patient_id': patientId,
      'doctor_id': doctorId,
      'appointment_type': appointmentType,
      if (preferredDate != null) 'preferred_date': preferredDate,
      'duration_minutes': durationMinutes,
      'max_suggestions': maxSuggestions,
    });

    return response as Map<String, dynamic>;
  }

  /// Get optimal booking times for a doctor
  ///
  /// Analyzes historical data to find the best time windows for appointments.
  ///
  /// [doctorId] - Doctor to analyze
  /// [days] - Number of days of history to analyze (7-90)
  ///
  /// Returns:
  /// - doctor_id: String
  /// - analyzed_period_days: int
  /// - optimal_windows: List of optimal time windows
  /// - total_appointments_analyzed: int
  Future<Map<String, dynamic>> getOptimalBookingTimes({
    required String doctorId,
    int days = 30,
  }) async {
    final response = await _apiClient.get(
      '/scheduling/optimal-times/$doctorId',
      queryParameters: {
        'days': days.toString(),
      },
    );

    return response as Map<String, dynamic>;
  }

  /// Get scheduling pattern analysis for a doctor
  ///
  /// Returns detailed insights about booking patterns, peak times, etc.
  ///
  /// [doctorId] - Doctor to analyze
  /// [period] - Period to analyze: 'week', 'month', 'quarter', 'year'
  /// [startDate] - Optional custom start date (YYYY-MM-DD)
  /// [endDate] - Optional custom end date (YYYY-MM-DD)
  ///
  /// Returns:
  /// - doctor_id: String
  /// - period: Map with start and end dates
  /// - total_appointments: int
  /// - patterns: Detailed pattern breakdown
  /// - recommendations: List of AI-generated recommendations
  Future<Map<String, dynamic>> getSchedulingPatterns({
    required String doctorId,
    String period = 'month',
    String? startDate,
    String? endDate,
  }) async {
    final queryParams = {
      'period': period,
    };

    if (startDate != null) {
      queryParams['start_date'] = startDate;
    }
    if (endDate != null) {
      queryParams['end_date'] = endDate;
    }

    final response = await _apiClient.get(
      '/scheduling/patterns/$doctorId',
      queryParameters: queryParams,
    );

    return response as Map<String, dynamic>;
  }

  /// Submit feedback on suggestion quality
  ///
  /// Helps improve the AI algorithm by tracking which suggestions work well.
  ///
  /// [patientId] - Patient ID
  /// [doctorId] - Doctor ID
  /// [suggestedSlot] - The suggested slot time (ISO 8601 format)
  /// [wasAccepted] - Whether the suggestion was accepted
  /// [actualSlot] - The actual slot booked (if different)
  /// [feedbackNotes] - Optional feedback text
  Future<Map<String, dynamic>> submitSuggestionFeedback({
    required String patientId,
    required String doctorId,
    required String suggestedSlot,
    required bool wasAccepted,
    String? actualSlot,
    String? feedbackNotes,
  }) async {
    final response = await _apiClient.post('/scheduling/feedback', {
      'patient_id': patientId,
      'doctor_id': doctorId,
      'suggested_slot': suggestedSlot,
      'was_accepted': wasAccepted,
      if (actualSlot != null) 'actual_slot': actualSlot,
      if (feedbackNotes != null) 'feedback_notes': feedbackNotes,
    });

    return response as Map<String, dynamic>;
  }
}
