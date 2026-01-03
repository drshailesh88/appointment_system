# DocAssist Practice Manager

Premium appointment scheduling and practice management for Indian doctors. Seamlessly integrates with [DocAssist EMR](https://github.com/drshailesh88/emr) for a complete digital practice solution.

## Vision

The Apple of medical practice management - premium, intuitive, indispensable. Software that doctors **love** to use, not just tolerate.

## Features

### Core Modules
- **Appointment Management** - Multi-channel booking (walk-in, phone, online, voice)
- **Patient Registry** - Unified patient database with EMR sync
- **Billing & Payments** - Invoicing, UPI/card payments, GST compliance
- **Practice Analytics** - Revenue, patient, and operational insights
- **Voice Agent** - Hands-free appointment scheduling via voice commands

### Key Differentiators
- **Offline-First** - Works without internet, just like our EMR
- **AI-Powered** - Local LLM for voice commands and smart suggestions
- **Premium UX** - Clean, minimal, delightful interface
- **Indian Context** - UPI, Aadhaar, regional languages, SMS/WhatsApp

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| UI Framework | Flet |
| Database | SQLite + SQLAlchemy |
| Vector Store | ChromaDB |
| LLM Runtime | Ollama + Qwen |
| Voice STT | Whisper (local) |
| Voice TTS | Piper (local) |
| API Layer | FastAPI |

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Ollama (optional, for AI features)

### Installation

```bash
# Clone the repository
git clone https://github.com/drshailesh88/appointment_system.git
cd appointment_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Run the application
python main.py
```

### With Ollama (for AI features)

```bash
# Install Ollama from https://ollama.ai
# Then pull the required model:
ollama pull qwen2.5:3b

# Run the application
python main.py
```

## Development

### Development Methodology

This project uses **Spec-Driven Development** with [Spec-Kit](https://github.com/github/spec-kit) and **iterative AI development** with [Ralph Wiggum](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum).

Key documents:
- `.claude/commands/speckit.constitution.md` - Core principles
- `.claude/commands/speckit.specify.md` - Feature specifications
- `.claude/commands/speckit.plan.md` - Technical architecture
- `.claude/commands/speckit.tasks.md` - Task breakdown

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src

# Run specific test file
pytest tests/test_models/test_patient.py -v

# Type checking
mypy src/ --strict

# Linting
ruff check src/
```

### Project Structure

```
docassist-practice-manager/
├── src/
│   ├── models/          # SQLAlchemy data models
│   ├── services/        # Business logic
│   ├── ui/              # Flet UI components
│   ├── voice/           # Voice agent
│   └── integrations/    # EMR, SMS, WhatsApp
├── tests/               # Pytest test suite
├── prompts/             # LLM prompt templates
├── data/                # Runtime data (gitignored)
└── .claude/commands/    # Spec-Kit documents
```

## EMR Integration

DocAssist Practice Manager integrates with [DocAssist EMR](https://github.com/drshailesh88/emr) via:
- **Shared SQLite database** for patient demographics
- **File system watching** for real-time sync
- **Deep linking** for seamless navigation between apps

Configure the EMR path in `.env`:
```
EMR_DATABASE_PATH=/path/to/emr/clinic.db
```

## Contributing

1. Read the Spec-Kit documents before making changes
2. Follow the development methodology (spec → plan → implement)
3. Ensure tests pass and coverage is maintained
4. Update documentation as needed

## License

Proprietary - All rights reserved.

## Support

For issues and feature requests, please open an issue on GitHub.

---

*Built with care for Indian doctors*
