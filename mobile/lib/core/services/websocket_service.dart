import 'dart:async';
import 'dart:convert';
import 'package:logger/logger.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

/// WebSocket connection state
enum ConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

/// WebSocket event types
enum WebSocketEventType {
  appointmentCreated,
  appointmentUpdated,
  appointmentCancelled,
  waitlistAdded,
  waitlistUpdated,
  waitlistOfferSent,
  notification,
  heartbeat,
  unknown,
}

/// WebSocket event model
class WebSocketEvent {
  final WebSocketEventType type;
  final Map<String, dynamic> data;
  final DateTime timestamp;

  WebSocketEvent({
    required this.type,
    required this.data,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory WebSocketEvent.fromJson(Map<String, dynamic> json) {
    return WebSocketEvent(
      type: _parseEventType(json['type'] as String?),
      data: json['data'] as Map<String, dynamic>? ?? {},
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
    );
  }

  static WebSocketEventType _parseEventType(String? type) {
    switch (type) {
      case 'appointment.created':
        return WebSocketEventType.appointmentCreated;
      case 'appointment.updated':
        return WebSocketEventType.appointmentUpdated;
      case 'appointment.cancelled':
        return WebSocketEventType.appointmentCancelled;
      case 'waitlist.added':
        return WebSocketEventType.waitlistAdded;
      case 'waitlist.updated':
        return WebSocketEventType.waitlistUpdated;
      case 'waitlist.offer_sent':
        return WebSocketEventType.waitlistOfferSent;
      case 'notification':
        return WebSocketEventType.notification;
      case 'heartbeat':
      case 'ping':
      case 'pong':
        return WebSocketEventType.heartbeat;
      default:
        return WebSocketEventType.unknown;
    }
  }
}

/// WebSocket service for real-time updates
class WebSocketService {
  final String baseUrl;
  final Logger _logger = Logger();

  WebSocketChannel? _channel;
  String? _authToken;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 10;
  static const Duration _baseReconnectDelay = Duration(seconds: 2);
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _connectionTimeout = Duration(seconds: 10);

  // Stream controllers
  final _connectionStateController = StreamController<ConnectionState>.broadcast();
  final _eventController = StreamController<WebSocketEvent>.broadcast();
  final _appointmentEventController = StreamController<WebSocketEvent>.broadcast();
  final _waitlistEventController = StreamController<WebSocketEvent>.broadcast();
  final _notificationEventController = StreamController<WebSocketEvent>.broadcast();

  ConnectionState _currentState = ConnectionState.disconnected;

  WebSocketService({required this.baseUrl});

  // Public getters
  ConnectionState get connectionState => _currentState;
  Stream<ConnectionState> get connectionStateStream => _connectionStateController.stream;
  Stream<WebSocketEvent> get eventStream => _eventController.stream;
  Stream<WebSocketEvent> get appointmentEventStream => _appointmentEventController.stream;
  Stream<WebSocketEvent> get waitlistEventStream => _waitlistEventController.stream;
  Stream<WebSocketEvent> get notificationEventStream => _notificationEventController.stream;

  /// Set authentication token for WebSocket connection
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Connect to WebSocket server
  Future<void> connect() async {
    if (_currentState == ConnectionState.connected ||
        _currentState == ConnectionState.connecting) {
      _logger.i('WebSocket already connected or connecting');
      return;
    }

    _updateConnectionState(ConnectionState.connecting);
    _logger.i('Connecting to WebSocket: $baseUrl');

    try {
      // Convert HTTP base URL to WebSocket URL
      final wsUrl = _buildWebSocketUrl();
      _logger.d('WebSocket URL: $wsUrl');

      // Create WebSocket connection with timeout
      final uri = Uri.parse(wsUrl);
      _channel = WebSocketChannel.connect(
        uri,
        protocols: _authToken != null ? ['Bearer.$_authToken'] : null,
      );

      // Wait for connection with timeout
      await _channel!.ready.timeout(
        _connectionTimeout,
        onTimeout: () {
          throw TimeoutException('WebSocket connection timeout');
        },
      );

      _updateConnectionState(ConnectionState.connected);
      _reconnectAttempts = 0;
      _logger.i('WebSocket connected successfully');

      // Listen to messages
      _listenToMessages();

      // Start heartbeat
      _startHeartbeat();
    } catch (e) {
      _logger.e('WebSocket connection error: $e');
      _updateConnectionState(ConnectionState.error);
      _scheduleReconnect();
    }
  }

  /// Disconnect from WebSocket server
  Future<void> disconnect() async {
    _logger.i('Disconnecting WebSocket');
    _cancelReconnect();
    _stopHeartbeat();

    await _channel?.sink.close(status.normalClosure);
    _channel = null;

    _updateConnectionState(ConnectionState.disconnected);
  }

  /// Send message to WebSocket server
  void send(Map<String, dynamic> message) {
    if (_currentState != ConnectionState.connected) {
      _logger.w('Cannot send message: WebSocket not connected');
      return;
    }

    try {
      final jsonMessage = jsonEncode(message);
      _channel?.sink.add(jsonMessage);
      _logger.d('Sent message: $jsonMessage');
    } catch (e) {
      _logger.e('Error sending message: $e');
    }
  }

  /// Build WebSocket URL from HTTP base URL
  String _buildWebSocketUrl() {
    // Convert http://host:port/api/v1 to ws://host:port/api/v1/ws
    // Convert https://host/api/v1 to wss://host/api/v1/ws

    final httpUrl = baseUrl.replaceAll('/api/v1', '').replaceAll(RegExp(r'/$'), '');
    final wsProtocol = httpUrl.startsWith('https') ? 'wss' : 'ws';
    final wsBase = httpUrl.replaceFirst(RegExp(r'^https?'), wsProtocol);

    final wsUrl = '$wsBase/api/v1/ws';

    // Add auth token as query parameter if available
    if (_authToken != null) {
      return '$wsUrl?token=$_authToken';
    }

    return wsUrl;
  }

  /// Listen to WebSocket messages
  void _listenToMessages() {
    _channel?.stream.listen(
      (message) {
        try {
          final data = jsonDecode(message as String) as Map<String, dynamic>;
          final event = WebSocketEvent.fromJson(data);

          _logger.d('Received event: ${event.type}');

          // Broadcast to main event stream
          _eventController.add(event);

          // Route to specific streams
          _routeEvent(event);
        } catch (e) {
          _logger.e('Error parsing WebSocket message: $e');
        }
      },
      onError: (error) {
        _logger.e('WebSocket stream error: $error');
        _updateConnectionState(ConnectionState.error);
        _scheduleReconnect();
      },
      onDone: () {
        _logger.w('WebSocket stream closed');
        if (_currentState == ConnectionState.connected) {
          _updateConnectionState(ConnectionState.disconnected);
          _scheduleReconnect();
        }
      },
      cancelOnError: false,
    );
  }

  /// Route events to specific streams
  void _routeEvent(WebSocketEvent event) {
    switch (event.type) {
      case WebSocketEventType.appointmentCreated:
      case WebSocketEventType.appointmentUpdated:
      case WebSocketEventType.appointmentCancelled:
        _appointmentEventController.add(event);
        break;

      case WebSocketEventType.waitlistAdded:
      case WebSocketEventType.waitlistUpdated:
      case WebSocketEventType.waitlistOfferSent:
        _waitlistEventController.add(event);
        break;

      case WebSocketEventType.notification:
        _notificationEventController.add(event);
        break;

      case WebSocketEventType.heartbeat:
        // Handle heartbeat/pong
        _logger.d('Heartbeat received');
        break;

      case WebSocketEventType.unknown:
        _logger.w('Unknown event type: ${event.data}');
        break;
    }
  }

  /// Update connection state
  void _updateConnectionState(ConnectionState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      _connectionStateController.add(newState);
      _logger.i('Connection state changed: $newState');
    }
  }

  /// Start heartbeat to keep connection alive
  void _startHeartbeat() {
    _stopHeartbeat();

    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (_currentState == ConnectionState.connected) {
        send({'type': 'ping', 'timestamp': DateTime.now().toIso8601String()});
      }
    });
  }

  /// Stop heartbeat timer
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// Schedule reconnection with exponential backoff
  void _scheduleReconnect() {
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      _logger.e('Max reconnection attempts reached');
      _updateConnectionState(ConnectionState.error);
      return;
    }

    _cancelReconnect();
    _updateConnectionState(ConnectionState.reconnecting);

    // Exponential backoff: 2s, 4s, 8s, 16s, 32s, etc. (capped at 60s)
    final delaySeconds = (_baseReconnectDelay.inSeconds * (1 << _reconnectAttempts)).clamp(2, 60);
    final delay = Duration(seconds: delaySeconds);

    _reconnectAttempts++;
    _logger.i('Scheduling reconnect attempt $_reconnectAttempts in ${delay.inSeconds}s');

    _reconnectTimer = Timer(delay, () {
      _logger.i('Attempting to reconnect...');
      connect();
    });
  }

  /// Cancel scheduled reconnection
  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  /// Reset reconnection attempts (call when connection is successful)
  void resetReconnectAttempts() {
    _reconnectAttempts = 0;
  }

  /// Dispose resources
  void dispose() {
    _logger.i('Disposing WebSocket service');
    _cancelReconnect();
    _stopHeartbeat();

    _channel?.sink.close(status.normalClosure);
    _channel = null;

    _connectionStateController.close();
    _eventController.close();
    _appointmentEventController.close();
    _waitlistEventController.close();
    _notificationEventController.close();
  }
}
