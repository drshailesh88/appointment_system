# DocAssist Practice Manager - Task Breakdown

## Development Workflow Reminder

**IMPORTANT:** All development follows Spec-Kit + Ralph Wiggum methodology:

1. Before implementing any feature, reference:
   - `speckit.constitution.md` - For principles and constraints
   - `speckit.specify.md` - For feature requirements
   - `speckit.plan.md` - For technical approach

2. Use Ralph Wiggum loops for all significant implementations:
   - Define clear completion criteria
   - Run verification after each iteration
   - Commit working code
   - Continue until tests pass

3. After completing tasks, update this file with status

---

## Phase 1: Foundation

### Task 1.1: Project Initialization
**Status:** Pending
**Ralph Loop:** Not required (setup tasks)

- [ ] Create pyproject.toml with all dependencies
- [ ] Create requirements.txt for pip compatibility
- [ ] Set up virtual environment structure
- [ ] Create .gitignore for Python project
- [ ] Create .env.example with all config options
- [ ] Set up pytest.ini with coverage settings
- [ ] Configure mypy.ini for strict type checking
- [ ] Create CLAUDE.md with project instructions
- [ ] Replicate to AGENTS.md, CODEX.md, GEMINI.md, GROK.md
- [ ] Create README.md with project overview

**Verification:**
```bash
python -m pytest --version  # pytest available
mypy --version              # mypy available
```

### Task 1.2: Database Models
**Status:** Pending
**Ralph Loop:** Yes - "Implement all SQLAlchemy models with tests"
**Max Iterations:** 30

- [ ] Create src/models/base.py with SQLAlchemy base
- [ ] Implement Patient model with EMR sync fields
- [ ] Implement Doctor model
- [ ] Implement Staff model with roles
- [ ] Implement Appointment model with constraints
- [ ] Implement Service model
- [ ] Implement Invoice and InvoiceItem models
- [ ] Implement Payment model
- [ ] Implement Notification model
- [ ] Implement AuditLog model
- [ ] Create database initialization script
- [ ] Write tests for all models

**Verification:**
```bash
pytest tests/test_models/ -v
mypy src/models/ --strict
```

**Completion Criteria:**
- All models defined with proper relationships
- All constraints working (foreign keys, unique)
- 100% test coverage on models
- mypy passes with strict mode

### Task 1.3: Configuration System
**Status:** Pending
**Ralph Loop:** Yes - "Implement configuration management"
**Max Iterations:** 15

- [ ] Create src/utils/config.py with Pydantic settings
- [ ] Support environment variables
- [ ] Support config file (config.yaml)
- [ ] Create default configuration
- [ ] Implement path management
- [ ] Add EMR integration paths
- [ ] Write tests for config loading

**Verification:**
```bash
pytest tests/test_utils/test_config.py -v
```

### Task 1.4: Logging Infrastructure
**Status:** Pending
**Ralph Loop:** Not required (simple task)

- [ ] Create src/utils/logging.py
- [ ] Configure rotating file logs
- [ ] Set up console logging with colors
- [ ] Create log formatters
- [ ] Integrate with all modules

### Task 1.5: Basic UI Shell
**Status:** Pending
**Ralph Loop:** Yes - "Create Flet UI shell with navigation"
**Max Iterations:** 25

- [ ] Create src/ui/app.py with main application
- [ ] Implement theme system (src/ui/theme.py)
- [ ] Create sidebar navigation component
- [ ] Implement page routing
- [ ] Create placeholder pages (Dashboard, Calendar, etc.)
- [ ] Add dark mode toggle
- [ ] Test on Windows and Linux

**Verification:**
```bash
python main.py  # App launches without errors
```

**Completion Criteria:**
- App launches in < 2 seconds
- Navigation works between all pages
- Dark mode toggle works
- No visual glitches

---

## Phase 2: Core Features

### Task 2.1: Patient Service
**Status:** Pending
**Ralph Loop:** Yes - "Implement patient CRUD with search"
**Max Iterations:** 30

