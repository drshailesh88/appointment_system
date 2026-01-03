# DocAssist Practice Manager - Constitution

## Project Identity

**Name:** DocAssist Practice Manager
**Codename:** PracticeHub
**Vision:** The Apple of medical practice management - premium, intuitive, indispensable

## Core Principles

### 1. Premium Experience Above All
Every interaction must feel crafted, intentional, and delightful. We build software that doctors LOVE to use, not just tolerate. The bar is Apple, not enterprise software.

### 2. Offline-First, Always Available
Like our sister EMR product, this system must work flawlessly without internet. Doctors in rural clinics deserve the same experience as those in metro hospitals.

### 3. Seamless Integration
This is not a standalone product - it is the practice management arm of the DocAssist ecosystem. Integration with DocAssist EMR is not an afterthought; it's foundational.

### 4. AI-Native, Human-Controlled
AI assists everywhere - voice scheduling, smart analytics, predictive insights. But doctors always have final control. Every AI action requires explicit confirmation.

### 5. Privacy by Design
All patient data stays local. No cloud telemetry. No data monetization. Doctors own their data, period.

### 6. Indian Context First
Built for Indian doctors, Indian patients, Indian workflows. UPI payments, Aadhaar integration, regional languages, SMS over email, WhatsApp integration.

---

## Technical Constitution

### Mandated Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Language | Python 3.11+ | Consistency with EMR, rich ML ecosystem |
| UI Framework | Flet | Cross-platform, Python-native, modern |
| Database | SQLite | Offline-first, embedded, battle-tested |
| Vector Store | ChromaDB | Local RAG capabilities |
| Voice AI | Whisper (local) + LLM | Offline voice processing |
| LLM Runtime | Ollama | Local inference, no cloud dependency |
| API Layer | FastAPI | For integrations and future mobile apps |

### Forbidden Technologies
- Electron (too heavy for target hardware)
- Cloud-only databases
- Proprietary voice APIs requiring internet
- Any technology requiring license fees per seat

### Integration Standards
- EMR integration via shared SQLite + IPC
- Standard REST API for third-party integrations
- Webhook support for notifications
- HL7 FHIR readiness for future compliance

---

## Development Constitution

### Spec-Driven Development (Spec-Kit)
All development follows the Spec-Kit workflow:
1. `/speckit.constitution` - Establish principles (this document)
2. `/speckit.specify` - Define requirements before code
3. `/speckit.plan` - Create technical implementation plans
4. `/speckit.tasks` - Generate actionable task lists
5. `/speckit.implement` - Execute with Ralph Wiggum loops

### Ralph Wiggum Iterative Development
Every significant feature uses Ralph loops:
- Clear completion criteria before starting
- Automated verification (tests must pass)
- Git commits at each iteration
- Maximum 50 iterations per feature
- Self-correction through test feedback

### Code Standards
- Type hints mandatory (mypy strict mode)
- Docstrings for all public APIs
- 80%+ test coverage minimum
- Pydantic for all data validation
- Async where appropriate (especially UI)

### Documentation Synchronization
Changes to project instructions must be replicated across:
- CLAUDE.md
- AGENTS.md
- CODEX.md
- GEMINI.md
- GROK.md

---

## Product Constitution

### Target Users
1. **Primary:** Solo practitioners and small clinics (1-3 doctors)
2. **Secondary:** Multi-specialty clinics (4-10 doctors)
3. **Future:** Hospital OPD departments

### Core Value Propositions
1. **Time Savings:** 30+ minutes saved daily on admin tasks
2. **Revenue Visibility:** Real-time practice revenue tracking
3. **Patient Experience:** Reduced wait times, seamless scheduling
4. **Professional Growth:** Analytics to grow the practice

### Pricing Philosophy
- Freemium base (essential features free forever)
- Premium features via subscription (analytics, voice agent)
- No per-patient fees (unlike competitors)
- Annual discounts for commitment

---

## Quality Bar

### Performance Requirements
- App launch: < 2 seconds
- Appointment booking: < 500ms
- Search results: < 200ms
- Voice command recognition: < 1 second

### Reliability Requirements
- Zero data loss guarantee
- 99.9% uptime for local operations
- Graceful degradation without LLM
- Automatic backup to local storage

### Accessibility Requirements
- High contrast mode for aging doctors
- Large touch targets for tablet use
- Voice control for hands-free operation
- Support for Hindi + 4 regional languages

---

## Success Metrics

### North Star Metric
**Daily Active Usage Rate:** % of registered doctors using app daily

### Supporting Metrics
- Appointments booked per day
- Average time to book appointment
- Practice revenue tracked accurately
- Net Promoter Score (NPS) > 50

---

## Red Lines (Never Cross)

1. **Never** send patient data to any external server
2. **Never** require internet for core functionality
3. **Never** auto-save AI-generated content without confirmation
4. **Never** lock doctors out of their own data
5. **Never** make the free tier unusable

---

*This constitution guides all product and technical decisions. When in doubt, refer here.*

**Last Updated:** 2026-01-03
**Version:** 1.0
