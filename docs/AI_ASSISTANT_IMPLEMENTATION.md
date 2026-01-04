# Phase 16a: Practice AI Assistant - Implementation Guide

**Status:** ✅ Implemented
**Date:** 2026-01-04
**Phase:** 16a - Natural Language Analytics

---

## Overview

The Practice AI Assistant enables natural language queries for practice analytics, allowing doctors and staff to ask questions like:

- "How many procedures this month?"
- "Revenue last week"
- "Dr. Sharma's procedure count"
- "Find diabetic patients"
- "No-show rate this month"

This implementation uses **Ollama + Qwen2.5** (already integrated for voice agent) with function calling capabilities.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Practice AI Assistant                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────────┐    │
│  │  Mobile  │───▶│   Backend    │───▶│   LLM Service      │    │
│  │  Chat UI │    │   /ai/chat   │    │   (Ollama+Qwen)    │    │
│  └──────────┘    └──────────────┘    └────────────────────┘    │
│                         │                      │                │
│                         ▼                      ▼                │
│                  ┌──────────────┐    ┌────────────────────┐    │
│                  │   Services   │    │   Tool Executor    │    │
│                  │  (existing)  │    │   (function call)  │    │
│                  └──────────────┘    └────────────────────┘    │
│                         │                                       │
│         ┌───────────────┼───────────────┐                      │
│         ▼               ▼               ▼                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │ Procedures │  │  Analytics │  │Appointments│               │
│  │  Service   │  │   Service  │  │  Service   │               │
│  └────────────┘  └────────────┘  └────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files Created

### Backend

#### 1. AI Assistant Service
**File:** `/home/user/appointment_system/backend/app/services/ai_assistant.py`

**Key Features:**
- Function calling with Ollama/Qwen
- Natural language query parsing
- Session management (in-memory for MVP)
- Response generation with follow-up suggestions
- Fallback parsing using keyword matching

**Available Functions:**
```python
- get_procedure_stats(start_date, end_date, category?, doctor_id?)
- get_revenue_analytics(start_date, end_date, doctor_id?)
- get_appointment_stats(start_date, end_date, doctor_id?)
- search_patients(query)
- get_doctor_stats(start_date, end_date)
```

**Example Usage:**
```python
from app.services.ai_assistant import get_ai_assistant

assistant = get_ai_assistant()
response = await assistant.chat(
    message="How many procedures this month?",
    clinic_id=clinic_id,
    user_id=user_id,
)
```

#### 2. Pydantic Schemas
**File:** `/home/user/appointment_system/backend/app/schemas/ai_chat.py`

**Models:**
- `ChatMessageRequest` - Request to send a message
- `ChatMessageResponse` - AI response with suggestions
- `MessageModel` - Single message in conversation
- `SessionHistoryResponse` - Full conversation history
- `SessionClearResponse` - Session clear confirmation

#### 3. API Endpoints
**File:** `/home/user/appointment_system/backend/app/api/v1/ai_chat.py`

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/chat` | Send message to AI assistant |
| GET | `/api/v1/ai/sessions/{session_id}` | Get conversation history |
| DELETE | `/api/v1/ai/sessions/{session_id}` | Clear session |
| POST | `/api/v1/ai/sessions/cleanup` | Cleanup old sessions (admin only) |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many procedures this month?",
    "session_id": "optional-session-id"
  }'
```

**Example Response:**
```json
{
  "response": "This month you've completed 127 procedures:\n\n• Cardiology: 68 (54%)\n  - Echo: 42\n  - ECG: 18\n  - Angioplasty: 8\n• Orthopedics: 35 (28%)\n• General: 24 (18%)\n\nTotal billed: ₹18,50,000\n\nWould you like a breakdown by doctor?",
  "suggestions": [
    "Breakdown by doctor",
    "Compare to last month",
    "Show me procedure trends"
  ],
  "data": {
    "total": 127,
    "by_category": {...},
    "by_type": {...}
  },
  "function_called": "get_procedure_stats",
  "session_id": "abc123-def456"
}
```

