# Practice AI Assistant - Feature Specification

## Document Info
- **Feature:** Practice AI Assistant
- **Phase:** 16 (New)
- **Status:** Draft
- **Created:** 2026-01-04
- **Author:** Claude + Dr. Shailesh

---

## 1. Executive Summary

### What We're Building
A conversational AI assistant for the Practice Manager that enables natural language interaction with practice data. Unlike the existing voice booking agent (Phase 1), this is a **general-purpose practice assistant** that can answer questions, generate insights, and perform actions across all modules.

### Why It Matters
| Current State | With Practice AI Assistant |
|---------------|---------------------------|
| Click through dashboards to find stats | "How many procedures this month?" → Instant answer |
| Manual report generation | "Email me the weekly summary" → Done |
| Voice agent only books appointments | Voice/chat handles any practice query |
| Each feature is siloed | Unified conversational interface |

### Differentiation from EMR AI
| EMR AI (Clinical) | Practice AI (Operational) |
|-------------------|--------------------------|
| Prescription assistance | Scheduling optimization |
| Diagnosis support | Revenue analytics |
| Clinical note generation | Patient communication |
| Treatment recommendations | Billing queries |

**Clear boundary:** Practice AI does NOT touch clinical decisions. It's for front-desk and practice management only.

---

## 2. Target Users

### Primary: Receptionist
- Needs quick answers while on phone with patients
- "When is Dr. Sharma's next free slot?"
- "How much does this patient owe?"
- "Book a follow-up for the stent patient in 1 week"

### Secondary: Doctor (Practice Owner)
- Wants practice insights on-the-go
- "How's my revenue this month vs last month?"
- "Which procedures are most profitable?"
- "Show me patients who need follow-ups"

### Tertiary: Clinic Manager
- Operational oversight
- "Staff utilization this week?"
- "No-show rate trend?"
- "Generate the GST report"

---

## 3. Feature Modules

### Module A: Natural Language Analytics (P0 - MVP)

#### A.1 Query Understanding
**Description:** Parse natural language questions into structured analytics queries

**Example Queries:**
```
"How many echos this month?"
→ {type: "procedure_count", filter: {procedure_type: "Echo", period: "this_month"}}

"Revenue from Dr. Sharma's patients"
→ {type: "revenue", filter: {doctor: "Dr. Sharma"}}

"Patients who missed follow-ups"
→ {type: "patient_list", filter: {missed_followup: true}}
```

**Supported Query Types:**
| Category | Example Queries |
|----------|-----------------|
| Procedure Analytics | "How many stents?", "Echo count by doctor", "Procedure trend" |
| Revenue Analytics | "Today's collection", "Revenue by service", "Outstanding payments" |
| Appointment Analytics | "No-show rate", "Busiest day", "Average wait time" |
| Patient Analytics | "New patients this week", "Patients by location", "Follow-up due" |

**Functional Requirements:**
- Parse queries in English and Hinglish ("Kitne echo hua is mahine?")
- Handle ambiguous queries with clarification ("Which month do you mean?")
- Support relative dates ("last week", "yesterday", "this quarter")
- Remember context within session ("And for Dr. Sharma?" after revenue query)

**Acceptance Criteria:**
- [ ] 90%+ accuracy on common query patterns
- [ ] Response time < 2 seconds
- [ ] Graceful handling of unknown queries
- [ ] Context maintained for 5+ turns

#### A.2 Response Generation
**Description:** Generate clear, actionable responses from query results

**Response Format:**
```
User: "How many procedures did we do this month?"

AI: "This month you've completed 127 procedures:
     • Cardiology: 68 (54%)
       - Echo: 42
       - ECG: 18
       - Angioplasty: 8
     • Orthopedics: 35 (28%)
     • General: 24 (18%)

     Total billed: ₹18.5L | Success rate: 96%

     Would you like a breakdown by doctor?"
```

**Requirements:**
- Concise but complete answers
- Include relevant context (comparisons, trends)
- Suggest follow-up queries
- Support tabular output for lists
- Export option ("Send this as PDF")

---

### Module B: Conversational Actions (P1)

#### B.1 Appointment Management via Chat
**Description:** Book, reschedule, cancel appointments through natural language

**Example Interactions:**
```
User: "Book Mr. Patel for tomorrow with Dr. Sharma"
AI: "I found 3 available slots with Dr. Sharma tomorrow:
     1. 10:00 AM
     2. 2:30 PM
     3. 4:00 PM
     Which would you prefer?"

User: "2:30"
AI: "Booked Mr. Patel with Dr. Sharma tomorrow at 2:30 PM.
     Should I send a WhatsApp confirmation?"
```

**Supported Actions:**
- Book new appointment
- Reschedule existing appointment
- Cancel appointment
- Check availability
- Add to waitlist

