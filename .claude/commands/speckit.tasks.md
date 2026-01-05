# DocAssist Practice Manager - Task Breakdown

**Last Updated:** 2026-01-05
**Status:** Phases 1-14, 16C, 17 Backend Complete

---

## 📌 IMPORTANT: Use Master Roadmap

**For current project status, read:**
- `/.claude/MASTER_ROADMAP.md` - SINGLE SOURCE OF TRUTH
- `/.claude/specs/PHASE_INDEX.md` - Index of all phase specs

This file provides task breakdowns for active development phases only.

---

## Development Workflow Reminder

**MANDATORY:** All development follows Spec-Kit + Ralph Wiggum methodology:

1. Before implementing any feature, reference:
   - `speckit.constitution.md` - For principles and constraints
   - `speckit.specify.md` - For feature requirements
   - `speckit.plan.md` - For technical approach

2. Use Ralph Wiggum loops for all significant implementations:
   - Define clear completion criteria
   - Run verification after each iteration
   - Commit working code
   - Continue until tests pass

3. After completing tasks, update:
   - This file with status
   - `/.claude/MASTER_ROADMAP.md` with phase progress
   - Create implementation summary in `/PHASE_XX_SUMMARY.md`

---

## 🎯 ACTIVE DEVELOPMENT PHASES

### Phase 15: Multi-Location & Staff Management
**Status:** Backend ✅ Complete, Mobile UI ⏳ Pending
**Priority:** HIGH
**Completion:** 75%

#### Task 15.1: Mobile UI - Organization Switcher
**Status:** Not Started
**Ralph Loop:** Yes - "Implement org switcher in Flutter app"
**Max Iterations:** 25

- [ ] Create org/branch switcher component
- [ ] Add to app bar or drawer
- [ ] Store selected org in local state (Riverpod)
- [ ] Filter all API calls by selected org
- [ ] Test org switching flow
- [ ] Handle permissions (users with single org)

**Verification:**
- User can switch between orgs
- Data filtered correctly per org
- No cross-contamination

**Completion Criteria:**
- Switcher UI functional
- Data isolation working
- No performance issues

#### Task 15.2: Mobile UI - Staff Management
**Status:** Not Started
**Ralph Loop:** Yes - "Create staff management screens"
**Max Iterations:** 30

- [ ] Create staff list screen
- [ ] Implement staff detail/profile
- [ ] Add staff form (create/edit)
- [ ] Role assignment UI
- [ ] Permission display
- [ ] Staff search and filters
- [ ] Integration with backend `/api/v1/staff`

**Verification:**
- All CRUD operations work
- Roles displayed correctly
- Permissions enforced

#### Task 15.3: Cross-Location Patient Search
**Status:** Not Started
**Ralph Loop:** Yes - "Enhance patient search for multi-location"
**Max Iterations:** 20

- [ ] Update patient search to support org filter
- [ ] Add "All Locations" option
- [ ] Display patient's primary location
- [ ] Show cross-location visit history
- [ ] Handle duplicate patient detection

**Verification:**
- Search works across locations
- Results show location info
- No duplicates shown

#### Task 15.4: Consolidated Analytics Dashboard
**Status:** Not Started
**Ralph Loop:** Yes - "Build multi-location analytics"
**Max Iterations:** 30

- [ ] Create org-level analytics screen
- [ ] Revenue by branch chart
- [ ] Patients by branch chart
- [ ] Appointments by branch chart
- [ ] Comparative metrics
- [ ] Branch performance leaderboard

**Verification:**
- Charts render correctly
- Data aggregates properly
- Performance acceptable

**Completion Criteria:**
- All screens functional
- Data accurate
- UX smooth

---

### Phase 16A: Natural Language Analytics (AI Chat)
**Status:** Not Started
**Priority:** MEDIUM
**Completion:** 0%

#### Task 16A.1: Chat UI Component
**Status:** Not Started
**Ralph Loop:** Yes - "Implement chat interface in Flutter"
**Max Iterations:** 25

- [ ] Create chat screen with message list
- [ ] Message input field
- [ ] Voice input button (reuse Phase 1 Whisper)
- [ ] Suggested query chips
- [ ] Loading states (typing indicator)
- [ ] Error handling UI
- [ ] Chat history persistence (local storage)

**Verification:**
```bash
# Test chat UI
flutter test test/features/ai_chat/chat_screen_test.dart
```

**Completion Criteria:**
- Chat UI matches mockup
- Voice input works
- Messages persist locally

#### Task 16A.2: Backend - Query Understanding
**Status:** Not Started
**Ralph Loop:** Yes - "Implement NL query parser with Ollama"
**Max Iterations:** 40

