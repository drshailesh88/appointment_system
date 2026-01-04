# Phase 16c: Proactive Intelligence - Quick Start Guide

## 🚀 Quick Deploy

### 1. Run Database Migration
```bash
cd /home/user/appointment_system/backend
alembic upgrade head
```

### 2. Verify Migration
```bash
# Should show 010_add_proactive_insights as current
alembic current
```

### 3. Test the Services
```bash
pytest tests/services/test_proactive_insights.py -v
```

### 4. Start Server
```bash
uvicorn app.main:app --reload
```

### 5. Test API Endpoints
```bash
# Get insights
curl http://localhost:8000/api/v1/ai/insights

# Get daily digest
curl http://localhost:8000/api/v1/ai/insights/digest
```

---

## 📂 File Structure

```
backend/
├── app/
│   ├── models/
│   │   └── insight.py .......................... 300 lines (NEW)
│   ├── schemas/
│   │   └── insights.py ......................... 207 lines (NEW)
│   ├── services/
│   │   ├── followup_intelligence.py ............ 411 lines (NEW)
│   │   ├── schedule_optimizer.py ............... 415 lines (NEW)
│   │   ├── proactive_insights.py ............... 475 lines (NEW)
│   │   ├── daily_digest.py ..................... 331 lines (NEW)
│   │   └── README_PROACTIVE_INTELLIGENCE.md .... (NEW)
│   └── api/v1/
│       └── ai_chat.py .......................... (MODIFIED +260 lines)
├── alembic/versions/
│   └── 010_add_proactive_insights.py ........... 217 lines (NEW)
└── tests/services/
    └── test_proactive_insights.py .............. 371 lines (NEW)
```

**Total:** 2,727 lines of Python code

---

## 🎯 Key Features Implemented

### ✅ Follow-up Intelligence
- **20+ procedure types** across 5 specialties
- **Automatic scheduling** when procedures recorded
- **Conditional rules** (e.g., EF < 40% → repeat echo)
- **Priority-based** reminders

### ✅ Schedule Optimization
- **Gap detection** for waitlist filling
- **Buffer time** suggestions per patient
- **Overbooking risk** assessment
- **Optimal slot** finding

### ✅ Proactive Insights
- **Follow-up reminders** (overdue + upcoming)
- **Revenue anomaly** detection (>30% deviation)
- **No-show risk** identification (>40% rate)
- **One-click actions** (book, remind, offer)

### ✅ Daily Digest
- **Personalized** morning summary
- **Multi-channel** (push, email, SMS)
- **User preferences** (time, content filters)
- **Key metrics** (appointments, revenue, insights)

---

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/ai/insights` | Get active insights |
| GET | `/api/v1/ai/insights/digest` | Get daily digest |
| POST | `/api/v1/ai/insights/{id}/dismiss` | Dismiss insight |
| POST | `/api/v1/ai/insights/{id}/act` | Act on insight |
| GET | `/api/v1/ai/preferences/digest` | Get preferences |
| PUT | `/api/v1/ai/preferences/digest` | Update preferences |

---

## 📊 Database Tables

### `proactive_insights`
- Stores AI-generated insights
- Tracks dismissals/actions
- Expires automatically

### `followup_schedules`
- Links to procedures
- Due dates with priorities
- Completion tracking

### `user_digest_preferences`
- Delivery time/channels
- Content filters
- Per-user settings

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/services/test_proactive_insights.py -v

# Run specific test
pytest tests/services/test_proactive_insights.py::TestFollowupIntelligence::test_suggest_followups_after_stent -v

# With coverage
pytest tests/services/test_proactive_insights.py --cov=app.services --cov-report=html
```

**Test Coverage:**
- ✅ Follow-up suggestions (all specialties)
- ✅ Conditional follow-ups
- ✅ Schedule gap detection
- ✅ Overbooking risk
- ✅ Revenue anomalies
- ✅ No-show risk
- ✅ Insight management

---

## 🔧 Usage Examples

### Create Follow-up After Procedure
```python
from app.services.followup_intelligence import FollowupIntelligence

intelligence = FollowupIntelligence(db)
schedules = await intelligence.create_followup_schedules(procedure)
# Auto-creates 7-day, 30-day, 180-day follow-ups for stent
```

