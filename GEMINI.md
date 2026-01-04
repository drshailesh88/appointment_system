# DocAssist Practice Manager - Development Instructions

## 🎯 Mission: Kill Practo, HealthPlix & PM Cardio

DocAssist Practice Manager is a premium appointment scheduling and practice management system for Indian doctors. It integrates seamlessly with [DocAssist EMR](https://github.com/drshailesh88/emr) to provide a complete digital practice solution that BEATS Practo, HealthPlix, and PM Cardio.

**Core Differentiators:**
- 100% offline-first (works without internet)
- AI-powered voice scheduling in 23 Indian languages
- Seamless EMR integration (not a separate silo)
- No per-seat licensing (one-time purchase)
- Doctor-owned data (no cloud lock-in)

**Product Relationship:**
- **EMR** = Doctor's clinical tool (notes, prescriptions, diagnosis) - https://github.com/drshailesh88/emr
- **Practice Manager** = Front desk + patient engagement (scheduling, payments, reminders, analytics)

---

## ⚠️ MANDATORY: Development Toolkits (NEVER FORGET)

> **CRITICAL**: These toolkits MUST be used for ALL development. No exceptions.
> This applies across ALL context windows and sessions.

### 1. Spec-Kit (Spec-Driven Development) - USE FIRST
**Source:** https://github.com/github/spec-kit

**BEFORE writing ANY code, run this workflow:**

```
Step 1: /speckit.specify    → Define WHAT to build (requirements)
Step 2: /speckit.clarify    → Resolve ambiguities
Step 3: /speckit.plan       → Technical architecture
Step 4: /speckit.tasks      → Break into actionable items
Step 5: /speckit.implement  → Execute the development
Step 6: /speckit.analyze    → Validate consistency
```

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/speckit.constitution` | Core governance and constraints | Project setup |
| `/speckit.specify` | Define WHAT to build (not how) | Every new feature |
| `/speckit.clarify` | Resolve underspecified areas | Before planning |
| `/speckit.plan` | Technical architecture decisions | After requirements |
| `/speckit.tasks` | Break into actionable items | Before coding |
| `/speckit.implement` | Execute the development | Build phase |
| `/speckit.analyze` | Cross-artifact consistency check | After tasks |
| `/speckit.checklist` | Quality validation checklist | Before commit |

**Spec-Kit Documents Location:** `.claude/commands/speckit.*.md`

### 2. Ralph Wiggum (Iterative Development Loop) - USE FOR COMPLEX TASKS
**Source:** https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum

For any task with clear completion criteria:

```bash
/ralph-loop "Your task description" --completion-promise "Tests pass" --max-iterations 50
```

**How It Works:**
1. You issue the command once
2. Claude works on the task
3. Stop hook blocks exit and re-feeds the prompt
4. Loop continues until completion criteria met
5. Each iteration sees previous work in files/git

**When to Use Ralph:**
- ✅ Tasks with testable completion (tests pass, build succeeds)
- ✅ Greenfield implementations
- ✅ Refactoring with test validation
- ✅ Multi-step implementations
- ❌ Tasks needing human judgment
- ❌ Unclear success metrics

**Ralph Loop Command:** `.claude/commands/ralph-loop.md`

### 3. Workflow Decision Tree

```
New Feature Request?
    ↓
    /speckit.specify → Define requirements
    ↓
    /speckit.plan → Technical approach
    ↓
    /speckit.tasks → Break into items
    ↓
Is task complex with clear tests?
    ├── YES → /ralph-loop "task" --completion-promise "Tests pass"
    └── NO → Implement directly with /speckit.implement
```

---

## 📋 Complete Implementation Roadmap

### Completed Phases (1-7) ✅

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Voice Agent (Chatterbox TTS, 23 languages) | ✅ DONE |
| 2 | RAG Search (Qdrant, hybrid search) | ✅ DONE |
| 3 | Analytics Dashboard | ✅ DONE |
| 4 | Waitlist Management | ✅ DONE |
| 5 | WhatsApp Bot | ✅ DONE |
| 6 | Mobile App Enhancements | ✅ DONE |
| 7 | Real-Time & Push Notifications | ✅ DONE |

### Phase 8: Reports & Exports 🔄 NEXT
**Goal:** Professional PDF/Excel reports for compliance and analysis

- [ ] PDF report generation using [fpdf2](https://github.com/py-pdf/fpdf2)
- [ ] Excel export with pandas + openpyxl
- [ ] Branded report templates (clinic logo, letterhead)
- [ ] Scheduled report emails
- [ ] Custom date range reports
- [ ] Print-ready formats

**Open Source:** [html-to-pdf-microservice](https://github.com/josmanuelsandrea/html-to-pdf-microservice), [pdf_reports](https://github.com/Edinburgh-Genome-Foundry/pdf_reports)

### Phase 9: Procedure & Intervention Tracking 🔄
**Goal:** Let ANY specialty track their procedures (not just cardiologists)

- [ ] Flexible Procedure model (category, type, subtype)
- [ ] Consumables tracking (stent brand, implant details)
- [ ] Outcome recording (successful, partial, referred)
- [ ] Procedure analytics ("How many echos this month?")
- [ ] Specialty-specific dashboards
- [ ] ICD/CPT code support for billing

**Use Cases:**
- Cardiologist: Echos, Angioplasties, Stents, Pacemakers
- Orthopedist: Surgeries, Fracture fixations, Joint replacements
- Ophthalmologist: Cataract surgeries, LASIK, Injections
- Dermatologist: Biopsies, Procedures, Laser treatments
- Any specialty: Custom procedure types

### Phase 10: Document Scanner & OCR 📱
**Goal:** Scan patient records at reception, sync to EMR

- [ ] Integrate [OpenScan](https://github.com/ethereal-developers/OpenScan) into Flutter
- [ ] Edge detection and auto-crop
- [ ] Multi-page document scanning
- [ ] OCR using Tesseract/EasyOCR (Hindi + English)
- [ ] Extract structured data (patient name, date, values)
- [ ] Push scanned docs to EMR SQLite
- [ ] Link documents to patient records

**Open Source:** [OpenScan](https://github.com/ethereal-developers/OpenScan), [OneScan](https://github.com/sparsh308/OneScan-Document-Scanner-Flutter-App)

### Phase 11: Google Calendar Sync 📅
**Goal:** Doctors see appointments in their personal calendar

- [ ] Google OAuth integration
- [ ] Bidirectional sync using [gcal_sync](https://github.com/allenporter/gcal_sync)
- [ ] Recurring appointment support
- [ ] Calendar event with patient details
- [ ] Conflict detection
- [ ] Multi-calendar support (personal + clinic)

**Open Source:** [gcal_sync](https://github.com/allenporter/gcal_sync), [google-calendar-simple-api](https://github.com/kuzmoyev/google-calendar-simple-api)

### Phase 12: Patient Booking Portal 🌐
**Goal:** Patients book online like Practo (but without the platform fee)

- [ ] Public web portal (Next.js/React)
- [ ] Doctor discovery by specialty/location
- [ ] Real-time slot availability
- [ ] Online payment (Razorpay)
- [ ] Appointment confirmation emails
- [ ] Patient login/history view
- [ ] Embedded widget for clinic websites

**Open Source:** Fork [healthcare-appointment-scheduling-app](https://github.com/Project-Based-Learning-IT/healthcare-appointment-scheduling-app)

### Phase 13: Advanced EMR Integration 🔗
**Goal:** Seamless data flow between Practice Manager and EMR

- [ ] Real-time sync (not just file watcher)
- [ ] Prescription sharing from EMR
- [ ] Lab result display
- [ ] Visit history in appointment view
- [ ] Clinical notes preview (read-only)
- [ ] Patient timeline (appointments + visits + procedures)

**EMR Repo:** https://github.com/drshailesh88/emr

### Phase 14: Insurance & Billing 💳
**Goal:** Complete billing workflow with insurance support

- [ ] Insurance company database
- [ ] Pre-authorization workflow
- [ ] Claim submission tracking
- [ ] TPA integration
- [ ] CGST/SGST/IGST compliance (already partial)
- [ ] Receipt printing
- [ ] Payment reminders

### Phase 15: Multi-Location & Staff Management 🏥
**Goal:** Scale from single clinic to hospital chain

- [ ] Multi-branch support
- [ ] Staff role management
- [ ] Cross-location patient records
- [ ] Consolidated analytics
- [ ] Branch-specific settings
- [ ] Staff performance metrics

---

## 🛠️ Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Backend | FastAPI + Python 3.11+ | Type hints mandatory |
| Mobile | Flutter + Riverpod | Offline-first with sync |
| Web Portal | Next.js + React | Patient booking (Phase 12) |
| Database | PostgreSQL (prod) / SQLite (dev) | SQLAlchemy ORM |
| Vectors | Qdrant | RAG for patient search |
| LLM | Ollama + Qwen2.5 | Local inference |
| Voice STT | Whisper (faster-whisper) | Local speech-to-text |
| Voice TTS | Chatterbox | Voice cloning, emotions, 23 languages |
| Payments | Razorpay | UPI, cards, wallets |
| SMS | MSG91 | India-focused |
| PDF | fpdf2 + WeasyPrint | Report generation |
| Excel | pandas + openpyxl | Export analytics |
| Calendar | gcal_sync | Google Calendar API |
| OCR | Tesseract / EasyOCR | Document scanning |

### Forbidden Technologies
- Electron (too heavy)
- Cloud-only databases (must work offline)
- Proprietary voice APIs (ElevenLabs, etc.)
- Per-seat licensed software
- Closed-source dependencies for core features

---

## 📁 Project Structure

```
appointment_system/
├── .claude/commands/          # Spec-Kit & Ralph commands
├── backend/
│   ├── app/
│   │   ├── api/v1/            # REST endpoints
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── voice/             # Voice agent (STT, TTS, NLU)
│   │   └── integrations/      # EMR, SMS, Razorpay, Calendar
│   ├── tests/                 # Pytest tests
│   └── alembic/               # Database migrations
├── mobile/
│   └── lib/
│       ├── core/              # Models, providers, services
│       └── features/          # UI screens
├── web/                       # Patient booking portal (Phase 12)
│   └── src/
└── docs/                      # Documentation
```

---

## 🔗 EMR Integration Architecture

Practice Manager integrates with DocAssist EMR via SQLite:

| Data Flow | Direction | Description |
|-----------|-----------|-------------|
| Patients | EMR → PM | Read patient data (no duplication) |
| Appointments | PM ↔ EMR | Bidirectional sync |
| Visits | EMR → PM | Link visit to appointment after consultation |
| Procedures | PM → EMR | Sync procedure records |
| Documents | PM → EMR | Push scanned documents |
| Clinical Notes | EMR only | Stay in EMR, never copied |

**EMR Database Path:** `data/clinic.db` (configurable via ENV)
**Integration Code:** `backend/app/integrations/emr.py`

---

## ✅ Critical Implementation Rules

### 1. ALWAYS Use Spec-Kit First
```bash
/speckit.specify   # Define requirements
/speckit.plan      # Technical approach
/speckit.tasks     # Break into tasks
```

### 2. Use Ralph for Complex Tasks
```bash
/ralph-loop "Implement X with tests" --completion-promise "All tests pass" --max-iterations 50
```

### 3. Draft Mode for AI Output
```python
# AI suggestions require explicit confirmation
ai_suggestion = llm.generate(prompt)
show_draft_dialog(ai_suggestion, on_confirm=db.save)
```

### 4. Offline-First Design
- All core features work without internet
- Gracefully handle missing Ollama
- Local data storage with sync queue
- No cloud telemetry

### 5. Test Before Commit
```bash
pytest tests/ -v --cov=app
mypy app/ --strict
ruff check app/
```

---

## ⚡ Performance Targets

| Operation | Target |
|-----------|--------|
| App launch | < 2 seconds |
| Appointment booking | < 500ms |
| Search results | < 200ms |
| Voice recognition | < 1 second |
| TTS response | < 500ms |
| Document scan | < 3 seconds |
| PDF generation | < 2 seconds |

---

## 📚 Open Source Libraries to Use

| Need | Library | URL |
|------|---------|-----|
| PDF Reports | fpdf2 | https://github.com/py-pdf/fpdf2 |
| HTML→PDF | WeasyPrint | https://github.com/josmanuelsandrea/html-to-pdf-microservice |
| Beautiful Reports | pdf_reports | https://github.com/Edinburgh-Genome-Foundry/pdf_reports |
| Google Calendar | gcal_sync | https://github.com/allenporter/gcal_sync |
| Document Scanner | OpenScan | https://github.com/ethereal-developers/OpenScan |
| OCR Flutter | OneScan | https://github.com/sparsh308/OneScan-Document-Scanner-Flutter-App |
| Booking Portal | Fork this | https://github.com/Project-Based-Learning-IT/healthcare-appointment-scheduling-app |
| Healthcare Reference | awesome-healthcare | https://github.com/kakoni/awesome-healthcare |

---

## 🏆 Competitive Targets

| Competitor | Their Weakness | Our Advantage |
|------------|----------------|---------------|
| **Practo** | Platform fees, data lock-in | Doctor-owned data, no fees |
| **HealthPlix** | Cloud-only, expensive | Offline-first, affordable |
| **PM Cardio** | Cardiology-only | All specialties supported |
| **Generic EMRs** | Separate from practice mgmt | Seamless EMR integration |

---

## 🔑 Key References

| Resource | URL | Purpose |
|----------|-----|---------|
| Spec-Kit | https://github.com/github/spec-kit | Spec-driven development |
| Ralph Wiggum | https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum | Iterative loops |
| DocAssist EMR | https://github.com/drshailesh88/emr | Parent EMR system |
| Chatterbox TTS | https://github.com/resemble-ai/chatterbox | Voice synthesis |
| awesome-healthcare | https://github.com/kakoni/awesome-healthcare | Healthcare OSS reference |
| awesome-llm-apps | https://github.com/Shubhamsaboo/awesome-llm-apps | Voice agents, RAG patterns |

---

## 📝 Documentation Sync

**IMPORTANT:** Changes to these instructions must be replicated across:
- `CLAUDE.md` (this file)
- `AGENTS.md`
- `CODEX.md`
- `GEMINI.md`
- `GROK.md`

---

*Last Updated: 2026-01-04*
*Version: 2.0 - Practo Killer Edition*
