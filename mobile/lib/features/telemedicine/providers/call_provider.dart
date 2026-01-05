import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:logger/logger.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../core/models/call_state.dart';
import '../../../core/models/ice_candidate.dart' as models;
import '../../../core/services/webrtc_service.dart';
import '../../../core/services/signaling_service.dart';
import '../../../core/providers/auth_provider.dart';

/// Call provider that manages the WebRTC call lifecycle
class CallNotifier extends StateNotifier<CallState> {
  final WebRTCService _webrtcService;
  final SignalingService _signalingService;
  final Logger _logger = Logger();

  Timer? _durationTimer;
  Timer? _statsTimer;
  StreamSubscription? _offerSubscription;
  StreamSubscription? _answerSubscription;
  StreamSubscription? _iceCandidateSubscription;
  StreamSubscription? _connectionStateSubscription;
  final List<ChatMessage> _chatMessages = [];

  CallNotifier({
    required WebRTCService webrtcService,
    required SignalingService signalingService,
  })  : _webrtcService = webrtcService,
        _signalingService = signalingService,
        super(const CallState()) {
    _setupWebRTCCallbacks();
    _setupSignalingListeners();
  }

  /// Get chat messages
  List<ChatMessage> get chatMessages => List.unmodifiable(_chatMessages);

