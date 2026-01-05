import 'package:flutter_webrtc/flutter_webrtc.dart';

/// Call status enum
enum CallStatus {
  idle,
  connecting,
  ringing,
  connected,
  reconnecting,
  disconnected,
  ended,
  failed,
}

/// Connection quality enum
enum ConnectionQuality {
  excellent,
  good,
  fair,
  poor,
  disconnected,
}

/// Call state model
class CallState {
  final CallStatus status;
  final String? consultationId;
  final String? roomName;
  final RTCVideoRenderer? localRenderer;
  final RTCVideoRenderer? remoteRenderer;
  final MediaStream? localStream;
  final MediaStream? remoteStream;
  final bool isAudioMuted;
  final bool isVideoMuted;
  final bool isFrontCamera;
  final bool isScreenSharing;
  final ConnectionQuality connectionQuality;
  final Duration? callDuration;
  final DateTime? callStartTime;
  final String? error;
  final Map<String, dynamic>? stats;

  const CallState({
    this.status = CallStatus.idle,
    this.consultationId,
    this.roomName,
    this.localRenderer,
    this.remoteRenderer,
    this.localStream,
    this.remoteStream,
    this.isAudioMuted = false,
    this.isVideoMuted = false,
    this.isFrontCamera = true,
    this.isScreenSharing = false,
    this.connectionQuality = ConnectionQuality.excellent,
    this.callDuration,
    this.callStartTime,
    this.error,
    this.stats,
  });

  CallState copyWith({
    CallStatus? status,
    String? consultationId,
    String? roomName,
    RTCVideoRenderer? localRenderer,
    RTCVideoRenderer? remoteRenderer,
    MediaStream? localStream,
    MediaStream? remoteStream,
    bool? isAudioMuted,
    bool? isVideoMuted,
    bool? isFrontCamera,
    bool? isScreenSharing,
    ConnectionQuality? connectionQuality,
    Duration? callDuration,
    DateTime? callStartTime,
    String? error,
    Map<String, dynamic>? stats,
  }) {
    return CallState(
      status: status ?? this.status,
      consultationId: consultationId ?? this.consultationId,
      roomName: roomName ?? this.roomName,
      localRenderer: localRenderer ?? this.localRenderer,
      remoteRenderer: remoteRenderer ?? this.remoteRenderer,
      localStream: localStream ?? this.localStream,
      remoteStream: remoteStream ?? this.remoteStream,
      isAudioMuted: isAudioMuted ?? this.isAudioMuted,
      isVideoMuted: isVideoMuted ?? this.isVideoMuted,
      isFrontCamera: isFrontCamera ?? this.isFrontCamera,
      isScreenSharing: isScreenSharing ?? this.isScreenSharing,
      connectionQuality: connectionQuality ?? this.connectionQuality,
      callDuration: callDuration ?? this.callDuration,
      callStartTime: callStartTime ?? this.callStartTime,
      error: error,
      stats: stats ?? this.stats,
    );
  }

  bool get isInCall => status == CallStatus.connected;
  bool get isConnecting => status == CallStatus.connecting || status == CallStatus.ringing;
  bool get hasError => error != null;
  bool get hasRemoteStream => remoteStream != null;
  bool get hasLocalStream => localStream != null;

  String get statusMessage {
    switch (status) {
      case CallStatus.idle:
        return 'Ready';
      case CallStatus.connecting:
        return 'Connecting...';
      case CallStatus.ringing:
        return 'Ringing...';
      case CallStatus.connected:
        return 'Connected';
      case CallStatus.reconnecting:
        return 'Reconnecting...';
      case CallStatus.disconnected:
        return 'Disconnected';
      case CallStatus.ended:
        return 'Call Ended';
      case CallStatus.failed:
        return 'Call Failed';
    }
  }

  String get connectionQualityMessage {
    switch (connectionQuality) {
      case ConnectionQuality.excellent:
        return 'Excellent';
      case ConnectionQuality.good:
        return 'Good';
      case ConnectionQuality.fair:
        return 'Fair';
      case ConnectionQuality.poor:
        return 'Poor';
      case ConnectionQuality.disconnected:
        return 'Disconnected';
    }
  }
}

/// Chat message model for in-call chat
class ChatMessage {
  final String id;
  final String senderId;
  final String senderName;
  final String message;
  final DateTime timestamp;
  final bool isMe;

  const ChatMessage({
    required this.id,
    required this.senderId,
    required this.senderName,
    required this.message,
    required this.timestamp,
    required this.isMe,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json, String currentUserId) {
    return ChatMessage(
      id: json['id'] ?? '',
      senderId: json['sender_id'] ?? '',
      senderName: json['sender_name'] ?? 'Unknown',
      message: json['message'] ?? '',
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
      isMe: json['sender_id'] == currentUserId,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'sender_id': senderId,
      'sender_name': senderName,
      'message': message,
      'timestamp': timestamp.toIso8601String(),
    };
  }
}
