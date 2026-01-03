# DocAssist Practice Manager - Specifications

## Product Overview

DocAssist Practice Manager is a premium appointment scheduling and practice management system designed exclusively for Indian doctors. It seamlessly integrates with DocAssist EMR to provide a complete digital practice solution.

---

## Feature Specifications

### Module 1: Appointment Management

#### F1.1 Appointment Booking
**Description:** Multi-channel appointment booking system
**Priority:** P0 (Critical)

**User Stories:**
- As a receptionist, I want to book appointments quickly so patients don't wait
- As a patient, I want to book online so I don't need to call
- As a doctor, I want to see my schedule at a glance

**Functional Requirements:**
- Book appointments in < 3 clicks
- Support walk-in, phone, online, and voice booking
- Automatic slot availability calculation
- Overbooking prevention with warnings
- Recurring appointment support
- Multi-doctor scheduling

**Acceptance Criteria:**
- [ ] Booking completes in < 500ms
- [ ] Conflict detection works for overlapping slots
- [ ] Calendar syncs in real-time across views
- [ ] Supports 1000+ appointments per month

#### F1.2 Smart Scheduling
**Description:** AI-powered schedule optimization
**Priority:** P1 (High)

**User Stories:**
- As a doctor, I want AI to suggest optimal slots based on appointment type
- As a receptionist, I want automatic gap filling suggestions

**Functional Requirements:**
- Appointment type duration learning
- Travel time consideration for home visits
- Break time protection
- Emergency slot reservation
- Waitlist management with auto-notification

#### F1.3 Voice Appointment Agent
**Description:** Conversational voice interface for scheduling
**Priority:** P1 (High)

**User Stories:**
- As a doctor, I want to schedule appointments hands-free during examinations
- As a receptionist, I want voice commands for faster booking

**Functional Requirements:**
- Wake word activation ("Hey DocAssist")
- Natural language understanding for scheduling intents
- Confirmation before booking
- Speaker verification for security
- Works completely offline

**Technical Specifications:**
- Whisper for speech-to-text (local)
- Ollama + Qwen for NLU
- Piper TTS for text-to-speech (local)
- < 2 second end-to-end latency

#### F1.4 Patient Notifications
**Description:** Multi-channel appointment reminders
**Priority:** P0 (Critical)

**User Stories:**
- As a patient, I want reminders so I don't miss appointments
- As a clinic, I want to reduce no-shows

**Functional Requirements:**
- SMS reminders (via local SMS gateway)
- WhatsApp notifications (via WhatsApp Business API)
- Configurable timing (24h, 2h before)
- Confirmation/cancellation via reply
- Language preference per patient

---

### Module 2: Patient Management (Practice Context)

#### F2.1 Patient Registry
**Description:** Unified patient database with EMR sync
**Priority:** P0 (Critical)

**User Stories:**
- As a receptionist, I want to find patients instantly
- As a doctor, I want patient history available when they arrive

**Functional Requirements:**
- Instant search by name, phone, ID
- EMR data sync (read patient records)
- New patient registration
- Aadhaar-based verification (optional)
- Family linking
- Photo capture

**Integration with EMR:**
- Shared SQLite database for patient demographics
- One-way sync of clinical data (EMR → Practice Manager)
- Two-way sync of appointments

#### F2.2 Patient Timeline
**Description:** Visual history of all patient interactions
**Priority:** P2 (Medium)

**User Stories:**
- As a doctor, I want to see when a patient last visited
- As a receptionist, I want to see payment history

**Functional Requirements:**
- Visit history with dates
- Payment/billing history
- Prescription history (from EMR)
- Upcoming appointments
- Notes and tags

---

### Module 3: Billing & Payments

#### F3.1 Invoice Generation
**Description:** Professional invoice creation
**Priority:** P0 (Critical)

**User Stories:**
- As a receptionist, I want to generate bills quickly
- As a patient, I want clear itemized bills

**Functional Requirements:**
- Customizable invoice templates
- Service catalog management
- Tax calculation (GST)
- Discount application
- Print and PDF export
- QR code for UPI payment

#### F3.2 Payment Collection
**Description:** Multi-mode payment acceptance
**Priority:** P0 (Critical)

