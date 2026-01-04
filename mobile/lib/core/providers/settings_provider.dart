import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';

// ============ WhatsApp Settings ============

class WhatsAppSettings {
  final bool isEnabled;
  final bool sendReminders;
  final bool sendConfirmations;
  final bool allowBooking;
  final bool allowCancellation;
  final int reminderHoursBefore;
  final String welcomeMessage;

  const WhatsAppSettings({
    this.isEnabled = false,
    this.sendReminders = true,
    this.sendConfirmations = true,
    this.allowBooking = true,
    this.allowCancellation = true,
    this.reminderHoursBefore = 24,
    this.welcomeMessage = '',
  });

  factory WhatsAppSettings.fromJson(Map<String, dynamic> json) {
    return WhatsAppSettings(
      isEnabled: json['is_enabled'] ?? false,
      sendReminders: json['send_reminders'] ?? true,
      sendConfirmations: json['send_confirmations'] ?? true,
      allowBooking: json['allow_booking'] ?? true,
      allowCancellation: json['allow_cancellation'] ?? true,
      reminderHoursBefore: json['reminder_hours_before'] ?? 24,
      welcomeMessage: json['welcome_message'] ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'is_enabled': isEnabled,
        'send_reminders': sendReminders,
        'send_confirmations': sendConfirmations,
        'allow_booking': allowBooking,
        'allow_cancellation': allowCancellation,
        'reminder_hours_before': reminderHoursBefore,
        'welcome_message': welcomeMessage,
      };

  WhatsAppSettings copyWith({
    bool? isEnabled,
    bool? sendReminders,
    bool? sendConfirmations,
    bool? allowBooking,
    bool? allowCancellation,
    int? reminderHoursBefore,
    String? welcomeMessage,
  }) {
    return WhatsAppSettings(
      isEnabled: isEnabled ?? this.isEnabled,
      sendReminders: sendReminders ?? this.sendReminders,
      sendConfirmations: sendConfirmations ?? this.sendConfirmations,
      allowBooking: allowBooking ?? this.allowBooking,
      allowCancellation: allowCancellation ?? this.allowCancellation,
      reminderHoursBefore: reminderHoursBefore ?? this.reminderHoursBefore,
      welcomeMessage: welcomeMessage ?? this.welcomeMessage,
    );
  }
}

class WhatsAppSettingsNotifier extends StateNotifier<WhatsAppSettings?> {
  final ApiClient _apiClient;

  WhatsAppSettingsNotifier(this._apiClient) : super(null) {
    loadSettings();
  }

  Future<void> loadSettings() async {
    try {
      final response = await _apiClient.get('/settings/whatsapp');
      if (response != null) {
        state = WhatsAppSettings.fromJson(response);
      }
    } catch (e) {
      // Use default settings on error
      state = const WhatsAppSettings();
    }
  }

  Future<void> updateSettings({
    bool? isEnabled,
    bool? sendReminders,
    bool? sendConfirmations,
    bool? allowBooking,
    bool? allowCancellation,
    int? reminderHoursBefore,
    String? welcomeMessage,
  }) async {
    final newSettings = (state ?? const WhatsAppSettings()).copyWith(
      isEnabled: isEnabled,
      sendReminders: sendReminders,
      sendConfirmations: sendConfirmations,
      allowBooking: allowBooking,
      allowCancellation: allowCancellation,
      reminderHoursBefore: reminderHoursBefore,
      welcomeMessage: welcomeMessage,
    );

    await _apiClient.put('/settings/whatsapp', newSettings.toJson());
    state = newSettings;
  }
}

final whatsappSettingsProvider =
    StateNotifierProvider<WhatsAppSettingsNotifier, WhatsAppSettings?>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WhatsAppSettingsNotifier(apiClient);
});

// ============ Voice Settings ============

class VoiceSettings {
  final bool isEnabled;
  final String? voiceId;
  final String? voiceName;
  final String language;
  final double speed;
  final double exaggeration;
  final bool useEmotions;

  const VoiceSettings({
    this.isEnabled = false,
    this.voiceId,
    this.voiceName,
    this.language = 'en',
    this.speed = 1.0,
    this.exaggeration = 0.5,
    this.useEmotions = true,
  });

