# DocAssist Practice Manager - Flutter + Python Architecture

## Why Flutter Instead of Flet?

| Aspect | Flet | Flutter | Our Choice |
|--------|------|---------|------------|
| **Mobile maturity** | New, limited | Battle-tested | Flutter |
| **iOS performance** | Interpreted | Native-compiled | Flutter |
| **Play Store/App Store** | Limited support | Full support | Flutter |
| **Developer ecosystem** | Small | Massive (2M+ devs) | Flutter |
| **UI components** | Limited | 1000s of packages | Flutter |
| **Desktop support** | Good | Good | Both similar |
| **Python integration** | Native | Via API | API-based |

**Decision:** Use Flutter for all client apps, Python FastAPI for backend.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Flutter    │  │   Flutter    │  │   Flutter    │  │   Flutter    │    │
│  │   Android    │  │     iOS      │  │     Web      │  │   Desktop    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│           │                │                │                │              │
│           └────────────────┴────────────────┴────────────────┘              │
│                                    │                                         │
│                          Shared Flutter Codebase                            │
│                          (95% code sharing)                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ REST API + WebSocket
                                     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVER LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                         FastAPI Backend                            │     │
│  │                                                                    │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │     │
│  │  │  Auth API   │  │Appointment  │  │  Billing    │               │     │
│  │  │  (JWT)      │  │    API      │  │    API      │               │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │     │
│  │                                                                    │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │     │
│  │  │  Patient    │  │  Analytics  │  │   Voice     │               │     │
│  │  │    API      │  │    API      │  │    API      │               │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │     │
│  │                                                                    │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│  ┌─────────────┐  ┌─────────────┐  │  ┌─────────────┐  ┌─────────────┐     │
│  │  PostgreSQL │  │  ChromaDB   │  │  │  Whisper    │  │   Ollama    │     │
│  │  (Primary)  │  │  (Vectors)  │  │  │  (STT)      │  │   (LLM)     │     │
│  └─────────────┘  └─────────────┘  │  └─────────────┘  └─────────────┘     │
│                                    │                                         │
│  ┌─────────────┐  ┌─────────────┐  │  ┌─────────────┐                      │
│  │   Redis     │  │  Celery     │  │  │   Piper     │                      │
│  │  (Cache)    │  │  (Tasks)    │  │  │   (TTS)     │                      │
│  └─────────────┘  └─────────────┘  │  └─────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Options

### Option A: Cloud Deployment (Recommended for MVP)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                CLOUD                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  AWS / DigitalOcean / Azure                                         │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   FastAPI   │  │  PostgreSQL │  │    Redis    │                 │   │
│  │  │  (Docker)   │  │   (RDS)     │  │(Elasticache)│                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐                                  │   │
│  │  │  Whisper    │  │   Ollama    │  ← GPU instance for AI          │   │
│  │  │  (GPU)      │  │   (GPU)     │                                  │   │
│  │  └─────────────┘  └─────────────┘                                  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
         │                    │                    │
    ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
    │ Mobile  │         │   Web   │         │ Desktop │
    │  Apps   │         │   App   │         │   App   │
    └─────────┘         └─────────┘         └─────────┘
