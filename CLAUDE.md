# DocAssist Practice Manager - Development Instructions

## Project Overview

DocAssist Practice Manager is a premium appointment scheduling and practice management system for Indian doctors. It integrates seamlessly with [DocAssist EMR](https://github.com/drshailesh88/emr) to provide a complete digital practice solution.

**Core Differentiator:** Premium user experience with offline-first operation and AI-powered voice scheduling.

**Product Relationship:**
- **EMR** = Doctor's clinical tool (notes, prescriptions, diagnosis)
- **Practice Manager** = Front desk + patient engagement (scheduling, payments, reminders)

---

## MANDATORY Development Toolkits

### 1. Spec-Kit (Spec-Driven Development)
**Source:** https://github.com/github/spec-kit

All development MUST follow the Spec-Kit workflow:

| Phase | Command | Purpose |
|-------|---------|---------|
| 1. Principles | `/speckit.constitution` | Core governance and constraints |
| 2. Requirements | `/speckit.specify` | Define WHAT to build (not how) |
| 3. Planning | `/speckit.plan` | Technical architecture decisions |
| 4. Tasks | `/speckit.tasks` | Break into actionable items |
| 5. Implementation | `/speckit.implement` | Execute the development |
| 6. Validation | `/speckit.clarify` | Resolve ambiguities |

**Spec-Kit Documents Location:** `.claude/commands/speckit.*.md`

### 2. Ralph Wiggum (Iterative Development Loop)
**Source:** https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum

For any significant implementation, use Ralph's iterative loop:

```bash
/ralph-loop "Your task description" --completion-promise "Tests pass"
```

**How Ralph Works:**
1. You issue the command once
2. Claude works on the task
3. Stop hook blocks exit and re-feeds the prompt
4. Loop continues until completion criteria met
5. Each iteration sees previous work in files/git

**When to Use Ralph:**
- Tasks with clear completion criteria (tests pass, build succeeds)
- Greenfield implementations
- Refactoring with test validation
- Any task requiring iterative refinement

**Ralph Loop Command:** `.claude/commands/ralph-loop.md`

---

## Current Implementation Plan

### Phase 1: Voice Agent Upgrade ✅ COMPLETED
- [x] Replace Piper TTS with **Chatterbox** (`pip install chatterbox-tts`)
- [x] Add voice cloning for doctor's personalized voice
- [x] Enable Hindi/regional language support (23 languages)
- [x] Add paralinguistic tags: [laugh], [cough], [chuckle]

**Chatterbox Reference:** https://github.com/resemble-ai/chatterbox

### Phase 2: RAG-Powered Search ✅ COMPLETED
- [x] Add **Qdrant** vector database
- [x] Implement hybrid search (semantic + keyword)
- [x] Enable natural language queries on patient history
- [x] Database routing for patients vs appointments

**RAG Patterns Reference:** https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/rag_tutorials

### Phase 3: Analytics & Reports ✅ COMPLETED
- [x] Daily/weekly/monthly appointment stats
- [x] Doctor utilization reports
- [x] Revenue tracking dashboard
- [x] No-show analytics

### Phase 4: Waitlist Management ✅ COMPLETED
- [x] Queue when slots are full
- [x] Auto-notify when slot opens (SMS/WhatsApp)
- [x] Estimated wait time display
- [x] Priority queue for emergencies

### Phase 5: WhatsApp Bot ✅ COMPLETED
- [x] Two-way booking via WhatsApp
- [x] Appointment reminders
- [x] Payment links
- [x] Prescription sharing

### Phase 6: Mobile App Enhancements ✅ COMPLETED
- [x] Analytics dashboard screens
- [x] Waitlist management UI
- [x] WhatsApp integration settings
- [x] Voice cloning settings for doctors
- [x] Voice booking quick action with backend integration

---

## Next Phase: Advanced Features

### Phase 7: Real-Time & Notifications
- [ ] WebSocket updates for waitlist/appointments
- [ ] Push notifications (FCM) for slot offers
- [ ] Real-time appointment status sync
- [ ] Background sync service

### Phase 8: Advanced Reports & Exports
- [ ] PDF report generation
- [ ] CSV/Excel export for analytics
- [ ] Scheduled report emails
- [ ] Custom date range reports

---

## Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Backend | FastAPI + Python 3.11+ | Type hints mandatory |
| Mobile | Flutter + Riverpod | Offline-first with sync |
| Database | PostgreSQL (prod) / SQLite (dev) | SQLAlchemy ORM |
| Vectors | Qdrant | RAG for patient search |
| LLM | Ollama + Qwen2.5 | Local inference |
| Voice STT | Whisper (faster-whisper) | Local speech-to-text |
| Voice TTS | **Chatterbox** | Voice cloning, emotions, 23 languages |
| Payments | Razorpay | UPI, cards, wallets |
| SMS | MSG91 | India-focused |

### Forbidden Technologies
- Electron
- Cloud-only databases
- Proprietary voice APIs (ElevenLabs, etc.)
- Technologies requiring per-seat licenses

---

## Project Structure

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
│   │   └── integrations/      # EMR, SMS, Razorpay
│   ├── tests/                 # Pytest tests
│   └── alembic/               # Database migrations
├── mobile/
│   └── lib/
│       ├── core/              # Models, providers, services
│       └── features/          # UI screens
└── docs/                      # Documentation
```

---

## EMR Integration

Practice Manager integrates with DocAssist EMR via SQLite:

| Data Flow | Direction | Description |
|-----------|-----------|-------------|
| Patients | EMR → PM | Read patient data (no duplication) |
| Appointments | PM ↔ EMR | Bidirectional sync |
| Visits | EMR → PM | Link visit to appointment after consultation |
| Clinical Notes | EMR only | Stay in EMR, never copied |

**Integration Code:** `backend/app/integrations/emr.py`

---

## Critical Implementation Rules

### 1. Always Use Spec-Kit First
Before coding ANY new feature:
```bash
/speckit.specify   # Define requirements
/speckit.plan      # Technical approach
/speckit.tasks     # Break into tasks
```

### 2. Use Ralph for Complex Tasks
For implementations requiring iteration:
```bash
/ralph-loop "Implement X with tests" --completion-promise "All tests pass"
```

### 3. Draft Mode for AI Output
AI-generated content MUST require explicit confirmation:
```python
# CORRECT - require confirmation
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
pytest tests/ -v --cov=src
mypy src/ --strict
ruff check src/
```

---

## Performance Targets

| Operation | Target |
|-----------|--------|
| App launch | < 2 seconds |
| Appointment booking | < 500ms |
| Search results | < 200ms |
| Voice recognition | < 1 second |
| TTS response | < 500ms |

---

## Key References

| Resource | URL | Purpose |
|----------|-----|---------|
| Spec-Kit | https://github.com/github/spec-kit | Spec-driven development |
| Ralph Wiggum | https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum | Iterative loops |
| Chatterbox TTS | https://github.com/resemble-ai/chatterbox | Voice synthesis |
| awesome-llm-apps | https://github.com/Shubhamsaboo/awesome-llm-apps | Voice agents, RAG patterns |
| DocAssist EMR | https://github.com/drshailesh88/emr | Parent EMR system |

---

## Documentation Synchronization

**IMPORTANT:** Any changes to these instructions must be replicated across:
- `CLAUDE.md` (this file)
- `AGENTS.md`
- `CODEX.md`
- `GEMINI.md`
- `GROK.md`

---

*Last Updated: 2026-01-04*