  factory VoiceSettings.fromJson(Map<String, dynamic> json) {
    return VoiceSettings(
      isEnabled: json['is_enabled'] ?? false,
      voiceId: json['voice_id'],
      voiceName: json['voice_name'],
      language: json['language'] ?? 'en',
      speed: (json['speed'] ?? 1.0).toDouble(),
      exaggeration: (json['exaggeration'] ?? 0.5).toDouble(),
      useEmotions: json['use_emotions'] ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
        'is_enabled': isEnabled,
        'voice_id': voiceId,
        'voice_name': voiceName,
        'language': language,
        'speed': speed,
        'exaggeration': exaggeration,
        'use_emotions': useEmotions,
      };

  VoiceSettings copyWith({
    bool? isEnabled,
    String? voiceId,
    String? voiceName,
    String? language,
    double? speed,
    double? exaggeration,
    bool? useEmotions,
  }) {
    return VoiceSettings(
      isEnabled: isEnabled ?? this.isEnabled,
      voiceId: voiceId ?? this.voiceId,
      voiceName: voiceName ?? this.voiceName,
      language: language ?? this.language,
      speed: speed ?? this.speed,
      exaggeration: exaggeration ?? this.exaggeration,
      useEmotions: useEmotions ?? this.useEmotions,
    );
  }

  bool get hasCustomVoice => voiceId != null;
}

class VoiceSettingsNotifier extends StateNotifier<VoiceSettings?> {
  final ApiClient _apiClient;

  VoiceSettingsNotifier(this._apiClient) : super(null) {
    loadSettings();
  }

  Future<void> loadSettings() async {
    try {
      final response = await _apiClient.get('/settings/voice');
      if (response != null) {
        state = VoiceSettings.fromJson(response);
      }
    } catch (e) {
      state = const VoiceSettings();
    }
  }

  Future<void> updateSettings({
    bool? isEnabled,
    String? voiceId,
    String? voiceName,
    String? language,
    double? speed,
    double? exaggeration,
    bool? useEmotions,
  }) async {
    final newSettings = (state ?? const VoiceSettings()).copyWith(
      isEnabled: isEnabled,
      voiceId: voiceId,
      voiceName: voiceName,
      language: language,
      speed: speed,
      exaggeration: exaggeration,
      useEmotions: useEmotions,
    );

    await _apiClient.put('/settings/voice', newSettings.toJson());
    state = newSettings;
  }

  Future<String?> uploadVoiceSample(List<int> audioData, String filename) async {
    try {
      final response = await _apiClient.uploadFile(
        '/voice/clone',
        audioData,
        filename,
      );
      if (response != null) {
        final voiceId = response['voice_id'];
        final voiceName = response['voice_name'];
        state = state?.copyWith(voiceId: voiceId, voiceName: voiceName);
        return voiceId;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  Future<void> deleteCustomVoice() async {
    if (state?.voiceId != null) {
      await _apiClient.delete('/voice/${state!.voiceId}');
      state = state?.copyWith(voiceId: null, voiceName: null);
    }
  }
}

final voiceSettingsProvider =
    StateNotifierProvider<VoiceSettingsNotifier, VoiceSettings?>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return VoiceSettingsNotifier(apiClient);
});

// ============ Available Languages ============

class VoiceLanguage {
  final String code;
  final String name;
  final String nativeName;

  const VoiceLanguage({
    required this.code,
    required this.name,
    required this.nativeName,
  });
}

const availableLanguages = [
  VoiceLanguage(code: 'en', name: 'English', nativeName: 'English'),
  VoiceLanguage(code: 'hi', name: 'Hindi', nativeName: 'हिन्दी'),
  VoiceLanguage(code: 'mr', name: 'Marathi', nativeName: 'मराठी'),
  VoiceLanguage(code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી'),
  VoiceLanguage(code: 'ta', name: 'Tamil', nativeName: 'தமிழ்'),
  VoiceLanguage(code: 'te', name: 'Telugu', nativeName: 'తెలుగు'),
  VoiceLanguage(code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ'),
  VoiceLanguage(code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം'),
  VoiceLanguage(code: 'bn', name: 'Bengali', nativeName: 'বাংলা'),
  VoiceLanguage(code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ'),
  VoiceLanguage(code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ'),
  VoiceLanguage(code: 'as', name: 'Assamese', nativeName: 'অসমীয়া'),
];
