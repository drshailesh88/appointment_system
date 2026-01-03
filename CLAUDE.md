# DocAssist Practice Manager - Development Instructions

## Project Overview

DocAssist Practice Manager is a premium appointment scheduling and practice management system for Indian doctors. It integrates seamlessly with DocAssist EMR to provide a complete digital practice solution.

**Core Differentiator:** Premium user experience with offline-first operation and AI-powered voice scheduling.

---

## Development Methodology

### Spec-Driven Development (Spec-Kit)

All development follows the Spec-Kit workflow. **ALWAYS** reference these documents:

| Document | Location | Purpose |
|----------|----------|---------|
| Constitution | `.claude/commands/speckit.constitution.md` | Core principles and constraints |
| Specifications | `.claude/commands/speckit.specify.md` | Feature requirements |
| Technical Plan | `.claude/commands/speckit.plan.md` | Architecture and approach |
| Task Breakdown | `.claude/commands/speckit.tasks.md` | Detailed tasks with status |

### Ralph Wiggum Iterative Development

For any significant implementation:
1. Use `/ralph-loop [task]` to start iterative development
2. Work until tests pass and completion criteria met
3. Commit working code at each iteration
4. Self-correct based on test failures

**Ralph Loop Command:** `.claude/commands/ralph-loop.md`

---

## Fixed Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Language | Python 3.11+ | Type hints mandatory |
| UI | Flet | Cross-platform, Python-native |
| Database | SQLite + SQLAlchemy | Offline-first |
| Vectors | ChromaDB | Local RAG |
| LLM | Ollama + Qwen | Local inference |
| Voice STT | Whisper | Local speech-to-text |
| Voice TTS | Piper | Local text-to-speech |
| API | FastAPI | For integrations |

### Forbidden Technologies
- Electron
- Cloud-only databases
- Proprietary voice APIs
- Technologies requiring per-seat licenses

---

## Project Structure

```
docassist-practice-manager/
├── .claude/commands/          # Spec-Kit documents
├── src/
│   ├── models/                # SQLAlchemy models
│   ├── services/              # Business logic
│   ├── ui/                    # Flet UI components
│   │   ├── components/        # Reusable widgets
│   │   └── pages/             # Page views
│   ├── voice/                 # Voice agent
│   └── integrations/          # EMR, SMS, WhatsApp
├── tests/                     # Pytest tests
├── prompts/                   # LLM prompts
├── data/                      # Runtime data (gitignored)
└── docs/                      # Documentation
```

---

## Critical Implementation Rules

### 1. Threading for LLM Operations
All LLM calls MUST run in background threads to prevent UI blocking:
```python
import threading

def async_llm_call(prompt: str, callback: Callable):
    def run():
        result = ollama.generate(model="qwen2.5:3b", prompt=prompt)
        callback(result)
    threading.Thread(target=run, daemon=True).start()
```

### 2. Pydantic Validation
All data models must use Pydantic for validation:
```python
from pydantic import BaseModel, Field

class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: str
    start_time: datetime
    duration_minutes: int = Field(ge=5, le=120)
```

### 3. Draft Mode for AI Output
AI-generated content MUST require explicit confirmation:
```python
# WRONG - auto-saving AI output
ai_suggestion = llm.generate(prompt)
db.save(ai_suggestion)

# CORRECT - require confirmation
ai_suggestion = llm.generate(prompt)
show_draft_dialog(ai_suggestion, on_confirm=db.save)
```

### 4. Offline-First Design
- All core features work without internet
- Gracefully handle missing Ollama
- Local data storage only
- No cloud telemetry

### 5. EMR Integration
- Shared patient data via SQLite
- Read clinical records from EMR (read-only)
- Appointments sync bidirectionally
- Use watchdog for file system sync

---

## Testing Requirements

- Minimum 80% code coverage
- All models must have unit tests
- All services must have integration tests
- Run before every commit:
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

---

## Code Style

- Type hints on all functions
- Docstrings for public APIs
- Max line length: 100 characters
- Use `ruff` and `black` for formatting
- Follow Google Python Style Guide

---

## Documentation Synchronization

**IMPORTANT:** Any changes to these instructions must be replicated across:
- `CLAUDE.md` (this file)
- `AGENTS.md`
- `CODEX.md`
- `GEMINI.md`
- `GROK.md`

---

## Common Commands

```bash
# Run application
python main.py

# Run tests
pytest tests/ -v

# Type checking
mypy src/ --strict

# Lint
ruff check src/

# Format
black src/ tests/

# Install dependencies
pip install -r requirements.txt
```

---

## Getting Help

1. Check Spec-Kit documents for requirements
2. Review existing code patterns
3. Run tests to understand expected behavior
4. Ask for clarification if blocked

---

*Last Updated: 2026-01-03*
