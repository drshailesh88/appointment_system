# DocAssist Practice Manager - Technical Implementation Plan

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DocAssist Practice Manager                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Dashboard  │  │   Calendar   │  │   Patients   │  │     Analytics       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                              FLET UI LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         FASTAPI SERVICE LAYER                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │ Appointment │  │   Patient   │  │   Billing   │  │    Analytics    │  │   │
│  │  │   Service   │  │   Service   │  │   Service   │  │     Service     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │    Sync     │  │    Voice    │  │Notification │  │      Auth       │  │   │
│  │  │   Service   │  │   Service   │  │   Service   │  │     Service     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           DATA ACCESS LAYER                              │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐                      │   │
│  │  │   SQLite + SQLAlchemy │  │   ChromaDB Vectors  │                      │   │
│  │  │   (Practice Data)     │  │   (Smart Search)    │                      │   │
│  │  └──────────────────────┘  └──────────────────────┘                      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          VOICE AI LAYER                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │   Whisper   │  │   Ollama    │  │   Intent    │  │     Piper       │  │   │
│  │  │     STT     │  │   + Qwen    │  │   Parser    │  │      TTS        │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          INTEGRATION LAYER                               │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐                      │   │
│  │  │   EMR Sync Bridge    │  │  External APIs       │                      │   │
│  │  │   (Shared SQLite)    │  │  (SMS, WhatsApp)     │                      │   │
│  │  └──────────────────────┘  └──────────────────────┘                      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
docassist-practice-manager/
├── .claude/
│   └── commands/
│       ├── speckit.constitution.md
│       ├── speckit.specify.md
│       ├── speckit.plan.md
│       ├── speckit.tasks.md
│       ├── ralph-loop.md
│       └── cancel-ralph.md
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── patient.py
│   │   ├── appointment.py
│   │   ├── doctor.py
│   │   ├── staff.py
│   │   ├── service.py
│   │   ├── invoice.py
│   │   ├── payment.py
│   │   └── audit.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── appointment_service.py
│   │   ├── patient_service.py
│   │   ├── billing_service.py
│   │   ├── analytics_service.py
│   │   ├── notification_service.py
│   │   ├── voice_service.py
│   │   ├── sync_service.py
│   │   └── auth_service.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── theme.py
│   │   ├── components/
│   │   │   ├── __init__.py
│   │   │   ├── sidebar.py
│   │   │   ├── calendar.py
│   │   │   ├── patient_card.py
│   │   │   ├── appointment_card.py
│   │   │   ├── metric_card.py
│   │   │   └── voice_indicator.py
│   │   └── pages/
│   │       ├── __init__.py
│   │       ├── dashboard.py
│   │       ├── calendar_view.py
│   │       ├── patient_list.py
│   │       ├── patient_profile.py
│   │       ├── billing.py
│   │       ├── analytics.py
│   │       └── settings.py
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── wake_word.py
│   │   ├── speech_to_text.py
│   │   ├── intent_parser.py
│   │   ├── action_handler.py
│   │   └── text_to_speech.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── emr_bridge.py
│   │   ├── sms_gateway.py
│   │   └── whatsapp_api.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       ├── logging.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models/
│   ├── test_services/
│   ├── test_ui/
│   └── test_voice/
├── prompts/
│   ├── voice_intent.txt
│   ├── appointment_nlp.txt
│   └── analytics_insight.txt
├── data/
│   ├── .gitkeep
│   └── (runtime: practice.db, chroma/)
├── docs/
│   ├── API.md
│   ├── INTEGRATION.md
│   └── USER_GUIDE.md
├── main.py
├── requirements.txt
├── pytest.ini
├── pyproject.toml
├── .env.example
├── .gitignore
├── CLAUDE.md
├── AGENTS.md
├── CODEX.md
├── GEMINI.md
├── GROK.md
└── README.md
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Objective:** Core infrastructure and basic functionality

#### 1.1 Project Setup
- Initialize Python project with pyproject.toml
- Set up virtual environment and dependencies
- Configure pytest, mypy, black, ruff
- Create base configuration system
- Set up logging infrastructure

#### 1.2 Database Layer
- Design and implement SQLAlchemy models
- Create database migrations (Alembic)
- Implement repository pattern
- Set up ChromaDB for vector search
- Create test fixtures

#### 1.3 Basic UI Shell
- Create Flet application skeleton
- Implement theme system (light/dark)
- Build navigation sidebar
- Create page routing
- Design component library

### Phase 2: Core Features (Week 3-4)
**Objective:** Essential appointment and patient management