- [ ] Create src/services/patient_service.py
- [ ] Implement create patient
- [ ] Implement read patient (by ID, phone, name)
- [ ] Implement update patient
- [ ] Implement delete patient (soft delete)
- [ ] Implement search with fuzzy matching
- [ ] Add pagination support
- [ ] Write comprehensive tests

**Verification:**
```bash
pytest tests/test_services/test_patient_service.py -v
```

**Completion Criteria:**
- All CRUD operations working
- Search returns results in < 200ms for 10k patients
- Tests pass with 90%+ coverage

### Task 2.2: Patient UI
**Status:** Pending
**Ralph Loop:** Yes - "Create patient list and profile pages"
**Max Iterations:** 30

- [ ] Create patient list page (src/ui/pages/patient_list.py)
- [ ] Implement search bar with instant results
- [ ] Create patient card component
- [ ] Implement infinite scroll / pagination
- [ ] Create patient profile page
- [ ] Implement patient timeline
- [ ] Add new patient dialog
- [ ] Add edit patient functionality

**Verification:**
- Visual inspection
- User testing

**Completion Criteria:**
- Search is instant (< 100ms feedback)
- List scrolls smoothly
- All patient details visible
- Edit flow intuitive

### Task 2.3: Appointment Service
**Status:** Pending
**Ralph Loop:** Yes - "Implement appointment booking with conflict detection"
**Max Iterations:** 40

- [ ] Create src/services/appointment_service.py
- [ ] Implement slot availability calculation
- [ ] Implement appointment creation
- [ ] Implement conflict detection
- [ ] Implement appointment update
- [ ] Implement appointment cancellation
- [ ] Implement recurring appointments
- [ ] Add appointment status management
- [ ] Write comprehensive tests

**Verification:**
```bash
pytest tests/test_services/test_appointment_service.py -v
```

**Completion Criteria:**
- Booking works correctly
- No double bookings possible
- Recurring appointments created correctly
- All edge cases handled

### Task 2.4: Calendar UI
**Status:** Pending
**Ralph Loop:** Yes - "Create calendar view with interactions"
**Max Iterations:** 50

- [ ] Create calendar view page (src/ui/pages/calendar_view.py)
- [ ] Implement day view
- [ ] Implement week view
- [ ] Implement month view (overview)
- [ ] Create appointment card component
- [ ] Implement drag-and-drop rescheduling
- [ ] Implement click to book
- [ ] Add appointment detail popup
- [ ] Add color coding by status/type

**Verification:**
- Visual inspection
- User testing

**Completion Criteria:**
- Calendar renders correctly
- All views work
- Interactions feel natural
- Performance is smooth

### Task 2.5: Dashboard
**Status:** Pending
**Ralph Loop:** Yes - "Build dashboard with all widgets"
**Max Iterations:** 30

- [ ] Create dashboard page (src/ui/pages/dashboard.py)
- [ ] Implement today's schedule widget
- [ ] Implement metrics cards (patients, revenue, etc.)
- [ ] Create quick actions section
- [ ] Add upcoming appointments widget
- [ ] Add recent activity feed
- [ ] Implement real-time updates

**Verification:**
- Visual inspection
- Data accuracy verification

**Completion Criteria:**
- Dashboard loads in < 1 second
- All metrics accurate
- Widgets update in real-time
- Premium look and feel

---

## Phase 3: Billing & Analytics

### Task 3.1: Service Catalog
**Status:** Pending
**Ralph Loop:** Yes - "Implement service catalog management"
**Max Iterations:** 20

- [ ] Create service management in settings
- [ ] Implement CRUD for services
- [ ] Add category support
- [ ] Implement pricing with tax
- [ ] Add service search

**Verification:**
```bash
pytest tests/test_services/test_service_catalog.py -v
```

### Task 3.2: Billing Service
**Status:** Pending
**Ralph Loop:** Yes - "Implement billing with invoice generation"
**Max Iterations:** 35

