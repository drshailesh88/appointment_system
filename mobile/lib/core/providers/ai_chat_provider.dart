/// AI Chat Provider for Practice AI Assistant.
///
/// Phase 16a: Natural Language Analytics

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/ai_chat.dart';
import '../api/api_client.dart';

final aiChatProvider = StateNotifierProvider<AIChatNotifier, AIChatState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AIChatNotifier(apiClient);
});

class AIChatState {
  final List<ChatMessage> messages;
  final String? sessionId;
  final List<String> suggestions;
  final bool isLoading;
  final String? error;

  AIChatState({
    this.messages = const [],
    this.sessionId,
    this.suggestions = const [],
    this.isLoading = false,
    this.error,
  });

  AIChatState copyWith({
    List<ChatMessage>? messages,
    String? sessionId,
    List<String>? suggestions,
    bool? isLoading,
    String? error,
  }) {
    return AIChatState(
      messages: messages ?? this.messages,
      sessionId: sessionId ?? this.sessionId,
      suggestions: suggestions ?? this.suggestions,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class AIChatNotifier extends StateNotifier<AIChatState> {
  final ApiClient apiClient;

  AIChatNotifier(this.apiClient) : super(AIChatState());

  /// Send a message to the AI assistant
  Future<void> sendMessage(String message) async {
    if (message.trim().isEmpty) return;

    // Add user message immediately
    final userMessage = ChatMessage(
      role: 'user',
      content: message,
    );

    state = state.copyWith(
      messages: [...state.messages, userMessage],
      isLoading: true,
      error: null,
    );

    try {
      final response = await apiClient.post(
        '/ai/chat',
        data: {
          'message': message,
          'session_id': state.sessionId,
        },
      );

      final chatResponse = ChatResponse.fromJson(response.data);

      // Add assistant message
      final assistantMessage = ChatMessage(
        role: 'assistant',
        content: chatResponse.response,
      );

      state = state.copyWith(
        messages: [...state.messages, assistantMessage],
        sessionId: chatResponse.sessionId,
        suggestions: chatResponse.suggestions,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        error: e.toString(),
        isLoading: false,
      );
    }
  }

  /// Clear the current conversation session
  Future<void> clearSession() async {
    if (state.sessionId == null) {
      state = AIChatState();
      return;
    }

    try {
      await apiClient.delete('/ai/sessions/${state.sessionId}');
      state = AIChatState();
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Load session history
  Future<void> loadSession(String sessionId) async {
    state = state.copyWith(isLoading: true);

    try {
      final response = await apiClient.get('/ai/sessions/$sessionId');
      final session = ConversationSession.fromJson(response.data);

      state = state.copyWith(
        messages: session.messages,
        sessionId: session.sessionId,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        error: e.toString(),
        isLoading: false,
      );
    }
  }

  /// Send a suggestion chip query
  Future<void> sendSuggestion(String suggestion) async {
    await sendMessage(suggestion);
  }
}
