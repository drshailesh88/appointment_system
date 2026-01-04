import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';

import '../api/api_client.dart';
import '../services/push_notification_service.dart';
import 'auth_provider.dart';

/// Notification state
class NotificationState {
  final bool isInitialized;
  final bool permissionGranted;
  final String? fcmToken;
  final int unreadCount;
  final List<RemoteMessage> recentMessages;
  final String? error;

  const NotificationState({
    this.isInitialized = false,
    this.permissionGranted = false,
    this.fcmToken,
    this.unreadCount = 0,
    this.recentMessages = const [],
    this.error,
  });

  NotificationState copyWith({
    bool? isInitialized,
    bool? permissionGranted,
    String? fcmToken,
    int? unreadCount,
    List<RemoteMessage>? recentMessages,
    String? error,
  }) {
    return NotificationState(
      isInitialized: isInitialized ?? this.isInitialized,
      permissionGranted: permissionGranted ?? this.permissionGranted,
      fcmToken: fcmToken ?? this.fcmToken,
      unreadCount: unreadCount ?? this.unreadCount,
      recentMessages: recentMessages ?? this.recentMessages,
      error: error ?? this.error,
    );
  }
}

/// Push notification service provider
final pushNotificationServiceProvider = Provider<PushNotificationService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return PushNotificationService(apiClient);
});

/// Notification state notifier
class NotificationNotifier extends StateNotifier<NotificationState> {
  final PushNotificationService _service;
  final Ref _ref;
  final Logger _logger = Logger();

  NotificationNotifier(this._service, this._ref) : super(const NotificationState()) {
    _initialize();
  }

  /// Initialize push notifications
  Future<void> _initialize() async {
    try {
      _logger.i('Initializing push notifications...');

      // Initialize the service
      await _service.initialize();

      // Listen to messages
      _service.onMessage.listen(_handleMessage);

      // Listen to token refresh
      _service.onTokenRefresh.listen(_handleTokenRefresh);

      // Update state
      state = state.copyWith(
        isInitialized: true,
        permissionGranted: _service.isInitialized,
        fcmToken: _service.fcmToken,
      );

      _logger.i('Push notifications initialized successfully');

      // Auto-register if user is authenticated
      final authState = _ref.read(authProvider);
      if (authState.isAuthenticated) {
        await registerDevice();
      }
    } catch (e, stackTrace) {
      _logger.e('Failed to initialize push notifications', error: e, stackTrace: stackTrace);
      state = state.copyWith(
        error: 'Failed to initialize notifications: $e',
      );
    }
  }

  /// Request notification permissions
  Future<bool> requestPermissions() async {
    try {
      final granted = await _service.requestPermissions();
      state = state.copyWith(permissionGranted: granted);
      return granted;
    } catch (e) {
      _logger.e('Failed to request permissions', error: e);
      state = state.copyWith(error: 'Failed to request permissions: $e');
      return false;
    }
  }

  /// Register device with backend
  ///
  /// Call this after successful login to enable push notifications.
  Future<void> registerDevice({String? deviceName}) async {
    if (!state.isInitialized) {
      _logger.w('Cannot register device: service not initialized');
      return;
    }

    try {
      final success = await _service.registerWithBackend(deviceName: deviceName);
      if (success) {
        _logger.i('Device registered successfully');
        // Auto-subscribe to clinic topic if user has clinic
        final authState = _ref.read(authProvider);
        final clinicId = authState.user?.clinicId;
        if (clinicId != null) {
          await subscribeToClinicTopic(clinicId);
        }
      } else {
        _logger.w('Failed to register device with backend');
      }
    } catch (e) {
      _logger.e('Error registering device', error: e);
      state = state.copyWith(error: 'Failed to register device: $e');
    }
  }

  /// Unregister device from backend
  ///
  /// Call this on logout to stop receiving notifications.
  Future<void> unregisterDevice() async {
    if (!state.isInitialized) return;

    try {
      await _service.unregisterFromBackend();
      _logger.i('Device unregistered successfully');

      // Unsubscribe from clinic topic
      final authState = _ref.read(authProvider);
      final clinicId = authState.user?.clinicId;
      if (clinicId != null) {
        await unsubscribeFromClinicTopic(clinicId);
      }
    } catch (e) {
      _logger.e('Error unregistering device', error: e);
    }
  }

