import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/app_config.dart';
import '../services/websocket_service.dart';
import 'auth_provider.dart';

/// WebSocket service provider
final webSocketServiceProvider = Provider<WebSocketService>((ref) {
  final service = WebSocketService(baseUrl: AppConfig.baseUrl);

  // Listen to auth state and connect/disconnect accordingly
  ref.listen<AuthState>(
    authStateProvider,
    (previous, next) {
      if (next.isAuthenticated && next.accessToken != null) {
        // User logged in - set token and connect
        service.setAuthToken(next.accessToken);
        service.connect();
      } else if (!next.isAuthenticated && previous?.isAuthenticated == true) {
        // User logged out - disconnect
        service.disconnect();
      }
    },
    fireImmediately: true,
  );

  // Cleanup on dispose
  ref.onDispose(() {
    service.dispose();
  });

  return service;
});

/// Connection state provider
final connectionStateProvider = StreamProvider<ConnectionState>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.connectionStateStream;
});

/// Current connection state value provider
final currentConnectionStateProvider = Provider<ConnectionState>((ref) {
  final asyncState = ref.watch(connectionStateProvider);
  return asyncState.when(
    data: (state) => state,
    loading: () => ConnectionState.disconnected,
    error: (_, __) => ConnectionState.error,
  );
});

/// All WebSocket events stream provider
final webSocketEventsProvider = StreamProvider<WebSocketEvent>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.eventStream;
});

/// Appointment events stream provider
final appointmentEventsProvider = StreamProvider<WebSocketEvent>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.appointmentEventStream;
});

/// Waitlist events stream provider
final waitlistEventsProvider = StreamProvider<WebSocketEvent>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.waitlistEventStream;
});

/// Notification events stream provider
final notificationEventsProvider = StreamProvider<WebSocketEvent>((ref) {
  final service = ref.watch(webSocketServiceProvider);
  return service.notificationEventStream;
});

/// Real-time connection manager
/// Handles automatic reconnection on app lifecycle changes
class RealtimeConnectionManager {
  final Ref ref;
  final WebSocketService _service;

  RealtimeConnectionManager(this.ref) : _service = ref.read(webSocketServiceProvider);

  /// Handle app lifecycle state changes
  void handleAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        // App resumed - reconnect if authenticated
        final authState = ref.read(authStateProvider);
        if (authState.isAuthenticated &&
            _service.connectionState != ConnectionState.connected) {
          _service.connect();
        }
        break;

      case AppLifecycleState.paused:
        // App paused - keep connection alive for background notifications
        // Don't disconnect to allow receiving notifications
        break;

      case AppLifecycleState.inactive:
      case AppLifecycleState.detached:
      case AppLifecycleState.hidden:
        // App about to close - disconnect
        _service.disconnect();
        break;
    }
  }

  /// Manually trigger reconnection
  Future<void> reconnect() async {
    await _service.disconnect();
    await Future.delayed(const Duration(milliseconds: 500));
    await _service.connect();
  }

  /// Check connection and reconnect if needed
  Future<void> ensureConnected() async {
    final authState = ref.read(authStateProvider);
    if (authState.isAuthenticated &&
        _service.connectionState != ConnectionState.connected) {
      await _service.connect();
    }
  }
}

/// Real-time connection manager provider
final realtimeConnectionManagerProvider = Provider<RealtimeConnectionManager>((ref) {
  return RealtimeConnectionManager(ref);
});

/// Helper to check if WebSocket is connected
final isWebSocketConnectedProvider = Provider<bool>((ref) {
  final state = ref.watch(currentConnectionStateProvider);
  return state == ConnectionState.connected;
});

/// Connection quality indicator provider
/// Returns a simple quality metric based on connection state
final connectionQualityProvider = Provider<ConnectionQuality>((ref) {
  final state = ref.watch(currentConnectionStateProvider);

  switch (state) {
    case ConnectionState.connected:
      return ConnectionQuality.good;
    case ConnectionState.reconnecting:
      return ConnectionQuality.degraded;
    case ConnectionState.connecting:
      return ConnectionQuality.connecting;
    case ConnectionState.disconnected:
    case ConnectionState.error:
      return ConnectionQuality.poor;
  }
});

/// Connection quality enum
enum ConnectionQuality {
  good,
  degraded,
  connecting,
  poor;

  String get displayName {
    switch (this) {
      case ConnectionQuality.good:
        return 'Connected';
      case ConnectionQuality.degraded:
        return 'Reconnecting...';
      case ConnectionQuality.connecting:
        return 'Connecting...';
      case ConnectionQuality.poor:
        return 'Disconnected';
    }
  }

  bool get isConnected => this == ConnectionQuality.good;
}
