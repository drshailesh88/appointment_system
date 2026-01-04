import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';

/// Voice booking states
enum VoiceBookingStatus {
  idle,
  listening,
  processing,
  responding,
  error,
}

/// Voice booking result
class VoiceBookingResult {
  final bool success;
  final String? message;
  final String? appointmentId;
  final Map<String, dynamic>? appointmentDetails;
  final String? errorMessage;

  const VoiceBookingResult({
    required this.success,
    this.message,
    this.appointmentId,
    this.appointmentDetails,
    this.errorMessage,
  });

  factory VoiceBookingResult.fromJson(Map<String, dynamic> json) {
    return VoiceBookingResult(
      success: json['success'] ?? false,
      message: json['message'],
      appointmentId: json['appointment_id'],
      appointmentDetails: json['appointment'],
      errorMessage: json['error'],
    );
  }
}

/// Voice booking state
class VoiceBookingState {
  final VoiceBookingStatus status;
  final String? transcript;
  final String? response;
  final VoiceBookingResult? result;
  final String? errorMessage;
  final double? audioLevel;

  const VoiceBookingState({
    this.status = VoiceBookingStatus.idle,
    this.transcript,
    this.response,
    this.result,
    this.errorMessage,
    this.audioLevel,
  });

  VoiceBookingState copyWith({
    VoiceBookingStatus? status,
    String? transcript,
    String? response,
    VoiceBookingResult? result,
    String? errorMessage,
    double? audioLevel,
  }) {
    return VoiceBookingState(
      status: status ?? this.status,
      transcript: transcript ?? this.transcript,
      response: response ?? this.response,
      result: result ?? this.result,
      errorMessage: errorMessage,
      audioLevel: audioLevel ?? this.audioLevel,
    );
  }

  bool get isListening => status == VoiceBookingStatus.listening;
  bool get isProcessing => status == VoiceBookingStatus.processing;
  bool get isResponding => status == VoiceBookingStatus.responding;
  bool get hasError => status == VoiceBookingStatus.error;
  bool get isActive =>
      status == VoiceBookingStatus.listening ||
      status == VoiceBookingStatus.processing ||
      status == VoiceBookingStatus.responding;
}

/// Voice booking notifier
class VoiceBookingNotifier extends StateNotifier<VoiceBookingState> {
  final ApiClient _apiClient;
  Timer? _audioLevelTimer;

  VoiceBookingNotifier(this._apiClient) : super(const VoiceBookingState());

  /// Start listening for voice input
  Future<void> startListening() async {
    state = state.copyWith(
      status: VoiceBookingStatus.listening,
      transcript: null,
      response: null,
      result: null,
      errorMessage: null,
    );

    // Simulate audio level updates (in real app, connect to microphone)
    _simulateAudioLevels();
  }

  /// Stop listening and process the audio
  Future<void> stopListening() async {
    _audioLevelTimer?.cancel();

    state = state.copyWith(
      status: VoiceBookingStatus.processing,
      audioLevel: null,
    );

    try {
      // In a real app, we would send audio to the backend
      // For now, simulate a voice booking request
      await Future.delayed(const Duration(milliseconds: 500));

      // Simulate transcript
      state = state.copyWith(
        transcript: 'Book an appointment with Dr. Sharma for tomorrow at 10 AM',
      );

      // Send to voice agent endpoint
      final response = await _apiClient.post('/voice/process', {
        'transcript': state.transcript,
        'language': 'en',
      });

      if (response != null) {
        state = state.copyWith(
          status: VoiceBookingStatus.responding,
          response: response['response_text'] ?? 'Appointment booked successfully',
        );

        // Parse result
        final result = VoiceBookingResult.fromJson(response);
        state = state.copyWith(result: result);

        // Return to idle after response
        await Future.delayed(const Duration(seconds: 2));
        state = state.copyWith(status: VoiceBookingStatus.idle);
      }
    } catch (e) {
      state = state.copyWith(
        status: VoiceBookingStatus.error,
        errorMessage: e.toString(),
      );
    }
  }

  /// Cancel the current voice booking session
  void cancel() {
    _audioLevelTimer?.cancel();
    state = const VoiceBookingState();
  }

  /// Process text input (for testing without microphone)
  Future<void> processTextInput(String text) async {
    state = state.copyWith(
      status: VoiceBookingStatus.processing,
      transcript: text,
    );

    try {
      final response = await _apiClient.post('/voice/process', {
        'transcript': text,
        'language': 'en',
      });

      if (response != null) {
        state = state.copyWith(
          status: VoiceBookingStatus.responding,
          response: response['response_text'],
        );

        final result = VoiceBookingResult.fromJson(response);
        state = state.copyWith(result: result);

        await Future.delayed(const Duration(seconds: 2));
        state = state.copyWith(status: VoiceBookingStatus.idle);
      }
    } catch (e) {
      state = state.copyWith(
        status: VoiceBookingStatus.error,
        errorMessage: e.toString(),
      );
    }
  }

  /// Simulate audio level changes for UI feedback
  void _simulateAudioLevels() {
    _audioLevelTimer = Timer.periodic(const Duration(milliseconds: 100), (_) {
      if (state.isListening) {
        // Random audio level between 0.1 and 1.0
        final level = 0.1 + (DateTime.now().millisecond % 90) / 100;
        state = state.copyWith(audioLevel: level);
      }
    });
  }

  @override
  void dispose() {
    _audioLevelTimer?.cancel();
    super.dispose();
  }
}

/// Voice booking provider
final voiceBookingProvider =
    StateNotifierProvider<VoiceBookingNotifier, VoiceBookingState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return VoiceBookingNotifier(apiClient);
});

/// Quick phrase suggestions for voice booking
const voiceBookingSuggestions = [
  'Book an appointment for tomorrow',
  'Schedule a follow-up with Dr. Sharma',
  'Cancel my appointment on Monday',
  'Check my appointment status',
  'Reschedule to next week',
];