```

**Pros:**
- Fast to market
- No hardware for doctors
- Easy updates

**Cons:**
- Requires internet (offline handled by local cache)
- Monthly cloud costs

### Option B: Hybrid (On-Premise + Cloud)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLINIC (On-Premise)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Clinic Server (Mini PC / NUC)                                      │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   FastAPI   │  │   SQLite    │  │   Ollama    │                 │   │
│  │  │   Local     │  │   Local     │  │   Local     │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │                                                                      │   │
│  │  ← Works completely offline                                         │   │
│  │  ← Voice agent runs locally                                         │   │
│  │  ← Data never leaves clinic                                         │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          │ Sync when online (optional)                      │
│                          ↓                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD (Optional)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │   Backup    │  │   Sync      │  │   Patient   │                         │
│  │   Service   │  │   Service   │  │   Portal    │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pros:**
- True offline-first
- Data stays local (privacy)
- No recurring cloud costs for clinic

**Cons:**
- Hardware cost for clinic
- More complex setup

### Recommended: Start with Option A, Add Option B Later

1. **MVP (Month 1-6):** Cloud-only with aggressive local caching
2. **V2 (Month 7-12):** Add on-premise option for privacy-conscious
3. **V3 (Year 2):** Hardware bundle (tablet + mini server)

---

## Technology Stack

### Frontend (Flutter)

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | Flutter 3.x | Cross-platform UI |
| **State Management** | Riverpod | Reactive state |
| **Local Storage** | Hive / Isar | Offline data cache |
| **API Client** | Dio | HTTP with interceptors |
| **Real-time** | WebSocket | Live updates |
| **Charts** | fl_chart | Analytics visualizations |
| **Forms** | flutter_form_builder | Complex forms |
| **Notifications** | firebase_messaging | Push notifications |

### Backend (Python)

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | FastAPI | High-performance API |
| **Database** | PostgreSQL | Primary data store |
| **ORM** | SQLAlchemy 2.0 | Database operations |
| **Migrations** | Alembic | Schema migrations |
| **Cache** | Redis | Session, rate limiting |
| **Task Queue** | Celery | Background jobs |
| **Vector DB** | ChromaDB | Semantic search |
| **Auth** | JWT + OAuth2 | Authentication |

### AI/Voice (Python)

| Component | Technology | Purpose |
|-----------|------------|---------|
| **STT** | faster-whisper | Speech to text |
| **TTS** | Piper | Text to speech |
| **Wake Word** | openWakeWord | "Hey DocAssist" |
| **LLM** | Ollama + Qwen | Intent classification |
| **NLU** | Custom + Ollama | Slot filling |

---

## Project Structure

### Flutter App (Single Codebase)

```
flutter_app/
├── lib/
│   ├── main.dart
│   ├── app/
│   │   ├── app.dart
│   │   ├── routes.dart
│   │   └── theme.dart
│   ├── core/
│   │   ├── api/
│   │   │   ├── api_client.dart
│   │   │   ├── interceptors/
│   │   │   └── endpoints.dart
│   │   ├── auth/
│   │   │   ├── auth_provider.dart
│   │   │   └── auth_service.dart
│   │   ├── local_storage/
│   │   │   ├── hive_service.dart
│   │   │   └── offline_sync.dart
│   │   └── utils/
│   ├── features/
│   │   ├── appointments/
│   │   │   ├── data/
│   │   │   ├── domain/
│   │   │   └── presentation/
│   │   ├── patients/
│   │   ├── billing/
│   │   ├── analytics/
│   │   └── settings/
│   ├── shared/
│   │   ├── widgets/
│   │   ├── models/
│   │   └── providers/
│   └── platform/
│       ├── mobile/          # Mobile-specific
│       ├── web/             # Web-specific
│       └── desktop/         # Desktop-specific
├── android/
├── ios/
├── web/
├── windows/
├── macos/
├── linux/
├── test/
└── pubspec.yaml
```

### Python Backend

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry
│   ├── core/
│   │   ├── config.py           # Settings
│   │   ├── security.py         # JWT, hashing
│   │   ├── database.py         # DB connection
│   │   └── redis.py            # Cache
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── appointments.py
│   │   │   ├── patients.py
│   │   │   ├── billing.py
│   │   │   ├── analytics.py
│   │   │   └── voice.py
│   │   └── deps.py             # Dependencies
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── patient.py
│   │   ├── appointment.py
│   │   └── ...
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py
│   │   ├── patient.py
│   │   └── ...
│   ├── services/               # Business logic
│   │   ├── appointment_service.py
│   │   ├── billing_service.py
│   │   ├── notification_service.py
│   │   └── ...
│   ├── voice/                  # Voice agent
│   │   ├── stt.py              # Whisper
│   │   ├── tts.py              # Piper
│   │   ├── wake_word.py        # openWakeWord
│   │   ├── intent.py           # Ollama NLU
│   │   └── agent.py            # Voice orchestration
│   └── integrations/
│       ├── sms.py
│       ├── whatsapp.py
│       └── emr_sync.py
├── alembic/                    # Migrations
├── tests/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
├── requirements.txt
└── pyproject.toml
```

---

## API Design

### Authentication

```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/forgot-password
POST /api/v1/auth/verify-otp
```

### Appointments

```
GET    /api/v1/appointments                    # List appointments
POST   /api/v1/appointments                    # Create appointment
GET    /api/v1/appointments/{id}               # Get appointment
PUT    /api/v1/appointments/{id}               # Update appointment
DELETE /api/v1/appointments/{id}               # Cancel appointment
GET    /api/v1/appointments/slots              # Available slots
POST   /api/v1/appointments/{id}/check-in      # Mark arrived
POST   /api/v1/appointments/{id}/complete      # Mark completed
```

### Voice Agent (WebSocket)

```
WS /api/v1/voice/stream

Messages:
→ { "type": "audio_chunk", "data": "<base64>" }
← { "type": "transcription", "text": "book appointment for..." }
← { "type": "intent", "intent": "book_appointment", "slots": {...} }
← { "type": "confirmation", "message": "Book Rahul for 10 AM?" }
→ { "type": "confirm", "value": true }
← { "type": "result", "success": true, "appointment_id": "..." }
← { "type": "tts_audio", "data": "<base64>" }
```

---

## Offline-First Strategy

### Local Caching (Flutter)