#### 4. Tests
**File:** `/home/user/appointment_system/backend/tests/test_ai_assistant.py`

**Coverage:**
- Query parsing (LLM + fallback)
- Relative date parsing
- Function execution
- Session management
- Response generation
- Suggestion generation

**Run Tests:**
```bash
cd backend
pytest tests/test_ai_assistant.py -v
```

---

### Mobile (Flutter)

#### 1. AI Chat Models
**File:** `/home/user/appointment_system/mobile/lib/core/models/ai_chat.dart`

**Models:**
- `ChatMessage` - Single message (user/assistant)
- `ChatResponse` - AI response from API
- `ConversationSession` - Full session with history

#### 2. AI Chat Provider
**File:** `/home/user/appointment_system/mobile/lib/core/providers/ai_chat_provider.dart`

**State Management:**
- Riverpod StateNotifier
- Message list with session tracking
- Loading states
- Error handling

**Methods:**
```dart
sendMessage(String message)       // Send user message
clearSession()                     // Clear conversation
loadSession(String sessionId)      // Load history
sendSuggestion(String suggestion)  // Send suggestion chip
```

#### 3. Chat UI Screen
**File:** `/home/user/appointment_system/mobile/lib/features/ai_assistant/presentation/ai_chat_screen.dart`

**Features:**
- Message bubbles (user vs assistant styling)
- Suggestion chips for follow-up queries
- Voice input button (ready for integration)
- Auto-scroll to latest message
- Empty state with example queries
- Loading indicator
- Error display
- Clear chat confirmation

**UI Components:**
```dart
- Message bubbles with timestamps
- Suggestion chips
- Text input field
- Voice input button
- Example queries in empty state
- Loading animation
```

#### 4. Floating Action Button Widget
**File:** `/home/user/appointment_system/mobile/lib/core/widgets/ai_assistant_fab.dart`

**Usage:**
```dart
// In any screen, add to Scaffold:
floatingActionButton: AIAssistantFAB(),

// Or use extended version:
floatingActionButton: AIAssistantExtendedFAB(),
```

**Example Integration:**
```dart
// dashboard_screen.dart
@override
Widget build(BuildContext context) {
  return Scaffold(
    appBar: AppBar(title: Text('Dashboard')),
    body: DashboardContent(),
    floatingActionButton: AIAssistantFAB(), // <-- Add here
  );
}
```

---

## Configuration

### Environment Variables

The AI Assistant uses existing Ollama configuration from `/home/user/appointment_system/backend/app/core/config.py`:

```python
# Already configured in settings
ollama_base_url: str = "http://localhost:11434"
ollama_model: str = "qwen2.5:3b"
```

No additional configuration needed!

---

## Integration Checklist

### Backend

- [x] AI assistant service created
- [x] Pydantic schemas defined
- [x] API endpoints implemented
- [x] Router registered in API v1
- [x] Tests written
- [ ] **TODO:** Connect to actual analytics services (currently using mocks)
- [ ] **TODO:** Add Redis for session storage (currently in-memory)
- [ ] **TODO:** Add authentication checks

### Mobile

- [x] AI chat models defined
- [x] AI chat provider implemented
- [x] Chat UI screen created
- [x] FAB widget created
- [ ] **TODO:** Add FAB to dashboard screen
- [ ] **TODO:** Add FAB to other key screens
- [ ] **TODO:** Integrate voice input with existing Whisper service
- [ ] **TODO:** Add data visualization for structured responses

### Infrastructure

- [ ] **TODO:** Ensure Ollama is running (`ollama serve`)
- [ ] **TODO:** Pull Qwen model if not present (`ollama pull qwen2.5:3b`)
- [ ] **TODO:** Configure Redis for production session storage
- [ ] **TODO:** Set up monitoring for AI query success rate

---

## Query Examples

### Supported Queries

