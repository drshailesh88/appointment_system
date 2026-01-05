import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

import '../models/consultation.dart';
import 'auth_provider.dart';

/// Telemedicine state
class TelemedicineState {
  final Consultation? activeConsultation;
  final WaitingRoomStatus? waitingRoomStatus;
  final DoctorQueueResponse? doctorQueue;
  final bool isLoading;
  final String? error;

  const TelemedicineState({
    this.activeConsultation,
    this.waitingRoomStatus,
    this.doctorQueue,
    this.isLoading = false,
    this.error,
  });

  TelemedicineState copyWith({
    Consultation? activeConsultation,
    WaitingRoomStatus? waitingRoomStatus,
    DoctorQueueResponse? doctorQueue,
    bool? isLoading,
    String? error,
  }) {
    return TelemedicineState(
      activeConsultation: activeConsultation ?? this.activeConsultation,
      waitingRoomStatus: waitingRoomStatus ?? this.waitingRoomStatus,
      doctorQueue: doctorQueue ?? this.doctorQueue,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Telemedicine notifier
class TelemedicineNotifier extends StateNotifier<TelemedicineState> {
  final String baseUrl;
  final String? authToken;
  Timer? _waitingRoomTimer;
  Timer? _doctorQueueTimer;

  TelemedicineNotifier({
    required this.baseUrl,
    required this.authToken,
  }) : super(const TelemedicineState());

  /// Create consultation for an appointment
  Future<Consultation?> createConsultation(String appointmentId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/telemedicine/consultations'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({
          'appointment_id': appointmentId,
        }),
      );

      if (response.statusCode == 201) {
        final consultation =
            Consultation.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
        state = state.copyWith(
          activeConsultation: consultation,
          isLoading: false,
        );
        return consultation;
      } else {
        final errorData = jsonDecode(response.body) as Map<String, dynamic>;
        state = state.copyWith(
          isLoading: false,
          error: errorData['detail'] ?? 'Failed to create consultation',
        );
        return null;
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Network error: $e',
      );
      return null;
    }
  }

  /// Patient joins waiting room
  Future<bool> joinWaitingRoom(
    String consultationId, {
    String? deviceType,
    String? connectionType,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final queryParams = <String, String>{};
      if (deviceType != null) queryParams['device_type'] = deviceType;
      if (connectionType != null) queryParams['connection_type'] = connectionType;

      final uri = Uri.parse(
          '$baseUrl/api/v1/telemedicine/consultations/$consultationId/waiting-room/join');

      final response = await http.post(
        uri.replace(queryParameters: queryParams),
        headers: {
          'Authorization': 'Bearer $authToken',
        },
      );

      if (response.statusCode == 200) {
        state = state.copyWith(isLoading: false);
        // Start polling for status updates
        _startWaitingRoomPolling(consultationId);
        return true;
      } else {
        final errorData = jsonDecode(response.body) as Map<String, dynamic>;
        state = state.copyWith(
          isLoading: false,
          error: errorData['detail'] ?? 'Failed to join waiting room',
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Network error: $e',
      );
      return false;
    }
  }

  /// Get waiting room status
  Future<WaitingRoomStatus?> getWaitingRoomStatus(String consultationId) async {
    try {
      final response = await http.get(
        Uri.parse(
            '$baseUrl/api/v1/telemedicine/consultations/$consultationId/waiting-room/status'),
        headers: {
          'Authorization': 'Bearer $authToken',
        },
      );

      if (response.statusCode == 200) {
        final status = WaitingRoomStatus.fromJson(
            jsonDecode(response.body) as Map<String, dynamic>);
        state = state.copyWith(waitingRoomStatus: status);
        return status;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Doctor admits patient
  Future<JoinRoomResponse?> admitPatient(String consultationId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await http.post(
        Uri.parse(
            '$baseUrl/api/v1/telemedicine/consultations/$consultationId/admit'),
        headers: {
          'Authorization': 'Bearer $authToken',
        },
      );

      if (response.statusCode == 200) {
        final joinResponse = JoinRoomResponse.fromJson(
            jsonDecode(response.body) as Map<String, dynamic>);
        state = state.copyWith(isLoading: false);
        return joinResponse;
      } else {
        final errorData = jsonDecode(response.body) as Map<String, dynamic>;
        state = state.copyWith(
          isLoading: false,
          error: errorData['detail'] ?? 'Failed to admit patient',
        );
        return null;
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Network error: $e',
      );
      return null;
    }
  }

  /// Join consultation (doctor or patient)
  Future<JoinRoomResponse?> joinConsultation(String consultationId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await http.post(
        Uri.parse(
            '$baseUrl/api/v1/telemedicine/consultations/$consultationId/join'),
        headers: {
          'Authorization': 'Bearer $authToken',
        },
      );

      if (response.statusCode == 200) {
        final joinResponse = JoinRoomResponse.fromJson(
            jsonDecode(response.body) as Map<String, dynamic>);
        state = state.copyWith(isLoading: false);
        return joinResponse;
      } else {
        final errorData = jsonDecode(response.body) as Map<String, dynamic>;
        state = state.copyWith(
          isLoading: false,
          error: errorData['detail'] ?? 'Failed to join consultation',
        );
        return null;
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Network error: $e',
      );
      return null;
    }
  }

  /// End consultation
  Future<bool> endConsultation(
    String consultationId, {
    String? notes,
    String? connectionQuality,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await http.post(
        Uri.parse(
            '$baseUrl/api/v1/telemedicine/consultations/$consultationId/end'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({
          if (notes != null) 'notes': notes,
          if (connectionQuality != null) 'connection_quality': connectionQuality,
        }),
      );

      if (response.statusCode == 200) {
        state = state.copyWith(
          isLoading: false,
          activeConsultation: null,
        );
        _stopWaitingRoomPolling();
        return true;
      } else {
        final errorData = jsonDecode(response.body) as Map<String, dynamic>;
        state = state.copyWith(
          isLoading: false,
          error: errorData['detail'] ?? 'Failed to end consultation',
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Network error: $e',
      );
      return false;
    }
  }

  /// Submit rating
  Future<bool> submitRating(
    String consultationId,
    int rating, {
    String? feedback,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(
            '$baseUrl/api/v1/telemedicine/consultations/$consultationId/rating'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({
          'rating': rating,
          if (feedback != null) 'feedback': feedback,
        }),
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Get doctor's queue
  Future<DoctorQueueResponse?> getDoctorQueue() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/telemedicine/consultations/queue'),
        headers: {
          'Authorization': 'Bearer $authToken',
        },
      );

      if (response.statusCode == 200) {
        final queueResponse = DoctorQueueResponse.fromJson(
            jsonDecode(response.body) as Map<String, dynamic>);
        state = state.copyWith(doctorQueue: queueResponse);
        return queueResponse;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Start polling waiting room status
  void _startWaitingRoomPolling(String consultationId) {
    _waitingRoomTimer?.cancel();
    _waitingRoomTimer = Timer.periodic(
      const Duration(seconds: 5),
      (timer) async {
        final status = await getWaitingRoomStatus(consultationId);
        // If patient was admitted, stop polling
        if (status?.status == 'in_progress') {
          _stopWaitingRoomPolling();
        }
      },
    );
  }

  /// Stop waiting room polling
  void _stopWaitingRoomPolling() {
    _waitingRoomTimer?.cancel();
    _waitingRoomTimer = null;
  }

  /// Start polling doctor queue
  void startDoctorQueuePolling() {
    _doctorQueueTimer?.cancel();
    _doctorQueueTimer = Timer.periodic(
      const Duration(seconds: 3),
      (timer) async {
        await getDoctorQueue();
      },
    );
  }

  /// Stop doctor queue polling
  void stopDoctorQueuePolling() {
    _doctorQueueTimer?.cancel();
    _doctorQueueTimer = null;
  }

  @override
  void dispose() {
    _stopWaitingRoomPolling();
    stopDoctorQueuePolling();
    super.dispose();
  }
}

/// Telemedicine provider
final telemedicineProvider =
    StateNotifierProvider<TelemedicineNotifier, TelemedicineState>((ref) {
  final auth = ref.watch(authProvider);
  return TelemedicineNotifier(
    baseUrl: 'http://localhost:8000', // TODO: Get from config
    authToken: auth.token,
  );
});