- [ ] Create `/api/v1/ai/query` endpoint
- [ ] Implement prompt templates for query parsing
- [ ] Parse common query patterns:
  - Procedure counts ("How many echos this month?")
  - Revenue queries ("Today's collection")
  - Appointment queries ("Busiest day this week")
  - Patient queries ("New patients this month")
- [ ] Extract entities (dates, procedures, doctors, etc.)
- [ ] Handle Hinglish queries
- [ ] Context management (remember last 5 queries)
- [ ] Write comprehensive tests

**Verification:**
```bash
pytest tests/api/test_ai_query.py -v
# Target: 90%+ accuracy on test queries
```

**Completion Criteria:**
- 90%+ query understanding accuracy
- Handles ambiguity with clarification
- Context maintained for 5+ turns
- Response time < 2 seconds

#### Task 16A.3: Backend - Response Generation
**Status:** Not Started
**Ralph Loop:** Yes - "Implement AI response formatter"
**Max Iterations:** 30

- [ ] Create response templates
- [ ] Format analytics results as natural language
- [ ] Add context (trends, comparisons)
- [ ] Suggest follow-up queries
- [ ] Support tabular output
- [ ] Add export options
- [ ] Integrate with existing analytics services

**Verification:**
```bash
pytest tests/services/test_ai_response.py -v
```

**Completion Criteria:**
- Responses are clear and actionable
- Include relevant context
- Suggest next steps
- Export works

#### Task 16A.4: Integration & Testing
**Status:** Not Started
**Ralph Loop:** Yes - "Integrate chat UI with backend"
**Max Iterations:** 20

- [ ] Connect Flutter chat to `/api/v1/ai/query`
- [ ] Implement API client methods
- [ ] Handle streaming responses (if needed)
- [ ] Error handling and retries
- [ ] End-to-end testing
- [ ] Performance optimization

**Verification:**
- Manual testing with 20+ query variations
- Response time < 2 seconds
- No crashes or errors

---

### Phase 16B: Conversational Actions
**Status:** Not Started
**Priority:** MEDIUM
**Completion:** 0%

#### Task 16B.1: Action Execution Framework
**Status:** Not Started
**Ralph Loop:** Yes - "Build AI action execution system"
**Max Iterations:** 35

- [ ] Define action schemas (book, cancel, reschedule, etc.)
- [ ] Create `/api/v1/ai/actions` endpoint
- [ ] Implement confirmation flow
- [ ] Add undo capability (30 second window)
- [ ] Audit logging for all AI actions
- [ ] Safety checks (no deletion, no clinical actions)

**Verification:**
```bash
pytest tests/api/test_ai_actions.py -v
```

**Completion Criteria:**
- All actions work correctly
- Confirmation required before execution
- Undo works
- Audit trail complete

#### Task 16B.2: Book Appointment via Chat
**Status:** Not Started
**Ralph Loop:** Yes - "Implement chat-based booking"
**Max Iterations:** 30

- [ ] Parse booking intent from chat
- [ ] Extract patient, doctor, date, time
- [ ] Check slot availability
- [ ] Present options to user
- [ ] Confirmation dialog
- [ ] Book appointment via existing API
- [ ] Send confirmation message

**Verification:**
- User can book via chat
- No double bookings
- Confirmation sent

#### Task 16B.3: Patient Lookup via NL
**Status:** Not Started
**Ralph Loop:** Yes - "Enhance patient search with NL"
**Max Iterations:** 25

- [ ] Parse fuzzy patient descriptions
- [ ] Use existing RAG search (Phase 2)
- [ ] Handle multiple matches
- [ ] Present results in chat
- [ ] Allow selection via chat
- [ ] Display patient profile

**Verification:**
- Fuzzy search works
- Results relevant
- Selection clear

---

### Phase 17: Telemedicine - Frontend
**Status:** Backend ✅ Complete, Frontend ⏳ Pending
**Priority:** LOW (Nice to have)
**Completion:** 50% (Backend only)

#### Task 17.1: Flutter WebRTC Integration
**Status:** Not Started
**Ralph Loop:** Yes - "Integrate WebRTC in Flutter"
**Max Iterations:** 40

- [ ] Add `flutter_webrtc` package
- [ ] Create video call screen
- [ ] Implement WebRTC peer connection
- [ ] Connect to backend WebSocket signaling
- [ ] Handle ICE candidates
- [ ] Video/audio controls (mute, camera switch)
- [ ] Call quality indicators
- [ ] Recording controls

**Verification:**
```bash
flutter test test/features/telemedicine/
```

**Completion Criteria:**
- Video calls work peer-to-peer
- Audio clear
- Camera switching works
- No crashes