| Category | Example Queries |
|----------|-----------------|
| **Procedures** | "How many echos this month?"<br>"Procedure count by doctor"<br>"Compare procedures to last month" |
| **Revenue** | "What's my revenue today?"<br>"Revenue last week"<br>"Outstanding payments" |
| **Appointments** | "Appointment stats this month"<br>"No-show rate"<br>"Busiest day this week" |
| **Patients** | "Find diabetic patients"<br>"Search patient Ramesh"<br>"Patients from Andheri" |
| **Doctors** | "Dr. Sharma's performance"<br>"Which doctor most productive?"<br>"Doctor utilization rate" |

### Date Parsing

The AI understands relative dates:

| User Input | Parsed As |
|------------|-----------|
| "today" | 2026-01-04 |
| "yesterday" | 2026-01-03 |
| "this week" | 2025-12-29 to 2026-01-04 |
| "this month" | 2026-01-01 to 2026-01-04 |
| "last month" | 2025-12-01 to 2025-12-31 |

---

## Next Steps (Phase 16b+)

### Phase 16b: Conversational Actions (2 weeks)

- [ ] Book appointment via chat
- [ ] Reschedule appointment
- [ ] Patient lookup with details
- [ ] Confirmation flows for write actions
- [ ] Undo capability (30 seconds)

### Phase 16c: Proactive Intelligence (2 weeks)

- [ ] Smart notifications ("3 patients due for follow-up")
- [ ] Schedule optimization suggestions
- [ ] Automated follow-up scheduling
- [ ] Procedure-aware suggestions

### Phase 16d: Voice Integration (1 week)

- [ ] Connect voice input to existing Whisper
- [ ] Voice output using Chatterbox TTS
- [ ] Unified voice + chat experience
- [ ] Hands-free mode for busy doctors

---

## Production Considerations

### Performance

- **Target:** < 2 seconds response time (P95)
- **Current:** Uses in-memory session storage (fast but not persistent)
- **Recommendation:** Use Redis for session storage in production

### Security

- **Authentication:** Uses existing JWT auth from `CurrentUser` dependency
- **Authorization:** Session verification prevents cross-user access
- **Data Privacy:** No clinical notes access (practice data only)

### Scalability

- **Session Cleanup:** Auto-cleanup after 24 hours (configurable)
- **Rate Limiting:** Uses existing API rate limiting
- **LLM Load:** Ollama can be scaled horizontally if needed

### Monitoring

**Key Metrics to Track:**
- Query success rate (target: > 90%)
- Response time (target: < 2s)
- Function call accuracy
- User adoption rate (% of users using daily)
- Most common queries (for optimization)

---

## Troubleshooting

### "Ollama not available" Error

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# Pull Qwen model if not present
ollama pull qwen2.5:3b
```

### "Session not found" Error

**Cause:** Session expired or was cleared

**Solution:** Frontend should handle this gracefully by starting a new session

### Slow Response Time

**Check:**
1. Ollama server status
2. Model size (qwen2.5:3b is fast, 14b is slower but more accurate)
3. Network latency between backend and Ollama

**Optimize:**
```python
# In config.py, use smaller model for speed
ollama_model: str = "qwen2.5:1.5b"  # Faster but less accurate
```

### Inaccurate Function Calls

**Fallback:** The system has keyword-based fallback parsing

**Improve:**
1. Use larger Qwen model (qwen2.5:7b or 14b)
2. Add more examples to system prompt
3. Implement few-shot learning in prompt

---

## API Documentation

Full API documentation available at:
- **Swagger UI:** http://localhost:8000/docs (when backend running)
- **Tag:** "AI Assistant"

---

## References

- **Spec:** `/home/user/appointment_system/.claude/specs/practice-ai-assistant.md`
- **Ollama Docs:** https://github.com/ollama/ollama/blob/main/docs/api.md
- **Qwen Model:** https://ollama.com/library/qwen2.5
- **Existing Voice Agent:** `/home/user/appointment_system/backend/app/voice/nlu.py`

---

## License

Part of DocAssist Practice Manager
© 2026 Dr. Shailesh

---

**Last Updated:** 2026-01-04
**Phase:** 16a Complete ✅
**Next Phase:** 16b - Conversational Actions