- [ ] Create src/services/billing_service.py
- [ ] Implement invoice creation
- [ ] Implement invoice number generation
- [ ] Implement line item management
- [ ] Implement tax calculation
- [ ] Implement discount application
- [ ] Implement payment recording
- [ ] Implement invoice PDF generation
- [ ] Implement UPI QR code generation

**Verification:**
```bash
pytest tests/test_services/test_billing_service.py -v
```

**Completion Criteria:**
- Invoices generate correctly
- PDF looks professional
- UPI QR works
- All calculations accurate

### Task 3.3: Billing UI
**Status:** Pending
**Ralph Loop:** Yes - "Create billing interface"
**Max Iterations:** 30

- [ ] Create billing page (src/ui/pages/billing.py)
- [ ] Implement invoice creation flow
- [ ] Create invoice list view
- [ ] Implement payment recording UI
- [ ] Add print functionality
- [ ] Add PDF download

**Verification:**
- Visual inspection
- End-to-end billing test

### Task 3.4: Analytics Service
**Status:** Pending
**Ralph Loop:** Yes - "Implement analytics calculations"
**Max Iterations:** 30

- [ ] Create src/services/analytics_service.py
- [ ] Implement revenue analytics
- [ ] Implement patient analytics
- [ ] Implement appointment analytics
- [ ] Implement trends calculation
- [ ] Implement forecasting (simple)
- [ ] Write tests with sample data

**Verification:**
```bash
pytest tests/test_services/test_analytics_service.py -v
```

### Task 3.5: Analytics UI
**Status:** Pending
**Ralph Loop:** Yes - "Create analytics dashboard"
**Max Iterations:** 40

- [ ] Create analytics page (src/ui/pages/analytics.py)
- [ ] Implement revenue charts
- [ ] Implement patient charts
- [ ] Implement date range selector
- [ ] Add export functionality
- [ ] Create report templates

**Verification:**
- Visual inspection
- Chart accuracy verification

---

## Phase 4: Voice Agent

### Task 4.1: Audio Infrastructure
**Status:** Pending
**Ralph Loop:** Yes - "Set up audio I/O with Whisper"
**Max Iterations:** 25

- [ ] Create src/voice/__init__.py
- [ ] Implement audio capture (src/voice/audio_capture.py)
- [ ] Integrate Whisper for STT
- [ ] Integrate Piper for TTS
- [ ] Handle audio device selection
- [ ] Test on various hardware

**Verification:**
```bash
pytest tests/test_voice/test_audio.py -v
```

### Task 4.2: Wake Word Detection
**Status:** Pending
**Ralph Loop:** Yes - "Implement wake word detection"
**Max Iterations:** 20

- [ ] Create src/voice/wake_word.py
- [ ] Integrate openwakeword
- [ ] Train custom "Hey DocAssist" model
- [ ] Implement detection loop
- [ ] Add visual/audio feedback

**Verification:**
- Manual testing with wake word

### Task 4.3: Intent Classification
**Status:** Pending
**Ralph Loop:** Yes - "Implement intent parser with 95% accuracy"
**Max Iterations:** 40

- [ ] Create src/voice/intent_parser.py
- [ ] Create prompt templates (prompts/voice_intent.txt)
- [ ] Implement intent classification with Ollama
- [ ] Implement slot extraction
- [ ] Create test dataset
- [ ] Measure and improve accuracy

**Verification:**
```bash
pytest tests/test_voice/test_intent.py -v
# Target: 95% accuracy on test set
```

**Completion Criteria:**
- 95%+ intent classification accuracy
- All required slots extracted
- Handles variations gracefully

### Task 4.4: Voice Action Handler
**Status:** Pending
**Ralph Loop:** Yes - "Implement voice command execution"
**Max Iterations:** 35

- [ ] Create src/voice/action_handler.py
- [ ] Implement book_appointment action
- [ ] Implement cancel_appointment action
- [ ] Implement reschedule_appointment action
- [ ] Implement schedule query actions
- [ ] Implement confirmation flow
- [ ] Add multi-turn dialogue support

