import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:logger/logger.dart';

import '../api/api_client.dart';

/// Background message handler - must be top-level function
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  Logger().i('Background message received: ${message.messageId}');
  // Process notification data if needed
}

/// Notification types from backend
enum NotificationType {
  appointmentReminder('appointment_reminder'),
  appointmentConfirmed('appointment_confirmed'),
  appointmentCancelled('appointment_cancelled'),
  appointmentRescheduled('appointment_rescheduled'),
  slotOffer('slot_offer'),
  paymentReceived('payment_received'),
  paymentPending('payment_pending'),
  waitlistPositionUpdate('waitlist_position_update'),
  generalAnnouncement('general_announcement');

  const NotificationType(this.value);
  final String value;

  static NotificationType? fromString(String? value) {
    if (value == null) return null;
    return NotificationType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => NotificationType.generalAnnouncement,
    );
  }
}

/// Push Notification Service using Firebase Cloud Messaging
///
/// Features:
/// - Initialize Firebase and request permissions
/// - Get and register FCM token with backend
/// - Handle foreground notifications
/// - Handle background notifications
/// - Handle notification tap navigation
/// - Auto-register on authentication
class PushNotificationService {
  final ApiClient _apiClient;
  final Logger _logger = Logger();
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  FirebaseMessaging? _messaging;
  String? _fcmToken;
  bool _isInitialized = false;

  // Stream controllers for notification events
  final _messageStreamController = StreamController<RemoteMessage>.broadcast();
  final _tokenRefreshController = StreamController<String>.broadcast();

  /// Stream of received messages (foreground and on-tap)
  Stream<RemoteMessage> get onMessage => _messageStreamController.stream;

  /// Stream of token refresh events
  Stream<String> get onTokenRefresh => _tokenRefreshController.stream;

  /// Current FCM token
  String? get fcmToken => _fcmToken;

  /// Whether the service is initialized
  bool get isInitialized => _isInitialized;

  PushNotificationService(this._apiClient);

  /// Initialize Firebase and FCM
  ///
  /// Call this during app startup, before any authentication.
  Future<void> initialize() async {
    if (_isInitialized) {
      _logger.w('Push notification service already initialized');
      return;
    }

    try {
      // Initialize Firebase
      await Firebase.initializeApp();
      _logger.i('Firebase initialized');

      // Initialize Firebase Messaging
      _messaging = FirebaseMessaging.instance;

      // Set background message handler
      FirebaseMessaging.onBackgroundMessage(
        _firebaseMessagingBackgroundHandler,
      );

      // Initialize local notifications for foreground display
      await _initializeLocalNotifications();

      // Request permissions
      await _requestPermissions();

      // Get FCM token
      await _getToken();

      // Listen to token refresh
      _messaging!.onTokenRefresh.listen((token) {
        _logger.i('FCM token refreshed: $token');
        _fcmToken = token;
        _tokenRefreshController.add(token);
        // Auto-register new token with backend if user is authenticated
        _registerTokenWithBackend(token);
      });

      // Handle foreground messages
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

      // Handle notification tap when app is in background
      FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

      // Check if app was opened from a notification
      final initialMessage = await _messaging!.getInitialMessage();
      if (initialMessage != null) {
        _handleNotificationTap(initialMessage);
      }

      _isInitialized = true;
      _logger.i('Push notification service initialized successfully');
    } catch (e, stackTrace) {
      _logger.e('Failed to initialize push notifications', error: e, stackTrace: stackTrace);
      // Don't throw - allow app to continue without notifications
    }
  }

  /// Initialize local notifications for foreground display
  Future<void> _initializeLocalNotifications() async {
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );

    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _localNotifications.initialize(
      settings,
      onDidReceiveNotificationResponse: _onLocalNotificationTap,
    );

