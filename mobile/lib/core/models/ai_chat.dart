/// AI Chat models for Practice AI Assistant.
///
/// Phase 16a: Natural Language Analytics

class ChatMessage {
  final String role; // 'user', 'assistant', 'system'
  final String content;
  final DateTime timestamp;

  ChatMessage({
    required this.role,
    required this.content,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      role: json['role'] as String,
      content: json['content'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'role': role,
      'content': content,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
}

class ChatResponse {
  final String response;
  final List<String> suggestions;
  final Map<String, dynamic>? data;
  final String? functionCalled;
  final String sessionId;

  ChatResponse({
    required this.response,
    required this.suggestions,
    this.data,
    this.functionCalled,
    required this.sessionId,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      response: json['response'] as String,
      suggestions: (json['suggestions'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      data: json['data'] as Map<String, dynamic>?,
      functionCalled: json['function_called'] as String?,
      sessionId: json['session_id'] as String,
    );
  }
}

class ConversationSession {
  final String sessionId;
  final String userId;
  final String clinicId;
  final List<ChatMessage> messages;
  final DateTime createdAt;
  final DateTime updatedAt;

  ConversationSession({
    required this.sessionId,
    required this.userId,
    required this.clinicId,
    required this.messages,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ConversationSession.fromJson(Map<String, dynamic> json) {
    return ConversationSession(
      sessionId: json['session_id'] as String,
      userId: json['user_id'] as String,
      clinicId: json['clinic_id'] as String,
      messages: (json['messages'] as List<dynamic>?)
              ?.map((e) => ChatMessage.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}