**User Stories:**
- As a patient, I want to pay via UPI
- As a clinic, I want accurate payment tracking

**Functional Requirements:**
- Cash payment recording
- UPI payment (QR code generation)
- Card payment (via external terminal, manual entry)
- Partial payment support
- Payment plan/EMI tracking
- Daily collection reconciliation

#### F3.3 Insurance & TPA
**Description:** Insurance claim management
**Priority:** P2 (Medium)

**User Stories:**
- As a receptionist, I want to track insurance claims
- As a patient, I want help with claim documentation

**Functional Requirements:**
- Insurance company database
- Pre-authorization tracking
- Claim submission tracking
- Document attachment
- Claim status updates

---

### Module 4: Practice Analytics

#### F4.1 Dashboard
**Description:** Real-time practice overview
**Priority:** P0 (Critical)

**User Stories:**
- As a doctor, I want to see today's stats at a glance
- As a practice owner, I want to track revenue trends

**Functional Requirements:**
- Today's appointments (completed, pending, no-shows)
- Revenue metrics (today, week, month)
- Patient volume trends
- Top services by revenue
- Upcoming slots availability

**Visual Design:**
- Clean, minimal, premium feel
- Dark mode support
- Customizable widget layout
- Touch-optimized for tablets

#### F4.2 Revenue Analytics
**Description:** Deep financial insights
**Priority:** P1 (High)

**User Stories:**
- As a practice owner, I want to understand revenue patterns
- As a doctor, I want to track my earnings

**Functional Requirements:**
- Revenue by period (day/week/month/year)
- Revenue by service type
- Revenue by payment mode
- Revenue by doctor (multi-doctor clinics)
- Outstanding payments tracking
- Revenue forecasting (AI-powered)

#### F4.3 Patient Analytics
**Description:** Patient behavior insights
**Priority:** P1 (High)

**User Stories:**
- As a doctor, I want to understand patient demographics
- As a practice owner, I want to reduce no-shows

**Functional Requirements:**
- New vs returning patient ratio
- Patient demographics (age, gender, location)
- No-show rate and patterns
- Peak hours analysis
- Patient retention metrics
- Referral tracking

#### F4.4 Operational Analytics
**Description:** Efficiency metrics
**Priority:** P2 (Medium)

**User Stories:**
- As a practice owner, I want to optimize operations
- As a doctor, I want to reduce patient wait times

**Functional Requirements:**
- Average wait time tracking
- Consultation duration analysis
- Staff productivity metrics
- Resource utilization
- Appointment slot optimization suggestions

---

### Module 5: Communication Hub

#### F5.1 SMS Gateway Integration
**Description:** Bulk and transactional SMS
**Priority:** P1 (High)

**User Stories:**
- As a clinic, I want to send reminders
- As a practice, I want to announce holidays

**Functional Requirements:**
- Local SMS gateway integration
- Template management
- Bulk send capability
- Delivery tracking
- DND compliance

#### F5.2 WhatsApp Integration
**Description:** WhatsApp Business messaging
**Priority:** P1 (High)

**User Stories:**
- As a patient, I want WhatsApp reminders
- As a clinic, I want to share reports via WhatsApp

**Functional Requirements:**
- WhatsApp Business API integration
- Template messages
- Media sharing (prescriptions, reports)
- Quick replies
- Chat history

---

### Module 6: Staff Management

#### F6.1 User Roles & Permissions
**Description:** Role-based access control
**Priority:** P0 (Critical)

**User Stories:**
- As a doctor, I want to control who sees what
- As a receptionist, I want access to scheduling

**Functional Requirements:**
- Predefined roles (Doctor, Receptionist, Billing Staff, Admin)
- Custom role creation
- Granular permissions
- Audit logging
- Session management

#### F6.2 Staff Scheduling
**Description:** Staff duty roster management
**Priority:** P2 (Medium)

**User Stories:**
- As a clinic manager, I want to manage staff shifts
- As staff, I want to see my schedule

**Functional Requirements:**
- Shift definition
- Staff assignment
- Leave management
- Duty swaps
- Availability calendar

---

### Module 7: EMR Integration

#### F7.1 Bidirectional Sync
**Description:** Real-time sync with DocAssist EMR
**Priority:** P0 (Critical)