#### 2.1 Patient Management
- Patient CRUD operations
- Search functionality
- Patient profile view
- EMR data integration (read-only)
- Patient timeline

#### 2.2 Appointment Management
- Calendar view implementation
- Appointment booking flow
- Slot availability calculation
- Conflict detection
- Recurring appointments

#### 2.3 Dashboard
- Today's schedule widget
- Key metrics display
- Quick actions
- Upcoming appointments
- Recent activity

### Phase 3: Billing & Analytics (Week 5-6)
**Objective:** Revenue management and insights

#### 3.1 Billing System
- Service catalog management
- Invoice generation
- Payment recording
- UPI QR code generation
- Invoice printing/PDF

#### 3.2 Analytics Engine
- Revenue analytics
- Patient analytics
- Operational metrics
- Dashboard visualizations
- Report generation

### Phase 4: Voice Agent (Week 7-8)
**Objective:** Hands-free appointment scheduling

#### 4.1 Speech Infrastructure
- Whisper integration (local)
- Piper TTS integration
- Audio I/O handling
- Wake word detection

#### 4.2 Intent Processing
- Intent classification with Ollama
- Slot filling
- Context management
- Confirmation flow

#### 4.3 Voice Actions
- Appointment booking via voice
- Schedule queries
- Cancellation/rescheduling
- Natural conversations

### Phase 5: Integration & Polish (Week 9-10)
**Objective:** EMR integration and premium experience

#### 5.1 EMR Integration
- Shared database schema
- Sync service implementation
- Deep linking
- Context handoff

#### 5.2 Notifications
- SMS gateway integration
- WhatsApp API integration
- Notification scheduling
- Template management

#### 5.3 Final Polish
- Performance optimization
- UI refinements
- Accessibility improvements
- User testing
- Bug fixes

---

## Database Schema

### Core Tables

```sql
-- Patients (synced with EMR)
CREATE TABLE patients (
    id TEXT PRIMARY KEY,
    emr_id TEXT UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT,
    phone TEXT NOT NULL,
    email TEXT,
    date_of_birth DATE,
    gender TEXT,
    address TEXT,
    city TEXT,
    pincode TEXT,
    aadhaar_hash TEXT,
    photo_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP
);

-- Doctors
CREATE TABLE doctors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    specialization TEXT,
    qualification TEXT,
    registration_number TEXT,
    phone TEXT,
    email TEXT,
    consultation_fee DECIMAL(10,2),
    slot_duration INTEGER DEFAULT 15,
    working_hours JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Appointments
CREATE TABLE appointments (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id),
    doctor_id TEXT NOT NULL REFERENCES doctors(id),
    service_id TEXT REFERENCES services(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'scheduled',
    type TEXT DEFAULT 'consultation',
    notes TEXT,
    source TEXT DEFAULT 'manual',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Services
CREATE TABLE services (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    duration INTEGER DEFAULT 15,
    price DECIMAL(10,2) NOT NULL,
    tax_rate DECIMAL(5,2) DEFAULT 18.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invoices
CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    invoice_number TEXT UNIQUE NOT NULL,
    patient_id TEXT NOT NULL REFERENCES patients(id),
    appointment_id TEXT REFERENCES appointments(id),
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    status TEXT DEFAULT 'pending',
    due_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invoice Items
CREATE TABLE invoice_items (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL REFERENCES invoices(id),
    service_id TEXT REFERENCES services(id),
    description TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    tax_rate DECIMAL(5,2) DEFAULT 18.00,
    amount DECIMAL(10,2) NOT NULL
);

-- Payments
CREATE TABLE payments (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL REFERENCES invoices(id),
    amount DECIMAL(10,2) NOT NULL,
    payment_mode TEXT NOT NULL,
    payment_reference TEXT,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_by TEXT
);

-- Staff
CREATE TABLE staff (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    password_hash TEXT,
    permissions JSON,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE notifications (
    id TEXT PRIMARY KEY,
    patient_id TEXT REFERENCES patients(id),
    appointment_id TEXT REFERENCES appointments(id),
    type TEXT NOT NULL,
    channel TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    error_message TEXT
);

-- Audit Log
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    old_values JSON,
    new_values JSON,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Voice Agent Architecture

### Wake Word Detection
```
openwakeword library
Model: "hey_docassist" (custom trained)
Threshold: 0.5
Refractory period: 2 seconds
```

### Speech-to-Text Pipeline
```
Input: Audio stream (16kHz, mono)
Engine: Whisper (base.en or small.en)
Output: Transcribed text + confidence
Latency target: < 500ms
```

### Intent Classification
```
Engine: Ollama + Qwen 2.5
Prompt template: prompts/voice_intent.txt
Intents:
  - book_appointment
  - cancel_appointment
  - reschedule_appointment
  - query_schedule
  - query_availability
  - query_patient
  - query_metrics
  - general_query