```dart
// Using Hive for local storage
class OfflineRepository {
  final Box<Appointment> appointmentsBox;
  final Box<Patient> patientsBox;
  final Box<SyncQueue> syncQueueBox;

  // Always read from local first
  Future<List<Appointment>> getAppointments(DateTime date) async {
    // 1. Return cached data immediately
    final cached = appointmentsBox.values.where((a) => a.date == date);

    // 2. Fetch from server in background
    _syncFromServer(date);

    return cached.toList();
  }

  // Queue writes for sync
  Future<void> createAppointment(Appointment apt) async {
    // 1. Save locally
    await appointmentsBox.put(apt.id, apt);

    // 2. Queue for server sync
    await syncQueueBox.add(SyncQueue(
      action: 'create',
      entity: 'appointment',
      data: apt.toJson(),
      timestamp: DateTime.now(),
    ));

    // 3. Try sync immediately if online
    _trySync();
  }
}
```

### Sync Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                        SYNC FLOW                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User action (book appointment)                              │
│     ↓                                                           │
│  2. Save to local Hive database                                 │
│     ↓                                                           │
│  3. Add to sync queue                                           │
│     ↓                                                           │
│  4. If online → Push to server immediately                      │
│     If offline → Queue for later                                │
│     ↓                                                           │
│  5. Server confirms → Mark synced                               │
│     Server fails → Retry with exponential backoff               │
│     Conflict → Apply conflict resolution                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Conflict Resolution

| Scenario | Resolution |
|----------|------------|
| Same appointment edited on 2 devices | Last-write-wins with merge |
| Appointment booked offline, slot taken | Notify user, offer alternatives |
| Patient edited while offline | Merge non-conflicting fields |

---

## Voice Agent Architecture (Server-Side)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VOICE AGENT FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Microphone] ─→ [WebSocket] ─→ [Server]                                   │
│                                    │                                         │
│                    ┌───────────────┴───────────────┐                        │
│                    ↓                               ↓                        │
│              [Wake Word]                    [VAD Detection]                 │
│              (openWakeWord)                 (Voice Activity)                │
│                    │                               │                        │
│                    └───────────┬───────────────────┘                        │
│                                ↓                                            │
│                         [faster-whisper]                                    │
│                         (Speech to Text)                                    │
│                                │                                            │
│                                ↓                                            │
│                    "Book Rahul Sharma tomorrow 10 AM"                       │
│                                │                                            │
│                                ↓                                            │
│                         [Ollama + Qwen]                                     │
│                         (Intent + Slots)                                    │
│                                │                                            │
│                                ↓                                            │
│                    {                                                        │
│                      "intent": "book_appointment",                          │
│                      "slots": {                                             │
│                        "patient": "Rahul Sharma",                           │
│                        "date": "2026-01-04",                                │
│                        "time": "10:00"                                      │
│                      }                                                      │
│                    }                                                        │
│                                │                                            │
│                                ↓                                            │
│                      [Action Handler]                                       │
│                      (Execute Booking)                                      │
│                                │                                            │
│                                ↓                                            │
│                      [Piper TTS]                                            │
│                      "Booked. SMS sent."                                    │
│                                │                                            │
│                                ↓                                            │
│  [Speaker] ←── [WebSocket] ←── [Audio Response]                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Development Phases

### Phase 1: Backend MVP (Weeks 1-4)
- [ ] FastAPI project setup
- [ ] PostgreSQL models and migrations
- [ ] Auth (JWT + refresh tokens)
- [ ] Appointments CRUD API
- [ ] Patients CRUD API
- [ ] Basic billing API
- [ ] Docker setup

### Phase 2: Flutter MVP (Weeks 5-8)
- [ ] Flutter project setup
- [ ] Auth flow (login, register)
- [ ] Appointments list and calendar
- [ ] Patient management
- [ ] Basic billing
- [ ] Offline caching with Hive

### Phase 3: Integration (Weeks 9-10)
- [ ] API integration
- [ ] Offline sync implementation
- [ ] Push notifications
- [ ] Error handling

### Phase 4: Voice Agent (Weeks 11-14)
- [ ] WebSocket endpoint
- [ ] faster-whisper integration
- [ ] Ollama intent classification
- [ ] Piper TTS responses
- [ ] Voice UI in Flutter (desktop/web)

### Phase 5: Polish & Launch (Weeks 15-16)
- [ ] Performance optimization
- [ ] iOS/Android store preparation
- [ ] Documentation
- [ ] Beta testing

---

## Repository Structure

```
docassist/
├── backend/                    # Python FastAPI
├── flutter_app/                # Flutter (all platforms)
├── docs/                       # Documentation
├── infrastructure/             # Terraform, K8s configs
└── shared/                     # Shared API specs (OpenAPI)
```

---

*This architecture enables:*
*- Single Flutter codebase for iOS, Android, Web, Desktop*
*- Python backend for AI/Voice processing*
*- True offline-first with cloud sync*
*- Scalable from 1 to 100,000 clinics*

---

**Last Updated:** 2026-01-03