### Generate Daily Insights
```python
from app.services.proactive_insights import ProactiveInsightsEngine

engine = ProactiveInsightsEngine(db)
insights = await engine.generate_daily_insights(clinic_id)
# Returns follow-ups, revenue alerts, no-show risks
```

### Send Morning Digest
```python
from app.services.daily_digest import DailyDigestService

digest_service = DailyDigestService(db)
await digest_service.send_digest(clinic_id, user_id)
# Sends via push/email/SMS based on preferences
```

---

## 📱 Mobile UI (To Be Implemented)

Create these Flutter widgets:

1. **`insights_card.dart`**
   - Display single insight
   - One-click action button
   - Dismiss button

2. **`daily_digest_screen.dart`**
   - Morning summary view
   - Metrics + insights
   - Swipeable cards

3. **`followup_reminders_widget.dart`**
   - Overdue (red)
   - Due today (orange)
   - Upcoming (green)

---

## ⚙️ Configuration

### Environment Variables
```bash
# In .env
ENABLE_PROACTIVE_INSIGHTS=true
DIGEST_DELIVERY_HOUR=8
INSIGHT_RETENTION_DAYS=7
```

### Scheduled Jobs
```bash
# Crontab entries

# Generate insights every hour (9 AM - 6 PM)
0 9-18 * * * /path/to/generate_insights.py

# Send morning digests at 8 AM
0 8 * * * /path/to/send_digests.py
```

---

## 🎓 Follow-up Rules Reference

### Cardiology
| Procedure | Follow-ups |
|-----------|------------|
| Stent Placement | 7d, 30d, 180d |
| Angioplasty | 7d, 90d |
| Pacemaker | 1d, 7d, 90d, 180d |
| Echo (EF<40%) | 180d |

### Ophthalmology
| Procedure | Follow-ups |
|-----------|------------|
| Cataract Surgery | 1d, 7d, 30d |
| LASIK | 1d, 7d, 90d |
| Intravitreal Injection | 28d (recurring) |

### Orthopedics
| Procedure | Follow-ups |
|-----------|------------|
| Knee Replacement | 14d, 42d, 90d, 365d |
| ACL Reconstruction | 7d, 42d, 90d, 180d |
| Fracture Fixation | 14d, 42d, 90d |

**See `README_PROACTIVE_INTELLIGENCE.md` for complete list**

---

## 🐛 Troubleshooting

### Insights Not Showing
```python
# Check if expired
SELECT * FROM proactive_insights WHERE expires_at < NOW();

# Check if dismissed
SELECT * FROM proactive_insights WHERE dismissed_at IS NOT NULL;

# Regenerate
await engine.generate_daily_insights(clinic_id)
```

### Follow-ups Not Created
```python
# Verify procedure category matches rules
assert procedure.category in ["Cardiology", "Ophthalmology", ...]

# Check logs
tail -f logs/followup_intelligence.log
```

### Digest Not Delivered
```python
# Check preferences
prefs = await digest_service.get_user_preferences(user_id)
print(prefs.enabled, prefs.channels)

# Send manually
await digest_service.send_digest(clinic_id, user_id)
```

---

## 📚 Documentation

- **Full Guide:** `/backend/app/services/README_PROACTIVE_INTELLIGENCE.md`
- **Implementation Summary:** `/PHASE_16C_IMPLEMENTATION_SUMMARY.md`
- **API Docs:** Auto-generated at `/docs` when server running

---

## ✅ Checklist

- [x] Models created (insight.py)
- [x] Schemas created (insights.py)
- [x] Services implemented (4 files)
- [x] API endpoints added (6 endpoints)
- [x] Database migration created (010)
- [x] Tests written (12+ test cases)
- [x] Documentation completed
- [ ] Database migration run
- [ ] Mobile UI implemented
- [ ] Scheduled jobs configured
- [ ] Production deployment

---

## 🚀 Next Steps

1. **Run migration:** `alembic upgrade head`
2. **Test endpoints:** Use Postman/curl
3. **Implement mobile UI:** Create Flutter widgets
4. **Set up cron jobs:** Schedule insight generation
5. **Monitor performance:** Add logging/metrics
6. **Go live:** Deploy to production

---

*Quick Start Guide for Phase 16c*
*Last Updated: 2026-01-04*