#### Task 17.2: Consultation UI
**Status:** Not Started
**Ralph Loop:** Yes - "Build consultation interface"
**Max Iterations:** 30

- [ ] Consultation list screen
- [ ] Start consultation flow
- [ ] Waiting room UI
- [ ] In-call UI with chat
- [ ] Prescription sharing UI
- [ ] End call summary
- [ ] Recording playback (if enabled)

**Verification:**
- All UI states handled
- UX smooth
- No performance issues

---

## ⏸️ ON HOLD / NOT STARTED

### Phase 18: Patient Mobile App
**Status:** Not Started
**Priority:** LOW
**Reason:** Booking portal (web) covers patient needs for now

**Tasks:**
- Separate Flutter app for patients
- Appointment booking
- Health records view
- Telemedicine support
- Prescription downloads
- Lab result viewing

**Blocked By:** Nothing, just prioritized lower

### Phase 19: Advanced Analytics & BI
**Status:** Not Started
**Priority:** LOW

**Tasks:**
- Interactive dashboards
- Custom report builder
- Predictive analytics
- Forecasting models
- Cohort analysis

### Phase 20: Integration Marketplace
**Status:** Not Started
**Priority:** LOW

**Tasks:**
- Lab integration framework
- Pharmacy integration
- Imaging center integration
- Diagnostic center integration

---

## ✅ COMPLETED PHASES (Archived)

For completed phases, see implementation summaries:
- Phase 1-9: Pre-2026 implementations (no detailed docs)
- Phase 10: `/PHASE_10_IMPLEMENTATION.md`
- Phase 11: `/PHASE_11_IMPLEMENTATION_SUMMARY.md`
- Phase 12: `/PHASE_12_IMPLEMENTATION_SUMMARY.md`
- Phase 13: `/PHASE_13_SUMMARY.md`
- Phase 14: `/PHASE_14_SUMMARY.md`
- Phase 16C: `/PHASE_16C_IMPLEMENTATION_SUMMARY.md`

**Completed Tasks:** 95% of Phases 1-14, 16C, 17 Backend

---

## 📋 Ralph Wiggum Command Templates

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

## 📊 Overall Progress

| Phase | Status | Backend | Mobile | Tests | Docs |
|-------|--------|---------|--------|-------|------|
| 1-9 | ✅ Complete | ✅ | ✅ | ✅ | ⚠️ |
| 10 | ✅ Complete | ✅ | ✅ | ✅ | ✅ |
| 11 | ✅ Complete | ✅ | ⚠️ | ✅ | ✅ |
| 12 | ✅ Complete | ✅ | N/A (Web) | ✅ | ✅ |
| 13 | ✅ Complete | ✅ | ❌ | ✅ | ✅ |
| 14 | ✅ Complete | ✅ | ❌ | ✅ | ✅ |
| 15 | ⏳ Partial | ✅ | ❌ | ✅ | ⚠️ |
| 16A | ❌ Not Started | ❌ | ❌ | ❌ | ✅ (Spec) |
| 16B | ❌ Not Started | ❌ | ❌ | ❌ | ✅ (Spec) |
| 16C | ✅ Complete | ✅ | ❌ | ✅ | ✅ |
| 17 | ⏳ Partial | ✅ | ❌ | ✅ | ⚠️ |
| 18+ | ❌ Not Started | ❌ | ❌ | ❌ | ❌ |

**Legend:**
- ✅ Complete
- ⏳ In Progress
- ⚠️ Partial
- ❌ Not Started
- N/A Not Applicable

---

## 🎯 Priority Queue

**High Priority:**
1. Phase 15: Mobile UI for multi-location
2. Phase 13: Mobile UI for EMR timeline
3. Phase 14: Mobile UI for insurance
4. SMS Gateway Configuration (MSG91)
5. Background job scheduler integration

**Medium Priority:**
1. Phase 16A: Natural Language Analytics
2. Phase 16B: Conversational Actions
3. Phase 16C: Mobile UI for proactive insights
4. Load testing and optimization

**Low Priority:**
1. Phase 17: Telemedicine mobile UI
2. Phase 18: Patient mobile app
3. Advanced features (Phases 19-21)

---

## 📝 Next Steps for Current Session

1. **Read** `/.claude/MASTER_ROADMAP.md` for current status
2. **Choose** a high-priority task from above
3. **Run** `/speckit.specify` if starting new feature
4. **Execute** using Ralph loop if complex
5. **Test** thoroughly before marking complete
6. **Update** this file and master roadmap when done
7. **Commit** with descriptive message

---

**Last Updated:** 2026-01-05
**Version:** 2.0 (Aligned with Master Roadmap)

*For detailed project status, always refer to /.claude/MASTER_ROADMAP.md*