**Safety Requirements:**
- Confirmation before any write action
- Undo capability for 30 seconds
- Audit log of all AI actions

#### B.2 Patient Lookup
**Description:** Find patients and their information conversationally

**Example:**
```
User: "Find the diabetic patient from Andheri who came last month"
AI: "Found 2 patients matching:
     1. Ramesh Gupta (M, 58) - Last visit: Dec 15
        Andheri West | Diabetes Type 2
     2. Sunita Desai (F, 45) - Last visit: Dec 22
        Andheri East | Diabetes Type 1

     Which patient do you need?"
```

**Uses existing:** Phase 2 RAG Search infrastructure

#### B.3 Quick Actions
**Description:** Common tasks via shorthand commands

**Examples:**
```
"Mark token 5 as done" → Updates appointment status
"Send reminder to Mr. Patel" → Triggers WhatsApp/SMS
"Add note: patient requested morning slot" → Adds to patient record
"Generate bill for today's consultation" → Creates invoice
```

---

### Module C: Proactive Intelligence (P2)

#### C.1 Smart Notifications
**Description:** AI-generated alerts and suggestions

**Examples:**
```
"3 patients are due for follow-up this week after their stent procedures"

"Dr. Sharma has 2 back-to-back complex procedures tomorrow.
 Consider adding buffer time?"

"Revenue is 15% below last month. Top reason: 23% fewer new patients"
```

#### C.2 Schedule Optimization
**Description:** AI suggestions for better scheduling

**Examples:**
```
"You have a 45-min gap at 3 PM. Should I offer it to waitlist patients?"

"Based on history, Mr. Gupta's appointments run 10 min over.
 Suggest booking 25-min slot instead of 15?"
```

#### C.3 Automated Follow-ups
**Description:** Procedure-aware follow-up scheduling

**Logic:**
```python
# After stent procedure → Suggest 1-week follow-up
# After cataract surgery → Suggest next-day and 1-week follow-up
# After echo → Suggest 6-month repeat if abnormal findings
```

---

### Module D: Report Generation (P2)

#### D.1 On-Demand Reports
**Description:** Generate reports via natural language

**Examples:**
```
"Send me the monthly revenue report"
"Generate GST summary for December"
"Email patient list to accounts team"
```

**Integration:** Uses Phase 8 Reports & Exports infrastructure

#### D.2 Scheduled Reports
**Description:** Set up recurring report delivery

**Example:**
```
User: "Send me a daily summary every evening at 6 PM"
AI: "I'll send you a daily practice summary at 6 PM including:
     - Appointments completed vs scheduled
     - Revenue collected
     - Tomorrow's schedule preview

     Confirm?"
```

---

## 4. Technical Architecture

### 4.1 High-Level Design

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

### 4.2 LLM Strategy

**Option A: Extend Existing Ollama Setup** (Recommended)
- Already have Ollama + Qwen2.5 for RAG
- Add function calling / tool use capability
- Keep everything local, offline-capable

**Option B: Hybrid (Local + Cloud)**
- Local for simple queries
- Cloud (OpenAI/Claude API) for complex reasoning
- Fallback when local fails

**Recommendation:** Start with Option A, add Option B as premium feature

### 4.3 Function Calling Design

The AI translates natural language into function calls:

```python
# User: "How many echos this month?"

# LLM generates:
{
  "function": "get_procedure_stats",
  "arguments": {
    "clinic_id": "{{current_clinic}}",
    "procedure_type": "Echo",
    "start_date": "2026-01-01",
    "end_date": "2026-01-04"
  }
}

# Backend executes and returns result
# LLM formats response for user
```

**Available Functions:**
| Function | Description | Module |
|----------|-------------|--------|
| `get_procedure_stats` | Procedure analytics | Phase 9 |
| `get_revenue_analytics` | Revenue queries | Phase 3 |
| `get_appointments` | Appointment queries | Core |
| `book_appointment` | Create appointment | Core |
| `search_patients` | Patient lookup | Phase 2 |
| `generate_report` | Report generation | Phase 8 |
| `send_notification` | Send SMS/WhatsApp | Phase 5 |

### 4.4 Context Management

```python
class ConversationContext:
    session_id: str
    user_id: str
    clinic_id: str
    messages: list[Message]  # Last 10 messages
    entities: dict  # Extracted entities (patient, doctor, date)
    last_query_result: Any  # For follow-up queries
```

**Context Rules:**
- Maintain context for 10 turns or 30 minutes
- Entity references persist ("he", "that patient", "same doctor")
- Results available for follow-up ("break that down by doctor")

### 4.5 API Design