**Verification:**
```bash
pytest tests/test_voice/test_actions.py -v
```

### Task 4.5: Voice UI Integration
**Status:** Pending
**Ralph Loop:** Yes - "Integrate voice agent with UI"
**Max Iterations:** 25

- [ ] Create voice indicator component
- [ ] Add voice button to UI
- [ ] Implement listening state
- [ ] Show transcription in real-time
- [ ] Display confirmation dialogs
- [ ] Handle errors gracefully

**Verification:**
- End-to-end voice booking test

---

## Phase 5: Integration & Polish

### Task 5.1: EMR Sync Service
**Status:** Pending
**Ralph Loop:** Yes - "Implement EMR synchronization"
**Max Iterations:** 35

- [ ] Create src/integrations/emr_bridge.py
- [ ] Implement database change detection
- [ ] Implement patient sync (EMR → PM)
- [ ] Implement appointment visibility (PM → EMR)
- [ ] Handle conflicts gracefully
- [ ] Add sync status UI

**Verification:**
```bash
pytest tests/test_integrations/test_emr_bridge.py -v
```

**Completion Criteria:**
- Patient data syncs correctly
- No data loss during sync
- Conflict resolution works
- Sync is efficient (only changed data)

### Task 5.2: Notification Service
**Status:** Pending
**Ralph Loop:** Yes - "Implement SMS and WhatsApp notifications"
**Max Iterations:** 30

- [ ] Create src/services/notification_service.py
- [ ] Integrate SMS gateway
- [ ] Integrate WhatsApp Business API
- [ ] Implement notification scheduling
- [ ] Create message templates
- [ ] Add notification history

**Verification:**
```bash
pytest tests/test_services/test_notification_service.py -v
```

### Task 5.3: Authentication & Authorization
**Status:** Pending
**Ralph Loop:** Yes - "Implement auth with RBAC"
**Max Iterations:** 30

- [ ] Create src/services/auth_service.py
- [ ] Implement login flow
- [ ] Implement role-based access control
- [ ] Add session management
- [ ] Implement audit logging
- [ ] Create user management UI

**Verification:**
```bash
pytest tests/test_services/test_auth_service.py -v
```

### Task 5.4: Settings Page
**Status:** Pending
**Ralph Loop:** Yes - "Create comprehensive settings"
**Max Iterations:** 25

- [ ] Create settings page (src/ui/pages/settings.py)
- [ ] Add clinic profile settings
- [ ] Add doctor management
- [ ] Add staff management
- [ ] Add service catalog management
- [ ] Add notification settings
- [ ] Add system settings

### Task 5.5: Performance Optimization
**Status:** Pending
**Ralph Loop:** Yes - "Optimize for performance targets"
**Max Iterations:** 30

- [ ] Profile application startup
- [ ] Optimize database queries
- [ ] Add caching where appropriate
- [ ] Optimize UI rendering
- [ ] Reduce memory footprint
- [ ] Test on minimum spec hardware

**Verification:**
- App launches in < 2 seconds
- All operations meet latency targets

### Task 5.6: Final Testing & Documentation
**Status:** Pending
**Ralph Loop:** Not required

- [ ] Run full test suite
- [ ] Fix any failing tests
- [ ] Write API documentation
- [ ] Create user guide
- [ ] Prepare release notes

---

## Ralph Wiggum Command Templates

### Starting a Feature
```
/ralph-loop Implement [feature] following specs in speckit.specify.md.
Completion: All tests pass and feature works as specified.
Max iterations: 30
```

### Resuming After Context Reset
```
/ralph-loop Continue implementing [feature] from speckit.tasks.md.
Check git log and test results for current state.
Complete remaining items until all tests pass.
Max iterations: 20
```

---

*Update this task list as work progresses. Check boxes and update status.*

**Last Updated:** 2026-01-03
**Version:** 1.0
