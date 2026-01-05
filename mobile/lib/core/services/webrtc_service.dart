import 'dart:async';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:logger/logger.dart';
import '../models/ice_candidate.dart' as models;
import '../models/call_state.dart';

/// Callback types
typedef OnIceCandidateCallback = void Function(RTCIceCandidate candidate);
typedef OnTrackCallback = void Function(MediaStream stream);
typedef OnConnectionStateChangeCallback = void Function(RTCPeerConnectionState state);

/// WebRTC service for managing peer connections
class WebRTCService {
  final Logger _logger = Logger();

  // WebRTC components
  RTCPeerConnection? _peerConnection;
  MediaStream? _localStream;
  MediaStream? _remoteStream;
  final List<RTCIceCandidate> _iceCandidateQueue = [];

  // Callbacks
  OnIceCandidateCallback? onIceCandidate;
  OnTrackCallback? onTrack;
  OnConnectionStateChangeCallback? onConnectionStateChange;

  // Configuration
  static const Map<String, dynamic> _iceServers = {
    'iceServers': [
      {'urls': 'stun:stun.l.google.com:19302'},
      {'urls': 'stun:stun1.l.google.com:19302'},
      {'urls': 'stun:stun2.l.google.com:19302'},
    ],
    'iceCandidatePoolSize': 10,
  };

  static const Map<String, dynamic> _mediaConstraints = {
    'audio': true,
    'video': {
      'facingMode': 'user',
      'width': {'ideal': 1280},
      'height': {'ideal': 720},
      'frameRate': {'ideal': 30},
    },
  };

  // Getters
  MediaStream? get localStream => _localStream;
  MediaStream? get remoteStream => _remoteStream;
  RTCPeerConnection? get peerConnection => _peerConnection;

  /// Initialize local media (camera and microphone)
  Future<MediaStream?> initializeLocalMedia({
    bool audio = true,
    bool video = true,
    bool frontCamera = true,
  }) async {
    try {
      _logger.i('Initializing local media (audio: $audio, video: $video)');

      final constraints = {
        'audio': audio,
        'video': video
            ? {
                'facingMode': frontCamera ? 'user' : 'environment',
                'width': {'ideal': 1280},
                'height': {'ideal': 720},
                'frameRate': {'ideal': 30},
              }
            : false,
      };

      _localStream = await navigator.mediaDevices.getUserMedia(constraints);
      _logger.i('Local media initialized: ${_localStream?.id}');

      return _localStream;
    } catch (e) {
      _logger.e('Failed to initialize local media: $e');
      return null;
    }
  }

  /// Create peer connection
  Future<bool> createPeerConnection() async {
    try {
      _logger.i('Creating peer connection');

      _peerConnection = await createPeerConnection(_iceServers);

      // Set up event handlers
      _peerConnection!.onIceCandidate = (candidate) {
        _logger.d('ICE candidate: ${candidate.candidate}');
        onIceCandidate?.call(candidate);
      };

      _peerConnection!.onTrack = (event) {
        _logger.i('Remote track received: ${event.track.kind}');
        if (event.streams.isNotEmpty) {
          _remoteStream = event.streams[0];
          onTrack?.call(_remoteStream!);
        }
      };

      _peerConnection!.onConnectionState = (state) {
        _logger.i('Connection state: $state');
        onConnectionStateChange?.call(state);

        // Process queued ICE candidates when connection is ready
        if (state == RTCPeerConnectionState.RTCPeerConnectionStateConnected) {
          _processQueuedIceCandidates();
        }
      };

      _peerConnection!.onIceConnectionState = (state) {
        _logger.d('ICE connection state: $state');
      };

      _peerConnection!.onIceGatheringState = (state) {
        _logger.d('ICE gathering state: $state');
      };

      // Add local stream tracks to peer connection
      if (_localStream != null) {
        _localStream!.getTracks().forEach((track) {
          _peerConnection!.addTrack(track, _localStream!);
        });
      }

      _logger.i('Peer connection created successfully');
      return true;
    } catch (e) {
      _logger.e('Failed to create peer connection: $e');
      return false;
    }
  }

  /// Create SDP offer
  Future<RTCSessionDescription?> createOffer() async {
    try {
      _logger.i('Creating SDP offer');

      final offer = await _peerConnection!.createOffer({
        'offerToReceiveAudio': true,
        'offerToReceiveVideo': true,
      });

      await _peerConnection!.setLocalDescription(offer);
      _logger.i('Local description set (offer)');

      return offer;
    } catch (e) {
      _logger.e('Failed to create offer: $e');
      return null;
    }
  }

  /// Create SDP answer
  Future<RTCSessionDescription?> createAnswer() async {
    try {
      _logger.i('Creating SDP answer');

      final answer = await _peerConnection!.createAnswer({
        'offerToReceiveAudio': true,
        'offerToReceiveVideo': true,
      });

      await _peerConnection!.setLocalDescription(answer);
      _logger.i('Local description set (answer)');

      return answer;
    } catch (e) {
      _logger.e('Failed to create answer: $e');
      return null;
    }
  }