**User Stories:**
- As a doctor, I want patient data available everywhere
- As a receptionist, I want to see if a patient has records

**Functional Requirements:**
- Shared SQLite database schema
- Real-time sync via file system watching
- Conflict resolution (last-write-wins with merge)
- Sync status indicator
- Manual sync trigger

**Technical Specifications:**
- SQLite WAL mode for concurrent access
- watchdog library for file system events
- SQLite triggers for change detection
- Merge strategy for concurrent edits

#### F7.2 Context Handoff
**Description:** Seamless transition between apps
**Priority:** P1 (High)

**User Stories:**
- As a doctor, I want to open a patient in EMR from Practice Manager
- As a doctor, I want to schedule follow-up from EMR

**Functional Requirements:**
- Deep linking between applications
- Shared patient context
- Appointment creation from EMR
- Clinical notes visibility in Practice Manager

---

## Non-Functional Requirements

### NFR1: Performance
- App launch: < 2 seconds on minimum spec hardware
- Screen transitions: < 100ms
- Search results: < 200ms for 10,000+ patients
- Voice recognition: < 1 second latency

### NFR2: Reliability
- Zero data loss under any circumstance
- Automatic backup every hour
- Transaction rollback on failure
- Graceful degradation without LLM

### NFR3: Security
- Local-only data storage
- Encrypted database (SQLCipher optional)
- Role-based access control
- Session timeout
- Audit logging

### NFR4: Usability
- Learnable in < 1 hour
- Touch-friendly for tablets
- Keyboard shortcuts for power users
- High contrast mode
- Large font option

### NFR5: Scalability
- Support 50,000+ patients
- Support 1,000+ appointments/month
- Support 10+ concurrent users
- Support 5+ years of data

### NFR6: Compatibility
- Windows 10/11
- Ubuntu 20.04+
- Minimum: 4GB RAM, 2 core CPU, 10GB storage
- Recommended: 8GB RAM, 4 core CPU, 50GB SSD

---

## Data Model Overview

### Core Entities
- **Patient** (synced with EMR)
- **Appointment**
- **Doctor**
- **Staff**
- **Service**
- **Invoice**
- **Payment**
- **Notification**
- **AuditLog**

### EMR Shared Entities
- Patient demographics
- Clinical records (read-only)
- Prescriptions (read-only)

---

## API Specifications

### Internal APIs (for EMR integration)
- `GET /patients/{id}` - Get patient details
- `POST /appointments` - Create appointment
- `GET /appointments?date={date}` - Get appointments
- `POST /invoices` - Create invoice

### External APIs (for future mobile app)
- RESTful API with JWT authentication
- Rate limiting
- Versioning (v1, v2, etc.)

---

## Voice Agent Specifications

### Supported Commands
- "Book appointment for [patient name] on [date] at [time]"
- "What's my schedule for today?"
- "Cancel appointment for [patient name]"
- "Reschedule [patient name] to [new time]"
- "How many patients today?"
- "What's the next available slot?"

### Voice Agent Architecture
```
[Microphone] → [Whisper STT] → [Intent Parser] → [Action Handler] → [Piper TTS] → [Speaker]
                                      ↓
                              [Ollama + Qwen]
```

### Conversation Flow
1. Wake word detection ("Hey DocAssist")
2. Listening indicator (visual + audio)
3. Speech-to-text conversion
4. Intent classification
5. Slot filling (ask clarifying questions)
6. Action confirmation
7. Execution
8. Response generation

---

## UI/UX Specifications

### Design Language
- Minimal, clean, professional
- Inspired by Apple's design principles
- Consistent with DocAssist EMR
- Premium color palette (deep blues, clean whites)

### Key Screens
1. **Dashboard** - Daily overview with key metrics
2. **Calendar** - Visual appointment calendar
3. **Patient List** - Searchable patient directory
4. **Patient Profile** - Individual patient view
5. **Billing** - Invoice creation and payment
6. **Analytics** - Charts and reports
7. **Settings** - Configuration and preferences

### Navigation
- Side navigation for main modules
- Tab bar for sub-sections
- Breadcrumbs for deep navigation
- Quick actions floating button

---

*This specification document defines the complete scope of DocAssist Practice Manager v1.0*

**Last Updated:** 2026-01-03
**Version:** 1.0
