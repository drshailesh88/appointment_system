/// Application configuration
class AppConfig {
  static const String appName = 'DocAssist Practice Manager';
  static const String appVersion = '0.1.0';

  // API Configuration
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  // Feature Flags
  static const bool enableVoiceBooking = true;
  static const bool enableOfflineMode = true;

  // Timeouts
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Cache
  static const Duration cacheMaxAge = Duration(hours: 1);

  /// Initialize app configuration
  static Future<void> initialize() async {
    // Initialize any required services
  }
}