```

### Slot Filling
```
Slots for book_appointment:
  - patient_name (required)
  - date (required)
  - time (optional)
  - doctor (optional)
  - service (optional)

Strategy: Multi-turn dialogue if slots missing
```

### Text-to-Speech
```
Engine: Piper TTS
Voice: en_US-lessac-medium
Sample rate: 22050 Hz
Latency target: < 200ms
```

---

## EMR Integration Design

### Shared Database Schema
```
EMR Database: clinic.db
Practice Manager Database: practice.db

Shared Tables (synced):
- patients (demographics)

EMR-Only Tables (read from EMR):
- clinical_records
- prescriptions
- vitals

Practice Manager-Only Tables:
- appointments
- invoices
- payments
- staff
```

### Sync Strategy
```python
class SyncService:
    """
    Bidirectional sync between EMR and Practice Manager
    """

    def __init__(self, emr_db_path: str, pm_db_path: str):
        self.emr_db = emr_db_path
        self.pm_db = pm_db_path
        self.watcher = FileSystemWatcher()

    def start_sync(self):
        """Watch for changes and sync"""
        self.watcher.watch(self.emr_db, self.on_emr_change)
        self.watcher.watch(self.pm_db, self.on_pm_change)

    def on_emr_change(self, event):
        """Sync patient data from EMR"""
        # Pull new/updated patients
        # Merge with local data

    def on_pm_change(self, event):
        """Sync appointments to EMR (if needed)"""
        # Push appointment data
```

### Deep Linking
```
URI Scheme: docassist://
Examples:
  docassist://emr/patient/{id}
  docassist://practice/appointment/{id}
  docassist://practice/book?patient={id}
```

---

## Testing Strategy

### Unit Tests
- All models with SQLite in-memory
- All services with mocked dependencies
- UI components in isolation

### Integration Tests
- Full appointment booking flow
- Payment and invoice flow
- EMR sync scenarios

### End-to-End Tests
- Critical user journeys
- Voice command scenarios
- Multi-user scenarios

### Performance Tests
- Load testing with 10k patients
- Concurrent user simulation
- Database query optimization

---

## Ralph Wiggum Integration

### Loop Configuration

```yaml
# For each feature implementation
ralph_config:
  task: "Implement [feature name]"
  max_iterations: 50
  completion_signals:
    - "All tests pass"
    - "Feature working as specified"
  verification:
    - "pytest tests/ -v"
    - "mypy src/ --strict"
    - "ruff check src/"
```

### Feature Development Loop

```
1. Start Ralph loop with feature task
2. Write/modify code
3. Run tests
4. If tests fail, analyze and fix
5. Commit working code
6. Repeat until completion signal
```

### Recommended Ralph Tasks

1. **Database Models** - "Implement all SQLAlchemy models with full test coverage"
2. **Appointment Service** - "Implement appointment booking with conflict detection"
3. **Calendar UI** - "Create calendar view with all interactions"
4. **Voice Intent Parser** - "Implement voice intent classification with 95% accuracy"
5. **Analytics Dashboard** - "Build analytics dashboard with all metrics"

---

## Deployment Strategy

### Desktop Application
```
Distribution: PyInstaller bundle
Installer: InnoSetup (Windows), .deb (Linux)
Auto-update: Built-in updater
```

### Configuration
```
User data: ~/DocAssist/PracticeManager/
Database: ~/DocAssist/PracticeManager/data/practice.db
Logs: ~/DocAssist/PracticeManager/logs/
Config: ~/DocAssist/PracticeManager/config.yaml
```

### System Requirements
```
Minimum:
  - OS: Windows 10 / Ubuntu 20.04
  - CPU: 2 cores
  - RAM: 4 GB
  - Storage: 10 GB

Recommended (with Voice):
  - OS: Windows 11 / Ubuntu 22.04
  - CPU: 4 cores
  - RAM: 8 GB
  - Storage: 50 GB SSD
```

---

*This technical plan guides the implementation of DocAssist Practice Manager using spec-driven development with Ralph Wiggum iteration.*

**Last Updated:** 2026-01-03
**Version:** 1.0
