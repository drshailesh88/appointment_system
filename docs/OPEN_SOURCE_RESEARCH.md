# Open Source Projects Research

Comprehensive research on GitHub open source projects that can be incorporated into DocAssist Practice Manager.

---

## 1. Appointment Scheduling Systems

### Recommended: django-appointment
**Repository:** [adamspd/django-appointment](https://github.com/adamspd/django-appointment)
**Stars:** 256+ | **License:** MIT | **Last Updated:** January 2026

A Django app for managing appointment scheduling with ease and flexibility.

**Key Features:**
- Customizable time slots, lead time, and finish time
- Conflict handling and availability management
- Automated email reminders (24h before via Django Q)
- ICS file attachment for calendar sync
- Rescheduling support

**Use Case:** Can extract scheduling logic and adapt for our Flet UI.

---

### Other Options:

| Project | Description | Link |
|---------|-------------|------|
| **pyappointment** | Django + Cronofy calendar integration | [mdave/pyappointment](https://github.com/mdave/pyappointment) |
| **flask-appointment-calendar** | Simple Flask-based scheduler | [wpic/flask-appointment-calendar](https://github.com/wpic/flask-appointment-calendar) |
| **Easy!Appointments** | Popular PHP scheduler (reference only) | [alextselegidis/easyappointments](https://github.com/alextselegidis/easyappointments) |
| **DaySchedule Widget** | Embeddable booking widget | [dayschedule/dayschedule-widget](https://github.com/dayschedule/dayschedule-widget) |

---

## 2. Medical Practice Management / EMR

### Reference Projects:

| Project | Description | Tech Stack | Link |
|---------|-------------|------------|------|
| **OpenEMR** | Most popular open source EMR | PHP | [openemr/openemr](https://github.com/openemr/openemr) |
| **Danphe EMR** | Enterprise hospital management (60+ hospitals) | ASP.NET, Angular | [opensource-emr/hospital-management-emr](https://github.com/opensource-emr/hospital-management-emr) |
| **Medplum** | Healthcare developer platform (FHIR) | TypeScript | [medplum/medplum](https://github.com/medplum) |
| **OPAL** | Python healthcare framework | Python/Django | [opal.openhealthcare.org.uk](https://opal.openhealthcare.org.uk/) |

### Curated Lists:
- **[kakoni/awesome-healthcare](https://github.com/kakoni/awesome-healthcare)** - Comprehensive healthcare software list
- **[medtorch/awesome-healthcare-ai](https://github.com/medtorch/awesome-healthcare-ai)** - Healthcare AI tools and datasets
- **[NeovaHealth/awesome-health](https://github.com/NeovaHealth/awesome-health)** - Open health software resources

---

## 3. Voice Agent Components

### Speech-to-Text (STT)

#### Recommended: faster-whisper
**Repository:** [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)
**Stars:** 10k+ | **License:** MIT

**Why This One:**
- 4x faster than original Whisper with same accuracy
- Lower memory usage
- 8-bit quantization support (CPU & GPU)
- Silero VAD integration for silence removal
- Batched transcription support
- No FFmpeg dependency

```python
from faster_whisper import WhisperModel
model = WhisperModel("base.en", device="cpu", compute_type="int8")
segments, info = model.transcribe("audio.mp3")
```

#### Related Projects:
| Project | Description | Link |
|---------|-------------|------|
| **WhisperX** | Word-level timestamps + speaker diarization | [m-bain/whisperX](https://github.com/m-bain/whisperX) |
| **WhisperLive** | Real-time streaming transcription | [collabora/WhisperLive](https://github.com/collabora/WhisperLive) |
| **whisper-writer** | Dictation app with faster-whisper | [savbell/whisper-writer](https://github.com/savbell/whisper-writer) |

---

### Text-to-Speech (TTS)

#### Recommended: Piper TTS
**Repository:** [rhasspy/piper](https://github.com/rhasspy/piper)
**Stars:** 5k+ | **License:** MIT

**Why This One:**
- Fast, local neural TTS
- Works offline (no cloud dependency)
- Low latency
- Multiple voice options
- Raspberry Pi compatible

```bash
pip install piper-tts
echo 'Welcome!' | piper --model en_US-lessac-medium --output_file welcome.wav
```

---

### Wake Word Detection

#### Recommended: openWakeWord
**Repository:** [dscripka/openWakeWord](https://github.com/dscripka/openWakeWord)
**Stars:** 500+ | **License:** Apache 2.0

**Why This One:**
- Trained on 100% synthetic data (no manual collection)
- Easy to train custom wake words
- Minimal dependencies
- Silero VAD integration
- Pre-trained models available ("hey jarvis", etc.)

```python
import openwakeword
from openwakeword.model import Model

model = Model(wakeword_models=["hey_jarvis"])
prediction = model.predict(audio_frame)
```

---

### Complete Voice Assistants (Reference)

| Project | Description | Link |
|---------|-------------|------|
| **Local-Talking-LLM** | Whisper + Ollama + Bark, fully offline | [vndee/local-talking-llm](https://github.com/vndee/local-talking-llm) |
| **Local-Voice** | Linux/RPi assistant with Vosk + Piper + Ollama | [m15-ai/Local-Voice](https://github.com/m15-ai/Local-Voice) |
| **GPT4ALL Voice Assistant** | 100% offline with GPT4ALL | [Ai-Austin/GPT4ALL-Voice-Assistant](https://github.com/Ai-Austin/GPT4ALL-Voice-Assistant) |
| **whisper-voice-assistant** | Porcupine wake word + Whisper | [garbit/whisper-voice-assistant](https://github.com/garbit/whisper-voice-assistant) |

---

## 4. Intent Classification / NLU

### Recommended: Snips NLU (Offline)
**Repository:** [snipsco/snips-nlu](https://github.com/snipsco/snips-nlu)
**License:** Apache 2.0

**Why This One:**
- Runs completely offline
- Low memory (100-200MB RAM)
- Intent + slot extraction
- Pre-built binaries available

**Alternative: Use Ollama + Local LLM**
For our use case, using Ollama with structured prompts may be simpler and more flexible than training a separate NLU model.

### Other Options:
| Project | Description | Link |
|---------|-------------|------|
| **Rasa NLU** | Full-featured NLU with entity extraction | [RasaHQ/rasa](https://github.com/RasaHQ/rasa) |
| **SpeechRecognition** | Multi-engine STT library | [Uberi/speech_recognition](https://github.com/Uberi/speech_recognition) |

---

## 5. UI Framework & Components

### Core: Flet
**Repository:** [flet-dev/flet](https://github.com/flet-dev/flet)
**Stars:** 10k+ | **License:** Apache 2.0

**Already in our stack.** Additional resources:

| Resource | Description | Link |
|----------|-------------|------|
| **Flet Examples** | Official sample apps | [flet-dev/examples](https://github.com/flet-dev/examples) |
| **Awesome Flet** | Curated Flet resources | [flet-dev/awesome-flet](https://github.com/flet-dev/awesome-flet) |
| **material_design_flet** | Modern UI components | [LineIndent/material_design_flet](https://github.com/LineIndent/material_design_flet) |
| **fletmint** | Sharp, modern components | Listed in awesome-flet |
| **Flet-Easy** | Router, JWT, middleware | Listed in awesome-flet |

---

## 6. Billing & Invoicing

### Recommended: InvoiceGenerator
**Repository:** [by-cx/InvoiceGenerator](https://github.com/by-cx/InvoiceGenerator)
**License:** BSD

Python library for PDF invoice generation using ReportLab.

```python
from InvoiceGenerator.api import Invoice, Item, Client, Provider
invoice = Invoice(client, provider, creator)
invoice.add_item(Item(32, 600, description="Consultation"))
invoice.generate_to_pdf()
```

### Other Options:
| Project | Description | Link |
|---------|-------------|------|
| **pydf_invoice** | Utility class for PDF invoices | [Simouche/pydf_invoice](https://github.com/Simouche/pydf_invoice) |
| **BilledIn** | Tkinter billing app for SMBs | [mahadev0811/BilledIn](https://github.com/mahadev0811/BilledIn) |
| **SolidInvoice** | Full invoicing platform (PHP) | [SolidInvoice/SolidInvoice](https://github.com/SolidInvoice/SolidInvoice) |

### PDF Generation Libraries:
- **ReportLab** - Industry standard, professional PDFs
- **fpdf2** - Lightweight, already in our requirements
- **weasyprint** - HTML/CSS to PDF

---

## 7. Payment Integration (India)

### Recommended: Razorpay Python SDK
**Repository:** [razorpay/razorpay-python](https://github.com/razorpay/razorpay-python)
**License:** MIT

Official SDK for UPI, cards, netbanking, wallets.

```python
import razorpay
client = razorpay.Client(auth=("key", "secret"))

# Create UPI QR Code
qr = client.qrcode.create({
    "type": "upi_qr",
    "usage": "single_use",
    "fixed_amount": True,
    "payment_amount": 50000,  # in paise
})
```

**Features:**
- UPI QR code generation
- Payment verification
- Refunds
- Subscriptions
- Payment links

### Reference Implementation:
- [episyche/razorpay_django_reactjs_example](https://github.com/episyche/razorpay_django_reactjs_example)

---

## 8. Analytics & Visualization

### Recommended for Embedded Charts: Plotly
**Repository:** [plotly/plotly.py](https://github.com/plotly/plotly.py)

Flet supports embedding Plotly charts via `ft.PlotlyChart()`.

### Dashboard Frameworks (Reference):
| Project | Description | Link |
|---------|-------------|------|
| **Plotly Dash** | Interactive dashboards | [plotly/dash](https://github.com/plotly/dash) |
| **Apache Superset** | BI tool (65k+ stars) | [apache/superset](https://github.com/apache/superset) |
| **Streamlit** | Data apps | [streamlit/streamlit](https://github.com/streamlit/streamlit) |
| **PyGWalker** | Tableau-like in Jupyter | [Kanaries/pygwalker](https://github.com/Kanaries/pygwalker) |

---

## 9. SMS & WhatsApp Integration

### WhatsApp:
| Project | Description | Link |
|---------|-------------|------|
| **whatsapp-api-client-python** | GREEN-API wrapper | [green-api/whatsapp-api-client-python](https://github.com/green-api/whatsapp-api-client-python) |
| **wa-automate-python** | Advanced WhatsApp automation | [open-wa/wa-automate-python](https://github.com/open-wa/wa-automate-python) |

### SMS:
For India, consider:
- **MSG91** - Popular Indian SMS gateway
- **Textlocal** - Indian SMS provider
- Use generic HTTP APIs with `httpx`

---

## 10. LLM Integration

### Recommended: Ollama Python
**Repository:** [ollama/ollama-python](https://github.com/ollama/ollama-python)

Already in our stack. Additional resources:

| Project | Description | Link |
|---------|-------------|------|
| **Langroid** | Multi-agent LLM framework | [langroid/langroid](https://github.com/langroid/langroid) |
| **ollama-langchain-agents** | LangChain + Ollama examples | [shivamr021/ollama-langchain-agents](https://github.com/shivamr021/ollama-langchain-agents) |
| **ollama-adk-python** | Google ADK + Ollama | [mstanton/ollama-adk-python](https://github.com/mstanton/ollama-adk-python) |

---

## 11. Vector Database / RAG

### Already Using: ChromaDB
**Repository:** [chroma-core/chroma](https://github.com/chroma-core/chroma)

Additional RAG resources:
| Project | Description | Link |
|---------|-------------|------|
| **chroma-db-rag** | RAG with reranker | [rupeshtr78/chroma-db-rag](https://github.com/rupeshtr78/chroma-db-rag) |
| **ai-chatbot-with-rag** | Swappable LLM + vector stores | [LiteObject/ai-chatbot-with-rag](https://github.com/LiteObject/ai-chatbot-with-rag) |

---

## 12. Queue Management / Token System

### Reference Projects:
| Project | Description | Link |
|---------|-------------|------|
| **HQMS** | Hospital Queue Management | [camsvn/HQMS](https://github.com/camsvn/HQMS) |
| **hospital-queue** | Online queuing with wait times | [ksuhartono97/hospital-queue](https://github.com/ksuhartono97/hospital-queue) |
| **Queue-Management-System** | Token + QR code + SMS | [yuvisidhu19/Queue-Management-System](https://github.com/yuvisidhu19/Queue-Management-System) |

---

## Priority Integration Recommendations

Based on our requirements, here's the recommended priority:

### High Priority (Immediate Use):
1. **faster-whisper** - Voice STT (replace openai-whisper)
2. **Piper TTS** - Already planned
3. **openWakeWord** - Already planned
4. **Razorpay SDK** - UPI payments
5. **InvoiceGenerator** - PDF invoices

### Medium Priority (Phase 2):
6. **django-appointment** - Extract scheduling algorithms
7. **ChromaDB** - Already in stack
8. **Plotly** - Analytics charts
9. **whatsapp-api-client-python** - WhatsApp notifications

### Reference Only:
- OpenEMR, Danphe EMR - Architecture patterns
- Rasa NLU - If LLM-based NLU proves insufficient
- awesome-healthcare - Feature inspiration

---

## License Compatibility

All recommended projects use permissive licenses compatible with our proprietary product:

| License | Projects |
|---------|----------|
| **MIT** | faster-whisper, Piper, Razorpay SDK, InvoiceGenerator |
| **Apache 2.0** | Flet, openWakeWord, ChromaDB |
| **BSD** | Various Python libraries |

---

*Last Updated: 2026-01-03*
