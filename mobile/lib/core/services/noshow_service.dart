import 'package:logger/logger.dart';

import '../api/api_client.dart';
import '../models/noshow_prediction.dart';

/// Service for interacting with no-show prediction API
///
/// Handles:
/// - Predicting no-show likelihood for appointments
/// - Batch predictions
/// - High-risk appointment queries
/// - Model performance tracking
/// - Feedback submission
class NoShowService {
  final ApiClient _apiClient;
  final Logger _logger = Logger();

  NoShowService(this._apiClient);

  /// Predict no-show likelihood for a single appointment
  ///
  /// [appointmentId] - UUID of appointment to predict
  ///
  /// Returns NoShowPrediction with probability and risk level
  Future<NoShowPrediction?> predictNoShow(String appointmentId) async {
    try {
      _logger.i('Predicting no-show for appointment $appointmentId');

      final response = await _apiClient.get('/noshow/predict/$appointmentId');
      if (response == null) {
        _logger.w('No prediction returned for appointment $appointmentId');
        return null;
      }

      final prediction = NoShowPrediction.fromJson(response as Map<String, dynamic>);
      _logger.i(
        'No-show prediction: ${prediction.riskLevel} risk (${prediction.riskPercentage}%)',
      );

      return prediction;
    } catch (e) {
      _logger.e('Error predicting no-show: $e');
      return null;
    }
  }

  /// Predict no-show for multiple appointments
  ///
  /// [appointmentIds] - List of appointment UUIDs (max 100)
  ///
  /// Returns list of predictions
  Future<List<NoShowPrediction>> batchPredict(
    List<String> appointmentIds,
  ) async {
    if (appointmentIds.isEmpty) {
      _logger.w('Empty appointment list for batch prediction');
      return [];
    }

    if (appointmentIds.length > 100) {
      _logger.w('Too many appointments for batch prediction (max 100)');
      appointmentIds = appointmentIds.take(100).toList();
    }

    try {
      _logger.i('Batch predicting ${appointmentIds.length} appointments');

      final data = {
        'appointment_ids': appointmentIds,
      };

      final response = await _apiClient.post('/noshow/batch-predict', data);
      if (response == null) {
        return [];
      }

      final responseData = response as Map<String, dynamic>;
      final predictions = (responseData['predictions'] as List<dynamic>)
          .map((json) => NoShowPrediction.fromJson(json as Map<String, dynamic>))
          .toList();

      _logger.i(
        'Batch prediction completed: ${predictions.length} predictions, '
        '${responseData['high_risk_count']} high-risk',
      );

      return predictions;
    } catch (e) {
      _logger.e('Error in batch prediction: $e');
      return [];
    }
  }

  /// Get all high-risk appointments for the clinic
  ///
  /// [startDate] - Start of date range (default: today)
  /// [endDate] - End of date range (default: +7 days)
  ///
  /// Returns list of high-risk appointments with patient/doctor info
  Future<List<HighRiskAppointment>> getHighRiskAppointments({
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final params = <String, dynamic>{};

      if (startDate != null) {
        params['start_date'] = startDate.toIso8601String();
      }
      if (endDate != null) {
        params['end_date'] = endDate.toIso8601String();
      }

      final queryString = params.entries
          .map((e) => '${e.key}=${Uri.encodeComponent(e.value.toString())}')
          .join('&');

      final url = queryString.isEmpty
          ? '/noshow/high-risk'
          : '/noshow/high-risk?$queryString';

      _logger.i('Fetching high-risk appointments');

      final response = await _apiClient.get(url);
      if (response == null) {
        return [];
      }

      final responseData = response as Map<String, dynamic>;
      final appointments = (responseData['appointments'] as List<dynamic>)
          .map((json) =>
              HighRiskAppointment.fromJson(json as Map<String, dynamic>))
          .toList();

      _logger.i('Found ${appointments.length} high-risk appointments');

      return appointments;
    } catch (e) {
      _logger.e('Error fetching high-risk appointments: $e');
      return [];
    }
  }

