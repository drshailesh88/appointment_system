# Phase 16c: Proactive Intelligence - Implementation Guide

## Overview

Phase 16c adds proactive intelligence to the Practice AI Assistant, making it suggest actions rather than just respond to queries.

**Key Features:**
- Follow-up intelligence based on procedure type
- Schedule gap detection for waitlist filling
- Revenue anomaly alerts
- No-show risk identification
- Morning digest with key metrics
- One-click actions from insights

---

## Architecture

### Components

1. **Follow-up Intelligence** (`followup_intelligence.py`)
   - Procedure-specific follow-up rules
   - Automatic follow-up schedule generation
   - Condition-based follow-ups (e.g., EF < 40% after echo)

2. **Schedule Optimizer** (`schedule_optimizer.py`)
   - Gap detection in doctor schedules
   - Buffer time suggestions based on patient history
   - Overbooking risk assessment

3. **Proactive Insights Engine** (`proactive_insights.py`)
   - Generates daily insights
   - Revenue anomaly detection
   - No-show risk identification
   - Insight dismissal and action tracking

4. **Daily Digest Service** (`daily_digest.py`)
   - Personalized morning digest
   - Multi-channel delivery (push, email, SMS)
   - User preference management

---

## Database Schema

### Tables

#### `proactive_insights`
Stores AI-generated insights and suggestions.

**Key Fields:**
- `insight_type`: followup_due, schedule_gap, revenue_alert, etc.
- `priority`: 1-5 (5 = urgent)
- `title`: Short summary
- `message`: Detailed message
- `suggested_action`: JSON with one-click action
- `expires_at`: When insight becomes irrelevant
- `dismissed_at`, `acted_at`: User interaction tracking

#### `followup_schedules`
Automatic follow-up schedules based on procedures.

**Key Fields:**
- `procedure_id`: Link to procedure
- `due_date`: When follow-up is due
- `reason`: Why follow-up is needed
- `completed`: Whether follow-up was scheduled
- `scheduled_appointment_id`: Link to booked appointment

#### `user_digest_preferences`
User preferences for daily digest delivery.

**Key Fields:**
- `enabled`: Whether digest is enabled
- `delivery_hour`, `delivery_minute`: When to deliver
- `channels`: Array of ["push", "email", "sms"]
- Content filters: `include_revenue`, `include_followups`, etc.

---

## Follow-up Rules

### Cardiology

**Stent Placement:**
- 7 days: Post-stent check (Priority: 5)
- 30 days: Monthly follow-up (Priority: 4)
- 180 days: 6-month angiogram review (Priority: 3)

**Angioplasty (PTCA):**
- 7 days: Post-PTCA review (Priority: 5)
- 90 days: 3-month stress test (Priority: 3)

**Echocardiogram (Conditional):**
- 180 days: Repeat echo IF EF < 40% or abnormal findings (Priority: 3)

**Pacemaker Implantation:**
- 1 day: Day-1 device check (Priority: 5)
- 7 days: 1-week wound check (Priority: 4)
- 90 days: 3-month device interrogation (Priority: 3)
- 180 days: 6-month device check (Priority: 3)

### Ophthalmology

**Cataract Surgery:**
- 1 day: Day-1 post-op check (Priority: 5)
- 7 days: 1-week post-op review (Priority: 4)
- 30 days: 1-month final assessment (Priority: 3)

**Intravitreal Injection:**
- 28 days: Monthly injection (Priority: 4)

**LASIK:**
- 1 day: Day-1 post-op (Priority: 5)
- 7 days: 1-week check (Priority: 4)
- 90 days: 3-month final check (Priority: 2)

### Orthopedics

**Total Knee Replacement:**
- 14 days: Suture removal (Priority: 5)
- 42 days: 6-week X-ray (Priority: 4)
- 90 days: 3-month review (Priority: 3)
- 365 days: 1-year assessment (Priority: 2)

**ACL Reconstruction:**
- 7 days: Post-op wound check (Priority: 4)
- 42 days: 6-week physio review (Priority: 3)
- 90 days: 3-month strength test (Priority: 3)
- 180 days: 6-month return-to-sport assessment (Priority: 2)

**Fracture Fixation:**
- 14 days: Wound check (Priority: 4)
- 42 days: 6-week X-ray (Priority: 4)
- 90 days: 3-month X-ray (union check) (Priority: 3)

### Adding New Rules

To add follow-up rules for a new specialty or procedure:

1. Edit `backend/app/services/followup_intelligence.py`
2. Add to `FOLLOWUP_RULES` dictionary:

```python
FOLLOWUP_RULES = {
    "your_specialty": {
        "Your Procedure Name": [
            {"days": 7, "reason": "Follow-up reason", "priority": 4},
            {"days": 30, "reason": "Another follow-up", "priority": 3},
        ],
    },
}
```

For conditional follow-ups (based on findings):

```python
{
    "days": 180,
    "reason": "Repeat if needed",
    "priority": 3,
    "condition": "your_condition_key",
}
```

Then add condition logic in `_check_condition()` method.

---

## API Endpoints

### Get Insights
```http
GET /api/v1/ai/insights?insight_types=followup_due,revenue_alert&limit=10
```

