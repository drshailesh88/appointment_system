import 'dart:async';
import 'dart:convert';
import 'package:logger/logger.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import '../models/ice_candidate.dart';

/// Signaling message types
enum SignalingMessageType {
  offer,
  answer,
  iceCandidate,
  callStarted,
  callEnded,
  userJoined,
  userLeft,
  error,
  chatMessage,
  unknown,
}

/// Signaling message model
class SignalingMessage {
  final SignalingMessageType type;
  final Map<String, dynamic> data;
  final DateTime timestamp;

  SignalingMessage({
    required this.type,
    required this.data,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory SignalingMessage.fromJson(Map<String, dynamic> json) {
    return SignalingMessage(
      type: _parseMessageType(json['type'] as String?),
      data: json['data'] as Map<String, dynamic>? ?? {},
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type.name,
      'data': data,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  static SignalingMessageType _parseMessageType(String? type) {
    switch (type) {
      case 'offer':
        return SignalingMessageType.offer;
      case 'answer':
        return SignalingMessageType.answer;
      case 'ice_candidate':
      case 'iceCandidate':
        return SignalingMessageType.iceCandidate;
      case 'call_started':
      case 'callStarted':
        return SignalingMessageType.callStarted;
      case 'call_ended':
      case 'callEnded':
        return SignalingMessageType.callEnded;
      case 'user_joined':
      case 'userJoined':
        return SignalingMessageType.userJoined;
      case 'user_left':
      case 'userLeft':
        return SignalingMessageType.userLeft;
      case 'error':
        return SignalingMessageType.error;
      case 'chat_message':
      case 'chatMessage':
        return SignalingMessageType.chatMessage;
      default:
        return SignalingMessageType.unknown;
    }
  }
}

/// Connection state
enum SignalingConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

/// Signaling service for WebRTC signaling via WebSocket
class SignalingService {
  final String baseUrl;
  final Logger _logger = Logger();

  WebSocketChannel? _channel;
  String? _authToken;
  String? _consultationId;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;

  static const int _maxReconnectAttempts = 5;
  static const Duration _baseReconnectDelay = Duration(seconds: 2);
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _connectionTimeout = Duration(seconds: 10);

  // Stream controllers
  final _connectionStateController = StreamController<SignalingConnectionState>.broadcast();
  final _messageController = StreamController<SignalingMessage>.broadcast();
  final _offerController = StreamController<SessionDescription>.broadcast();
  final _answerController = StreamController<SessionDescription>.broadcast();
  final _iceCandidateController = StreamController<IceCandidate>.broadcast();
  final _chatMessageController = StreamController<Map<String, dynamic>>.broadcast();

  SignalingConnectionState _currentState = SignalingConnectionState.disconnected;

  SignalingService({required this.baseUrl});

  // Public getters
  SignalingConnectionState get connectionState => _currentState;
  Stream<SignalingConnectionState> get connectionStateStream =>
      _connectionStateController.stream;
  Stream<SignalingMessage> get messageStream => _messageController.stream;
  Stream<SessionDescription> get offerStream => _offerController.stream;
  Stream<SessionDescription> get answerStream => _answerController.stream;
  Stream<IceCandidate> get iceCandidateStream => _iceCandidateController.stream;
  Stream<Map<String, dynamic>> get chatMessageStream => _chatMessageController.stream;

  /// Set authentication token
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Connect to signaling server for a consultation
  Future<void> connect(String consultationId) async {
    if (_currentState == SignalingConnectionState.connected ||
        _currentState == SignalingConnectionState.connecting) {
      _logger.i('Signaling already connected or connecting');
      return;
    }

    _consultationId = consultationId;
    _updateConnectionState(SignalingConnectionState.connecting);
    _logger.i('Connecting to signaling server for consultation: $consultationId');

    try {
      final wsUrl = _buildWebSocketUrl(consultationId);
      _logger.d('WebSocket URL: $wsUrl');

      final uri = Uri.parse(wsUrl);
      _channel = WebSocketChannel.connect(uri);

      // Wait for connection with timeout
      await _channel!.ready.timeout(
        _connectionTimeout,
        onTimeout: () {
          throw TimeoutException('Signaling connection timeout');
        },
      );

      _updateConnectionState(SignalingConnectionState.connected);
      _reconnectAttempts = 0;
      _logger.i('Signaling connected successfully');

      // Listen to messages
      _listenToMessages();

      // Start heartbeat
      _startHeartbeat();
    } catch (e) {
      _logger.e('Signaling connection error: $e');
      _updateConnectionState(SignalingConnectionState.error);
      _scheduleReconnect();
    }
  }

  /// Disconnect from signaling server
  Future<void> disconnect() async {
    _logger.i('Disconnecting signaling');
    _cancelReconnect();
    _stopHeartbeat();

    await _channel?.sink.close(status.normalClosure);
    _channel = null;
    _consultationId = null;

    _updateConnectionState(SignalingConnectionState.disconnected);
  }

  /// Send offer
  void sendOffer(SessionDescription offer) {
    _send({
      'type': 'offer',
      'data': offer.toJson(),
    });
  }

  /// Send answer
  void sendAnswer(SessionDescription answer) {
    _send({
      'type': 'answer',
      'data': answer.toJson(),
    });
  }

  /// Send ICE candidate
  void sendIceCandidate(IceCandidate candidate) {
    _send({
      'type': 'ice_candidate',
      'data': candidate.toJson(),
    });
  }

  /// Send chat message
  void sendChatMessage(String message) {
    _send({
      'type': 'chat_message',
      'data': {'message': message},
    });
  }

  /// Send generic message
  void _send(Map<String, dynamic> message) {
    if (_currentState != SignalingConnectionState.connected) {
      _logger.w('Cannot send message: not connected');
      return;
    }

    try {
      message['timestamp'] = DateTime.now().toIso8601String();
      final jsonMessage = jsonEncode(message);
      _channel?.sink.add(jsonMessage);
      _logger.d('Sent message: ${message['type']}');
    } catch (e) {
      _logger.e('Error sending message: $e');
    }
  }

  /// Build WebSocket URL
  String _buildWebSocketUrl(String consultationId) {
    // Convert http://host:port to ws://host:port
    // Convert https://host to wss://host
    final httpUrl = baseUrl.replaceAll(RegExp(r'/$'), '');
    final wsProtocol = httpUrl.startsWith('https') ? 'wss' : 'ws';
    final wsBase = httpUrl.replaceFirst(RegExp(r'^https?'), wsProtocol);

    var wsUrl = '$wsBase/api/v1/ws/telemedicine/$consultationId';

    // Add auth token as query parameter if available
    if (_authToken != null) {
      wsUrl += '?token=$_authToken';
    }

    return wsUrl;
  }

  /// Listen to WebSocket messages
  void _listenToMessages() {
    _channel?.stream.listen(
      (message) {
        try {
          final data = jsonDecode(message as String) as Map<String, dynamic>;
          final signalingMessage = SignalingMessage.fromJson(data);

          _logger.d('Received message: ${signalingMessage.type}');

          // Broadcast to main stream
          _messageController.add(signalingMessage);

          // Route to specific streams
          _routeMessage(signalingMessage);
        } catch (e) {
          _logger.e('Error parsing signaling message: $e');
        }
      },
      onError: (error) {
        _logger.e('Signaling stream error: $error');
        _updateConnectionState(SignalingConnectionState.error);
        _scheduleReconnect();
      },
      onDone: () {
        _logger.w('Signaling stream closed');
        if (_currentState == SignalingConnectionState.connected) {
          _updateConnectionState(SignalingConnectionState.disconnected);
          _scheduleReconnect();
        }
      },
      cancelOnError: false,
    );
  }

  /// Route messages to specific streams
  void _routeMessage(SignalingMessage message) {
    switch (message.type) {
      case SignalingMessageType.offer:
        final offer = SessionDescription.fromJson(message.data);
        _offerController.add(offer);
        break;

      case SignalingMessageType.answer:
        final answer = SessionDescription.fromJson(message.data);
        _answerController.add(answer);
        break;

      case SignalingMessageType.iceCandidate:
        final candidate = IceCandidate.fromJson(message.data);
        _iceCandidateController.add(candidate);
        break;

      case SignalingMessageType.chatMessage:
        _chatMessageController.add(message.data);
        break;

      case SignalingMessageType.callStarted:
      case SignalingMessageType.callEnded:
      case SignalingMessageType.userJoined:
      case SignalingMessageType.userLeft:
        // These are handled by listening to the main message stream
        break;

      case SignalingMessageType.error:
        _logger.e('Signaling error: ${message.data}');
        break;

      case SignalingMessageType.unknown:
        _logger.w('Unknown message type: ${message.data}');
        break;
    }
  }

  /// Update connection state
  void _updateConnectionState(SignalingConnectionState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      _connectionStateController.add(newState);
      _logger.i('Signaling state changed: $newState');
    }
  }

  /// Start heartbeat
  void _startHeartbeat() {
    _stopHeartbeat();

    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (_currentState == SignalingConnectionState.connected) {
        _send({
          'type': 'ping',
          'data': {},
        });
      }
    });
  }

  /// Stop heartbeat
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// Schedule reconnection
  void _scheduleReconnect() {
    if (_consultationId == null) return;
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      _logger.e('Max reconnection attempts reached');
      _updateConnectionState(SignalingConnectionState.error);
      return;
    }

    _cancelReconnect();
    _updateConnectionState(SignalingConnectionState.reconnecting);

    final delaySeconds = (_baseReconnectDelay.inSeconds * (1 << _reconnectAttempts))
        .clamp(2, 30);
    final delay = Duration(seconds: delaySeconds);

    _reconnectAttempts++;
    _logger.i('Scheduling reconnect attempt $_reconnectAttempts in ${delay.inSeconds}s');

    _reconnectTimer = Timer(delay, () {
      _logger.i('Attempting to reconnect...');
      connect(_consultationId!);
    });
  }

  /// Cancel reconnection
  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  /// Dispose service
  void dispose() {
    _logger.i('Disposing signaling service');
    _cancelReconnect();
    _stopHeartbeat();

    _channel?.sink.close(status.normalClosure);
    _channel = null;

    _connectionStateController.close();
    _messageController.close();
    _offerController.close();
    _answerController.close();
    _iceCandidateController.close();
    _chatMessageController.close();
  }
}