```python
# POST /api/v1/ai/chat
{
  "message": "How many procedures this month?",
  "session_id": "optional-for-context",
  "context": {
    "current_screen": "dashboard",  # Optional UI context
    "selected_patient_id": null
  }
}

# Response
{
  "response": "This month you've completed 127 procedures...",
  "actions": [],  # Any actions taken
  "suggestions": ["Breakdown by doctor?", "Compare to last month?"],
  "data": {  # Structured data for UI rendering
    "type": "procedure_stats",
    "total": 127,
    "by_category": {...}
  },
  "session_id": "abc123"
}
```

---

## 5. Mobile UI Design

### 5.1 Chat Interface

```
┌─────────────────────────────────┐
│  Practice Assistant        [X] │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐   │
│  │ How many procedures     │   │
│  │ this month?             │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │ This month: 127 procs   │   │
│  │ • Cardiology: 68        │   │
│  │ • Orthopedics: 35       │   │
│  │ • General: 24           │   │
│  │                         │   │
│  │ [📊 View Chart]         │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌───────────────────────────┐ │
│  │ Suggested:               │ │
│  │ [By doctor] [vs last mo] │ │
│  └───────────────────────────┘ │
│                                 │
├─────────────────────────────────┤
│ [🎤] Type a message...    [➤] │
└─────────────────────────────────┘
```

### 5.2 Integration Points

- **Floating Action Button** on main screens → Opens chat
- **Context-aware** → "Tell me about this patient" when viewing patient
- **Quick actions** in chat → Buttons for common queries
- **Voice input** → Microphone button uses existing Whisper

---

## 6. Safety & Guardrails

### 6.1 Action Confirmation
All write actions require explicit confirmation:
```
AI: "I'll book Mr. Patel with Dr. Sharma tomorrow at 2:30 PM.

     [Confirm] [Cancel]"
```

### 6.2 Scope Limits
- Cannot access clinical notes (EMR boundary)
- Cannot delete patient records
- Cannot modify completed invoices
- Cannot access other clinics' data

### 6.3 Audit Trail
```python
class AIAuditLog:
    timestamp: datetime
    user_id: str
    query: str
    response: str
    actions_taken: list[str]
    function_calls: list[dict]
```

### 6.4 Fallback Behavior
```
"I'm not sure how to help with that. Here's what I can do:
 • Answer questions about procedures, revenue, appointments
 • Book or reschedule appointments
 • Find patient information
 • Generate reports

 Or you can reach this through: [Dashboard] [Reports] [Patients]"
```

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Query Success Rate | > 90% | Queries answered without fallback |
| Response Time | < 2s | P95 latency |
| User Adoption | > 50% | % of receptionists using daily |
| Task Completion | > 80% | Actions completed vs started |
| Error Rate | < 5% | Failed function calls |

---

## 8. Implementation Phases

### Phase 16a: Natural Language Analytics (MVP)
- Chat UI in mobile app
- Query parsing for procedures, revenue, appointments
- Response generation
- Basic context (single session)
- **Timeline:** 2-3 weeks

### Phase 16b: Conversational Actions
- Appointment booking via chat
- Patient lookup
- Confirmation flows
- Undo capability
- **Timeline:** 2 weeks

### Phase 16c: Proactive Intelligence
- Smart notifications
- Follow-up suggestions
- Schedule optimization hints
- **Timeline:** 2 weeks

### Phase 16d: Voice Integration
- Connect to existing voice agent
- Unified voice + chat experience
- **Timeline:** 1 week

---

## 9. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Ollama + Qwen2.5 | ✅ Exists | Phase 2 RAG |
| Procedure Analytics | ✅ Exists | Phase 9 |
| Revenue Analytics | ✅ Exists | Phase 3 |
| Reports Service | ✅ Exists | Phase 8 |
| Voice Agent | ✅ Exists | Phase 1 |
| Function Calling in Qwen | ⚠️ Needs setup | May need model upgrade |

---

## 10. Open Questions

1. **Hinglish Support:** How well does Qwen handle mixed Hindi-English? Need testing.

2. **Offline Mode:** Should AI work offline with cached responses, or gracefully degrade?

3. **Multi-turn Complexity:** How many turns of context before performance degrades?

4. **Model Size:** Qwen 7B vs 14B vs 32B tradeoffs for function calling accuracy?

5. **Voice vs Chat Priority:** Should voice and chat share the same backend, or separate?

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucination | High | Strict function calling, no freeform data access |
| Slow response | Medium | Caching, query optimization, smaller model |
| User trust | High | Always show source data, confirm actions |
| Scope creep into clinical | High | Hard boundaries, no EMR write access |

---

## 12. Competitive Advantage

| Competitor | Their AI | Our Advantage |
|------------|----------|---------------|
| Practo | Basic chatbot for patients | AI for practice operations |
| HealthPlix | None | First-mover in practice AI |
| PM Cardio | None | Procedure-aware intelligence |

**This makes DocAssist the first practice management system with conversational AI for Indian doctors.**

---

*Specification Version: 1.0*
*Last Updated: 2026-01-04*