  /// Submit actual appointment outcome for model improvement
  ///
  /// [appointmentId] - Appointment UUID
  /// [actualStatus] - Actual outcome: 'completed', 'no_show', or 'cancelled'
  ///
  /// Returns true if feedback was submitted successfully
  Future<bool> submitFeedback({
    required String appointmentId,
    required String actualStatus,
  }) async {
    try {
      _logger.i('Submitting feedback for appointment $appointmentId: $actualStatus');

      final data = {
        'appointment_id': appointmentId,
        'actual_status': actualStatus,
      };

      final response = await _apiClient.post('/noshow/feedback', data);
      if (response == null) {
        return false;
      }

      final responseData = response as Map<String, dynamic>;
      final success = responseData['success'] as bool;

      if (success) {
        final wasAccurate = responseData['was_accurate'];
        _logger.i(
          'Feedback submitted successfully. Prediction was ${wasAccurate == true ? 'accurate' : 'inaccurate'}',
        );
      }

      return success;
    } catch (e) {
      _logger.e('Error submitting feedback: $e');
      return false;
    }
  }

  /// Get model performance statistics
  ///
  /// Returns model stats including accuracy and risk distribution
  Future<ModelStats?> getModelStats() async {
    try {
      _logger.i('Fetching model statistics');

      final response = await _apiClient.get('/noshow/model-stats');
      if (response == null) {
        return null;
      }

      final stats = ModelStats.fromJson(response as Map<String, dynamic>);
      _logger.i(
        'Model stats: ${stats.accuracyPercentage}% accuracy, '
        '${stats.totalPredictions} predictions',
      );

      return stats;
    } catch (e) {
      _logger.e('Error fetching model stats: $e');
      return null;
    }
  }

  /// Trigger model retraining (admin only)
  ///
  /// [minSamples] - Minimum number of samples needed for training
  ///
  /// Returns training results or null if error
  Future<Map<String, dynamic>?> retrainModel({int minSamples = 100}) async {
    try {
      _logger.i('Triggering model retraining (min samples: $minSamples)');

      final data = {
        'min_samples': minSamples,
      };

      final response = await _apiClient.post('/noshow/retrain', data);
      if (response == null) {
        return null;
      }

      final result = response as Map<String, dynamic>;
      if (result['success'] == true) {
        _logger.i('Model retraining successful: ${result['message']}');
      } else {
        _logger.w('Model retraining failed: ${result['message']}');
      }

      return result;
    } catch (e) {
      _logger.e('Error retraining model: $e');
      return null;
    }
  }

  /// Get prediction for appointment if it exists
  ///
  /// This is useful for checking if a prediction has already been made
  /// without triggering a new prediction
  ///
  /// [appointmentId] - Appointment UUID
  ///
  /// Returns existing prediction or null if not found
  Future<NoShowPrediction?> getExistingPrediction(
    String appointmentId,
  ) async {
    // The predict endpoint will return existing prediction if available
    // without creating a new one (based on implementation)
    return predictNoShow(appointmentId);
  }

  /// Check if an appointment is high-risk
  ///
  /// Convenience method that predicts and checks risk level
  ///
  /// [appointmentId] - Appointment UUID
  ///
  /// Returns true if high-risk, false otherwise
  Future<bool> isHighRisk(String appointmentId) async {
    final prediction = await predictNoShow(appointmentId);
    return prediction?.isHighRisk ?? false;
  }

  /// Get risk summary for multiple appointments
  ///
  /// [appointmentIds] - List of appointment UUIDs
  ///
  /// Returns map of risk level to count
  Future<Map<String, int>> getRiskSummary(
    List<String> appointmentIds,
  ) async {
    final predictions = await batchPredict(appointmentIds);

    final summary = <String, int>{
      'high': 0,
      'medium': 0,
      'low': 0,
    };

    for (final prediction in predictions) {
      summary[prediction.riskLevel] = (summary[prediction.riskLevel] ?? 0) + 1;
    }

    return summary;
  }
}