  /// Set remote description
  Future<bool> setRemoteDescription(models.SessionDescription description) async {
    try {
      _logger.i('Setting remote description: ${description.type}');

      final rtcDescription = RTCSessionDescription(
        description.sdp,
        description.type,
      );

      await _peerConnection!.setRemoteDescription(rtcDescription);
      _logger.i('Remote description set');

      return true;
    } catch (e) {
      _logger.e('Failed to set remote description: $e');
      return false;
    }
  }

  /// Add ICE candidate
  Future<bool> addIceCandidate(models.IceCandidate candidate) async {
    try {
      final rtcCandidate = RTCIceCandidate(
        candidate.candidate,
        candidate.sdpMid ?? '',
        candidate.sdpMLineIndex ?? 0,
      );

      // Queue candidate if remote description is not set yet
      if (_peerConnection?.remoteDescription == null) {
        _logger.d('Queueing ICE candidate (no remote description yet)');
        _iceCandidateQueue.add(rtcCandidate);
        return true;
      }

      await _peerConnection!.addCandidate(rtcCandidate);
      _logger.d('ICE candidate added');

      return true;
    } catch (e) {
      _logger.e('Failed to add ICE candidate: $e');
      return false;
    }
  }

  /// Process queued ICE candidates
  Future<void> _processQueuedIceCandidates() async {
    if (_iceCandidateQueue.isEmpty) return;

    _logger.i('Processing ${_iceCandidateQueue.length} queued ICE candidates');

    for (final candidate in _iceCandidateQueue) {
      try {
        await _peerConnection!.addCandidate(candidate);
      } catch (e) {
        _logger.e('Failed to add queued ICE candidate: $e');
      }
    }

    _iceCandidateQueue.clear();
  }

  /// Toggle audio mute
  Future<bool> toggleAudio(bool muted) async {
    try {
      if (_localStream == null) return false;

      final audioTracks = _localStream!.getAudioTracks();
      for (var track in audioTracks) {
        await track.setEnabled(!muted);
      }

      _logger.i('Audio ${muted ? "muted" : "unmuted"}');
      return true;
    } catch (e) {
      _logger.e('Failed to toggle audio: $e');
      return false;
    }
  }

  /// Toggle video
  Future<bool> toggleVideo(bool enabled) async {
    try {
      if (_localStream == null) return false;

      final videoTracks = _localStream!.getVideoTracks();
      for (var track in videoTracks) {
        await track.setEnabled(enabled);
      }

      _logger.i('Video ${enabled ? "enabled" : "disabled"}');
      return true;
    } catch (e) {
      _logger.e('Failed to toggle video: $e');
      return false;
    }
  }

  /// Switch camera (front/back)
  Future<bool> switchCamera() async {
    try {
      if (_localStream == null) return false;

      final videoTracks = _localStream!.getVideoTracks();
      if (videoTracks.isEmpty) return false;

      await Helper.switchCamera(videoTracks[0]);
      _logger.i('Camera switched');

      return true;
    } catch (e) {
      _logger.e('Failed to switch camera: $e');
      return false;
    }
  }

  /// Get connection stats
  Future<Map<String, dynamic>?> getStats() async {
    try {
      if (_peerConnection == null) return null;

      final stats = await _peerConnection!.getStats();
      final statsMap = <String, dynamic>{};

      stats.forEach((key, value) {
        if (value.type == 'inbound-rtp' || value.type == 'outbound-rtp') {
          statsMap[key] = value.values;
        }
      });

      return statsMap;
    } catch (e) {
      _logger.e('Failed to get stats: $e');
      return null;
    }
  }

  /// Calculate connection quality from stats
  ConnectionQuality calculateConnectionQuality(Map<String, dynamic>? stats) {
    if (stats == null || stats.isEmpty) {
      return ConnectionQuality.disconnected;
    }

    // Simple quality calculation based on packet loss
    // In production, you'd want more sophisticated metrics
    try {
      var totalPacketsLost = 0;
      var totalPacketsReceived = 0;

      stats.forEach((key, value) {
        if (value['packetsLost'] != null) {
          totalPacketsLost += value['packetsLost'] as int;
        }
        if (value['packetsReceived'] != null) {
          totalPacketsReceived += value['packetsReceived'] as int;
        }
      });

      if (totalPacketsReceived == 0) {
        return ConnectionQuality.disconnected;
      }

      final lossRate = totalPacketsLost / totalPacketsReceived;

      if (lossRate < 0.02) return ConnectionQuality.excellent;
      if (lossRate < 0.05) return ConnectionQuality.good;
      if (lossRate < 0.10) return ConnectionQuality.fair;
      return ConnectionQuality.poor;
    } catch (e) {
      _logger.e('Failed to calculate quality: $e');
      return ConnectionQuality.fair;
    }
  }

  /// Close peer connection and cleanup
  Future<void> close() async {
    _logger.i('Closing WebRTC connection');

    // Stop all tracks
    _localStream?.getTracks().forEach((track) {
      track.stop();
    });

    _remoteStream?.getTracks().forEach((track) {
      track.stop();
    });

    // Close peer connection
    await _peerConnection?.close();

    // Dispose streams
    await _localStream?.dispose();
    await _remoteStream?.dispose();

    // Clear references
    _peerConnection = null;
    _localStream = null;
    _remoteStream = null;
    _iceCandidateQueue.clear();

    _logger.i('WebRTC connection closed');
  }

  /// Dispose service
  void dispose() {
    close();
  }
}