**Response:**
```json
{
  "insights": [
    {
      "id": "uuid",
      "insight_type": "followup_due",
      "priority": 5,
      "title": "Overdue: Mr. Kumar - Post-stent check",
      "message": "Mr. Kumar is 3 days overdue for post-stent check",
      "suggested_action": {
        "action": "book_appointment",
        "patient_id": "uuid"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

### Get Daily Digest
```http
GET /api/v1/ai/insights/digest
```

**Response:**
```json
{
  "date": "2026-01-04T00:00:00",
  "appointments_today": 24,
  "revenue_yesterday": 125000,
  "pending_followups": [...],
  "schedule_alerts": [...],
  "key_insights": [...]
}
```

### Dismiss Insight
```http
POST /api/v1/ai/insights/{insight_id}/dismiss
```

### Act on Insight
```http
POST /api/v1/ai/insights/{insight_id}/act
```

### Get/Update Digest Preferences
```http
GET /api/v1/ai/preferences/digest
PUT /api/v1/ai/preferences/digest
```

**Request Body:**
```json
{
  "enabled": true,
  "delivery_hour": 8,
  "delivery_minute": 0,
  "channels": ["push", "email"],
  "include_revenue": true,
  "include_followups": true
}
```

---

## Usage Examples

### Automatic Follow-up Creation

When a procedure is recorded, automatically create follow-up schedules:

```python
from app.services.followup_intelligence import FollowupIntelligence

# After procedure is saved
intelligence = FollowupIntelligence(db)
suggestions = await intelligence.suggest_followups_after_procedure(procedure)
schedules = await intelligence.create_followup_schedules(procedure, suggestions)
```

### Generate Daily Insights

```python
from app.services.proactive_insights import ProactiveInsightsEngine

engine = ProactiveInsightsEngine(db)
insights = await engine.generate_daily_insights(clinic_id)

# Insights include:
# - Overdue follow-ups
# - Revenue anomalies
# - No-show risks
# - Schedule gaps
```

### Send Morning Digest

```python
from app.services.daily_digest import DailyDigestService

digest_service = DailyDigestService(db)
await digest_service.send_digest(clinic_id, user_id)
```

### Find Schedule Gaps

```python
from app.services.schedule_optimizer import ScheduleOptimizer

optimizer = ScheduleOptimizer(db)
gaps = await optimizer.find_gaps(
    clinic_id=clinic_id,
    doctor_id=doctor_id,
    target_date=date.today(),
    min_gap_minutes=30,
)

# Returns list of TimeGap objects
for gap in gaps:
    print(f"Gap: {gap.start_time} - {gap.end_time} ({gap.duration_minutes} min)")
```

---

## Mobile UI Components

### Insights Card
**Location:** `mobile/lib/features/ai_assistant/presentation/insights/insights_card.dart`

Displays a single insight with:
- Priority indicator (color-coded)
- Title and message
- One-click action button
- Dismiss button

### Daily Digest Screen
**Location:** `mobile/lib/features/ai_assistant/presentation/insights/daily_digest_screen.dart`

Shows morning digest with:
- Key metrics (appointments, revenue)
- Pending follow-ups list
- Schedule alerts
- Actionable insights

### Follow-up Reminders Widget
**Location:** `mobile/lib/features/ai_assistant/presentation/insights/followup_reminders_widget.dart`

Lists:
- Overdue follow-ups (red)
- Due today (orange)
- Upcoming (green)

---

## Testing

Run tests:
```bash
pytest backend/tests/services/test_proactive_insights.py -v
```

**Test Coverage:**
- Follow-up suggestion generation
- Conditional follow-ups (EF < 40%, etc.)
- Schedule gap detection
- Overbooking risk assessment
- Revenue anomaly detection
- No-show risk identification
- Insight dismissal/action tracking

---

## Scheduled Jobs

### Daily Digest Delivery

**Cron Job:** Every day at user-specified time (default: 8 AM)

```python
# Pseudo-code for scheduler
for user in active_users:
    prefs = get_digest_preferences(user.id)
    if prefs.enabled and is_delivery_time(prefs):
        await daily_digest_service.send_digest(user.clinic_id, user.id)
```

### Insight Generation

**Cron Job:** Every hour during clinic hours (9 AM - 6 PM)

```python
for clinic in active_clinics:
    await insights_engine.generate_daily_insights(clinic.id)
```

---

## Performance Considerations

1. **Index Usage:**
   - Composite indexes on `(clinic_id, dismissed_at, expires_at)` for fast active insights query
   - Composite indexes on `(clinic_id, completed, due_date)` for pending follow-ups

2. **Caching:**
   - Cache daily digest for 1 hour
   - Cache active insights for 15 minutes

3. **Batch Processing:**
   - Generate insights in batches for all clinics
   - Throttle notifications to avoid spam

---

## Future Enhancements

1. **ML-Powered Insights:**
   - Predict no-show probability using ML model
   - Optimize schedule based on historical patterns
   - Personalized follow-up recommendations

2. **Smart Scheduling:**
   - Auto-book follow-ups with patient consent
   - Suggest optimal time slots based on patient preference

3. **Integration:**
   - WhatsApp reminders for follow-ups
   - Email digest with charts
   - Voice notifications

---

## Troubleshooting

### Insights Not Appearing

1. Check if expired: `expires_at < now()`
2. Check if dismissed: `dismissed_at IS NOT NULL`
3. Verify clinic_id matches user's clinic
4. Check insight generation logs

### Follow-ups Not Created

1. Verify procedure category matches `FOLLOWUP_RULES`
2. Check if conditions are met (e.g., EF < 40%)
3. Review logs for errors during procedure save

### Digest Not Delivered

1. Check user preferences: `enabled = true`
2. Verify delivery channels configured
3. Check push token validity
4. Review notification service logs

---

## Security

- **Authorization:** All endpoints require authenticated user
- **Multi-tenancy:** Insights scoped to `clinic_id`
- **Data Privacy:** Patient data in insights follows HIPAA guidelines
- **Audit Trail:** Track who dismissed/acted on insights

---

*Last Updated: 2026-01-04*
*Phase 16c: Proactive Intelligence - Complete*