    // Create notification channel for Android
    if (Platform.isAndroid) {
      final androidPlugin = _localNotifications.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();

      await androidPlugin?.createNotificationChannel(
        const AndroidNotificationChannel(
          'default_channel',
          'General Notifications',
          description: 'General notifications from DocAssist',
          importance: Importance.high,
          playSound: true,
        ),
      );

      await androidPlugin?.createNotificationChannel(
        const AndroidNotificationChannel(
          'appointment_channel',
          'Appointment Notifications',
          description: 'Appointment reminders and updates',
          importance: Importance.max,
          playSound: true,
        ),
      );

      await androidPlugin?.createNotificationChannel(
        const AndroidNotificationChannel(
          'slot_offer_channel',
          'Slot Offers',
          description: 'Available appointment slot offers',
          importance: Importance.max,
          playSound: true,
          enableVibration: true,
        ),
      );
    }
  }

  /// Request notification permissions
  Future<bool> requestPermissions() async {
    return await _requestPermissions();
  }

  Future<bool> _requestPermissions() async {
    if (_messaging == null) return false;

    try {
      final settings = await _messaging!.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: false,
        announcement: false,
        carPlay: false,
        criticalAlert: false,
      );

      final granted = settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional;

      _logger.i('Notification permission: ${settings.authorizationStatus}');
      return granted;
    } catch (e) {
      _logger.e('Failed to request permissions', error: e);
      return false;
    }
  }

  /// Get FCM token
  Future<String?> _getToken() async {
    if (_messaging == null) return null;

    try {
      _fcmToken = await _messaging!.getToken();
      _logger.i('FCM Token: $_fcmToken');
      return _fcmToken;
    } catch (e) {
      _logger.e('Failed to get FCM token', error: e);
      return null;
    }
  }

  /// Register device token with backend
  ///
  /// Call this after successful authentication to enable push notifications.
  Future<bool> registerWithBackend({String? deviceName}) async {
    if (_fcmToken == null) {
      _logger.w('No FCM token available for registration');
      await _getToken(); // Try to get token
      if (_fcmToken == null) return false;
    }

    return await _registerTokenWithBackend(_fcmToken!, deviceName: deviceName);
  }

  Future<bool> _registerTokenWithBackend(String token, {String? deviceName}) async {
    try {
      final platform = Platform.isIOS ? 'ios' : Platform.isAndroid ? 'android' : 'web';

      final response = await _apiClient._dio.post(
        '/notifications/register',
        data: {
          'device_token': token,
          'platform': platform,
          if (deviceName != null) 'device_name': deviceName,
        },
      );

      _logger.i('Device registered with backend: ${response.data}');
      return true;
    } catch (e) {
      _logger.e('Failed to register with backend', error: e);
      return false;
    }
  }

  /// Unregister device token from backend
  ///
  /// Call this on logout to stop receiving notifications.
  Future<bool> unregisterFromBackend() async {
    if (_fcmToken == null) return false;

    try {
      await _apiClient._dio.delete(
        '/notifications/unregister',
        queryParameters: {'device_token': _fcmToken},
      );

      _logger.i('Device unregistered from backend');
      return true;
    } catch (e) {
      _logger.e('Failed to unregister from backend', error: e);
      return false;
    }
  }

  /// Subscribe to a topic (e.g., clinic notifications)
  Future<bool> subscribeToTopic(String topic) async {
    if (_messaging == null) return false;

    try {
      await _messaging!.subscribeToTopic(topic);
      _logger.i('Subscribed to topic: $topic');
      return true;
    } catch (e) {
      _logger.e('Failed to subscribe to topic $topic', error: e);
      return false;
    }
  }

  /// Unsubscribe from a topic
  Future<bool> unsubscribeFromTopic(String topic) async {
    if (_messaging == null) return false;

    try {
      await _messaging!.unsubscribeFromTopic(topic);
      _logger.i('Unsubscribed from topic: $topic');
      return true;
    } catch (e) {
      _logger.e('Failed to unsubscribe from topic $topic', error: e);
      return false;
    }
  }

  /// Handle foreground messages
  void _handleForegroundMessage(RemoteMessage message) {
    _logger.i('Foreground message received: ${message.messageId}');
    _logger.d('Title: ${message.notification?.title}');
    _logger.d('Body: ${message.notification?.body}');
    _logger.d('Data: ${message.data}');

    // Show local notification
    _showLocalNotification(message);

    // Emit to stream for UI handling
    _messageStreamController.add(message);
  }

  /// Handle notification tap
  void _handleNotificationTap(RemoteMessage message) {
    _logger.i('Notification tapped: ${message.messageId}');
    _logger.d('Data: ${message.data}');

    // Emit to stream for navigation
    _messageStreamController.add(message);

    // Navigate based on notification type
    _navigateFromNotification(message);
  }

  /// Handle local notification tap
  void _onLocalNotificationTap(NotificationResponse response) {
    _logger.i('Local notification tapped: ${response.payload}');
    // Handle navigation if needed based on payload
  }

  /// Show local notification for foreground messages
  Future<void> _showLocalNotification(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;

    final notificationType = NotificationType.fromString(message.data['type']);
    final channelId = _getChannelIdForType(notificationType);

    final androidDetails = AndroidNotificationDetails(
      channelId,
      _getChannelNameForType(notificationType),
      channelDescription: notification.body,
      importance: Importance.high,
      priority: Priority.high,
      playSound: true,
      icon: '@mipmap/ic_launcher',
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _localNotifications.show(
      message.hashCode,
      notification.title,
      notification.body,
      details,
      payload: message.data.toString(),
    );
  }

  /// Get notification channel ID based on type
  String _getChannelIdForType(NotificationType? type) {
    switch (type) {
      case NotificationType.appointmentReminder:
      case NotificationType.appointmentConfirmed:
      case NotificationType.appointmentCancelled:
      case NotificationType.appointmentRescheduled:
        return 'appointment_channel';
      case NotificationType.slotOffer:
        return 'slot_offer_channel';
      default:
        return 'default_channel';
    }
  }

  /// Get notification channel name based on type
  String _getChannelNameForType(NotificationType? type) {
    switch (type) {
      case NotificationType.appointmentReminder:
      case NotificationType.appointmentConfirmed:
      case NotificationType.appointmentCancelled:
      case NotificationType.appointmentRescheduled:
        return 'Appointment Notifications';
      case NotificationType.slotOffer:
        return 'Slot Offers';
      default:
        return 'General Notifications';
    }
  }

  /// Navigate based on notification type
  void _navigateFromNotification(RemoteMessage message) {
    final notificationType = NotificationType.fromString(message.data['type']);

    // This would integrate with your app's navigation
    // For now, just log the intended navigation
    switch (notificationType) {
      case NotificationType.appointmentReminder:
      case NotificationType.appointmentConfirmed:
      case NotificationType.appointmentCancelled:
      case NotificationType.appointmentRescheduled:
        _logger.i('Navigate to: Appointment Details');
        // Example: navigationService.navigateTo('/appointments/${message.data['appointment_id']}');
        break;
      case NotificationType.slotOffer:
        _logger.i('Navigate to: Waitlist/Slot Offer');
        // Example: navigationService.navigateTo('/waitlist/slot-offer/${message.data['waitlist_id']}');
        break;
      case NotificationType.paymentPending:
      case NotificationType.paymentReceived:
        _logger.i('Navigate to: Payment Details');
        // Example: navigationService.navigateTo('/payments/${message.data['payment_id']}');
        break;
      default:
        _logger.i('Navigate to: Home');
        // Example: navigationService.navigateTo('/home');
    }
  }

  /// Get notification badge count (iOS)
  Future<int> getBadgeCount() async {
    if (!Platform.isIOS) return 0;

    try {
      // This requires additional setup in iOS
      // For now, return 0
      return 0;
    } catch (e) {
      return 0;
    }
  }

  /// Clear all notifications
  Future<void> clearAllNotifications() async {
    await _localNotifications.cancelAll();
    _logger.i('All notifications cleared');
  }

  /// Dispose resources
  void dispose() {
    _messageStreamController.close();
    _tokenRefreshController.close();
  }
}