  /// Setup WebRTC callbacks
  void _setupWebRTCCallbacks() {
    _webrtcService.onIceCandidate = (candidate) {
      _logger.d('Local ICE candidate generated');
      final iceCandidate = models.IceCandidate(
        candidate: candidate.candidate ?? '',
        sdpMid: candidate.sdpMid,
        sdpMLineIndex: candidate.sdpMLineIndex,
      );
      _signalingService.sendIceCandidate(iceCandidate);
    };

    _webrtcService.onTrack = (stream) {
      _logger.i('Remote stream received');
      state = state.copyWith(remoteStream: stream);
    };

    _webrtcService.onConnectionStateChange = (connectionState) {
      _logger.i('WebRTC connection state: $connectionState');

      if (connectionState == RTCPeerConnectionState.RTCPeerConnectionStateConnected) {
        state = state.copyWith(status: CallStatus.connected);
        _startCallDurationTimer();
        _startStatsMonitoring();
      } else if (connectionState ==
          RTCPeerConnectionState.RTCPeerConnectionStateDisconnected) {
        state = state.copyWith(status: CallStatus.disconnected);
      } else if (connectionState == RTCPeerConnectionState.RTCPeerConnectionStateFailed) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Connection failed',
        );
      }
    };
  }

  /// Setup signaling listeners
  void _setupSignalingListeners() {
    _offerSubscription = _signalingService.offerStream.listen((offer) async {
      _logger.i('Received SDP offer');
      await _handleOffer(offer);
    });

    _answerSubscription = _signalingService.answerStream.listen((answer) async {
      _logger.i('Received SDP answer');
      await _handleAnswer(answer);
    });

    _iceCandidateSubscription =
        _signalingService.iceCandidateStream.listen((candidate) async {
      _logger.d('Received remote ICE candidate');
      await _webrtcService.addIceCandidate(candidate);
    });

    _connectionStateSubscription =
        _signalingService.connectionStateStream.listen((connectionState) {
      if (connectionState == SignalingConnectionState.error) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Signaling connection failed',
        );
      }
    });
  }

  /// Check and request permissions
  Future<bool> checkPermissions() async {
    final cameraStatus = await Permission.camera.request();
    final microphoneStatus = await Permission.microphone.request();

    final granted =
        cameraStatus.isGranted && microphoneStatus.isGranted;

    if (!granted) {
      state = state.copyWith(
        error: 'Camera and microphone permissions are required',
      );
    }

    return granted;
  }

  /// Start call as caller (creates offer)
  Future<bool> startCall({
    required String consultationId,
    required String roomName,
    bool audio = true,
    bool video = true,
  }) async {
    try {
      _logger.i('Starting call for consultation: $consultationId');
      state = state.copyWith(
        status: CallStatus.connecting,
        consultationId: consultationId,
        roomName: roomName,
        error: null,
      );

      // Check permissions
      final hasPermissions = await checkPermissions();
      if (!hasPermissions) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Permissions denied',
        );
        return false;
      }

      // Initialize local media
      final localStream = await _webrtcService.initializeLocalMedia(
        audio: audio,
        video: video,
      );

      if (localStream == null) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Failed to access camera/microphone',
        );
        return false;
      }

      state = state.copyWith(localStream: localStream);

      // Connect to signaling server
      await _signalingService.connect(consultationId);

      // Create peer connection
      final peerConnectionCreated = await _webrtcService.createPeerConnection();
      if (!peerConnectionCreated) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Failed to create peer connection',
        );
        return false;
      }

      // Create and send offer
      final offer = await _webrtcService.createOffer();
      if (offer == null) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Failed to create offer',
        );
        return false;
      }

      final sessionDescription = models.SessionDescription(
        type: offer.type!,
        sdp: offer.sdp!,
      );

      _signalingService.sendOffer(sessionDescription);

      _logger.i('Call started successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to start call: $e');
      state = state.copyWith(
        status: CallStatus.failed,
        error: e.toString(),
      );
      return false;
    }
  }

  /// Join call as callee (receives offer, sends answer)
  Future<bool> joinCall({
    required String consultationId,
    required String roomName,
    bool audio = true,
    bool video = true,
  }) async {
    try {
      _logger.i('Joining call for consultation: $consultationId');
      state = state.copyWith(
        status: CallStatus.connecting,
        consultationId: consultationId,
        roomName: roomName,
        error: null,
      );

      // Check permissions
      final hasPermissions = await checkPermissions();
      if (!hasPermissions) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Permissions denied',
        );
        return false;
      }

      // Initialize local media
      final localStream = await _webrtcService.initializeLocalMedia(
        audio: audio,
        video: video,
      );

      if (localStream == null) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Failed to access camera/microphone',
        );
        return false;
      }

      state = state.copyWith(localStream: localStream);

      // Connect to signaling server
      await _signalingService.connect(consultationId);

      // Create peer connection
      final peerConnectionCreated = await _webrtcService.createPeerConnection();
      if (!peerConnectionCreated) {
        state = state.copyWith(
          status: CallStatus.failed,
          error: 'Failed to create peer connection',
        );
        return false;
      }

      _logger.i('Joined call successfully, waiting for offer');
      return true;
    } catch (e) {
      _logger.e('Failed to join call: $e');
      state = state.copyWith(
        status: CallStatus.failed,
        error: e.toString(),
      );
      return false;
    }
  }

  /// Handle received offer
  Future<void> _handleOffer(models.SessionDescription offer) async {
    try {
      // Set remote description
      await _webrtcService.setRemoteDescription(offer);

      // Create answer
      final answer = await _webrtcService.createAnswer();
      if (answer == null) {
        throw Exception('Failed to create answer');
      }

      final sessionDescription = models.SessionDescription(
        type: answer.type!,
        sdp: answer.sdp!,
      );

      // Send answer
      _signalingService.sendAnswer(sessionDescription);
    } catch (e) {
      _logger.e('Failed to handle offer: $e');
      state = state.copyWith(
        status: CallStatus.failed,
        error: 'Failed to handle offer',
      );
    }
  }

  /// Handle received answer
  Future<void> _handleAnswer(models.SessionDescription answer) async {
    try {
      await _webrtcService.setRemoteDescription(answer);
    } catch (e) {
      _logger.e('Failed to handle answer: $e');
      state = state.copyWith(
        status: CallStatus.failed,
        error: 'Failed to handle answer',
      );
    }
  }

  /// Toggle audio mute
  Future<void> toggleAudio() async {
    final newMuted = !state.isAudioMuted;
    final success = await _webrtcService.toggleAudio(newMuted);

    if (success) {
      state = state.copyWith(isAudioMuted: newMuted);
    }
  }

  /// Toggle video
  Future<void> toggleVideo() async {
    final newMuted = !state.isVideoMuted;
    final success = await _webrtcService.toggleVideo(!newMuted);

    if (success) {
      state = state.copyWith(isVideoMuted: newMuted);
    }
  }

  /// Switch camera
  Future<void> switchCamera() async {
    final success = await _webrtcService.switchCamera();

    if (success) {
      state = state.copyWith(isFrontCamera: !state.isFrontCamera);
    }
  }

  /// Send chat message
  void sendChatMessage(String message) {
    _signalingService.sendChatMessage(message);
  }

  /// End call
  Future<void> endCall() async {
    _logger.i('Ending call');

    _stopCallDurationTimer();
    _stopStatsMonitoring();

    await _webrtcService.close();
    await _signalingService.disconnect();

    state = state.copyWith(status: CallStatus.ended);
  }

  /// Start call duration timer
  void _startCallDurationTimer() {
    final startTime = DateTime.now();
    state = state.copyWith(callStartTime: startTime);

    _durationTimer?.cancel();
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      final duration = DateTime.now().difference(startTime);
      state = state.copyWith(callDuration: duration);
    });
  }

  /// Stop call duration timer
  void _stopCallDurationTimer() {
    _durationTimer?.cancel();
    _durationTimer = null;
  }

  /// Start stats monitoring
  void _startStatsMonitoring() {
    _statsTimer?.cancel();
    _statsTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      final stats = await _webrtcService.getStats();
      final quality = _webrtcService.calculateConnectionQuality(stats);

      state = state.copyWith(
        stats: stats,
        connectionQuality: quality,
      );
    });
  }

  /// Stop stats monitoring
  void _stopStatsMonitoring() {
    _statsTimer?.cancel();
    _statsTimer = null;
  }

  @override
  void dispose() {
    _stopCallDurationTimer();
    _stopStatsMonitoring();
    _offerSubscription?.cancel();
    _answerSubscription?.cancel();
    _iceCandidateSubscription?.cancel();
    _connectionStateSubscription?.cancel();
    _webrtcService.dispose();
    _signalingService.dispose();
    super.dispose();
  }
}

/// WebRTC service provider
final webrtcServiceProvider = Provider<WebRTCService>((ref) {
  return WebRTCService();
});

/// Signaling service provider
final signalingServiceProvider = Provider<SignalingService>((ref) {
  final auth = ref.watch(authStateProvider);
  final service = SignalingService(
    baseUrl: 'http://localhost:8000', // TODO: Get from config
  );
  service.setAuthToken(auth.accessToken);
  return service;
});

/// Call provider
final callProvider = StateNotifierProvider<CallNotifier, CallState>((ref) {
  final webrtcService = ref.watch(webrtcServiceProvider);
  final signalingService = ref.watch(signalingServiceProvider);

  return CallNotifier(
    webrtcService: webrtcService,
    signalingService: signalingService,
  );
});