  /// Subscribe to clinic topic
  Future<void> subscribeToClinicTopic(String clinicId) async {
    try {
      final topic = 'clinic_$clinicId';
      await _service.subscribeToTopic(topic);
      _logger.i('Subscribed to clinic topic: $topic');
    } catch (e) {
      _logger.e('Failed to subscribe to clinic topic', error: e);
    }
  }

  /// Unsubscribe from clinic topic
  Future<void> unsubscribeFromClinicTopic(String clinicId) async {
    try {
      final topic = 'clinic_$clinicId';
      await _service.unsubscribeFromTopic(topic);
      _logger.i('Unsubscribed from clinic topic: $topic');
    } catch (e) {
      _logger.e('Failed to unsubscribe from clinic topic', error: e);
    }
  }

  /// Handle incoming message
  void _handleMessage(RemoteMessage message) {
    _logger.i('Received message: ${message.messageId}');

    // Add to recent messages
    final recentMessages = [message, ...state.recentMessages].take(10).toList();

    // Increment unread count
    final unreadCount = state.unreadCount + 1;

    state = state.copyWith(
      recentMessages: recentMessages,
      unreadCount: unreadCount,
    );

    // Optionally trigger a refresh of relevant data
    _handleNotificationAction(message);
  }

  /// Handle token refresh
  void _handleTokenRefresh(String token) {
    _logger.i('Token refreshed: $token');
    state = state.copyWith(fcmToken: token);
  }

  /// Handle notification actions (refresh data, navigate, etc.)
  void _handleNotificationAction(RemoteMessage message) {
    final notificationType = NotificationType.fromString(message.data['type']);

    switch (notificationType) {
      case NotificationType.appointmentReminder:
      case NotificationType.appointmentConfirmed:
      case NotificationType.appointmentCancelled:
      case NotificationType.appointmentRescheduled:
        // Refresh appointments
        _logger.i('Refreshing appointments due to notification');
        _ref.invalidate(appointmentsProvider);
        break;

      case NotificationType.slotOffer:
        // Refresh waitlist
        _logger.i('Refreshing waitlist due to slot offer');
        _ref.invalidate(waitlistProvider);
        break;

      case NotificationType.paymentReceived:
      case NotificationType.paymentPending:
        // Refresh payments/invoices
        _logger.i('Refreshing payments due to notification');
        // _ref.invalidate(paymentsProvider);
        break;

      case NotificationType.waitlistPositionUpdate:
        // Refresh waitlist position
        _logger.i('Refreshing waitlist position');
        _ref.invalidate(waitlistProvider);
        break;

      default:
        _logger.i('No specific action for notification type: $notificationType');
    }
  }

  /// Mark notification as read
  void markAsRead(String messageId) {
    final recentMessages = state.recentMessages
        .where((msg) => msg.messageId != messageId)
        .toList();

    state = state.copyWith(
      recentMessages: recentMessages,
      unreadCount: state.unreadCount > 0 ? state.unreadCount - 1 : 0,
    );
  }

  /// Mark all notifications as read
  void markAllAsRead() {
    state = state.copyWith(
      unreadCount: 0,
      recentMessages: [],
    );
  }

  /// Clear all notifications
  Future<void> clearAllNotifications() async {
    await _service.clearAllNotifications();
    state = state.copyWith(
      unreadCount: 0,
      recentMessages: [],
    );
  }

  /// Get recent messages
  List<RemoteMessage> getRecentMessages() {
    return state.recentMessages;
  }

  /// Check if notifications are enabled
  bool areNotificationsEnabled() {
    return state.isInitialized && state.permissionGranted;
  }
}

/// Notification provider
final notificationProvider = StateNotifierProvider<NotificationNotifier, NotificationState>((ref) {
  final service = ref.watch(pushNotificationServiceProvider);
  return NotificationNotifier(service, ref);
});

/// Provider for checking if notifications are enabled
final notificationsEnabledProvider = Provider<bool>((ref) {
  final notificationState = ref.watch(notificationProvider);
  return notificationState.isInitialized && notificationState.permissionGranted;
});

/// Provider for unread count
final unreadNotificationCountProvider = Provider<int>((ref) {
  final notificationState = ref.watch(notificationProvider);
  return notificationState.unreadCount;
});

/// Provider for recent messages
final recentMessagesProvider = Provider<List<RemoteMessage>>((ref) {
  final notificationState = ref.watch(notificationProvider);
  return notificationState.recentMessages;
});

// Placeholder providers (replace with actual imports)
// These should be imported from their respective provider files
final appointmentsProvider = Provider((ref) => null);
final waitlistProvider = Provider((ref) => null);
