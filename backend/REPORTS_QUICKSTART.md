# Reports Backend - Quick Start Guide

## Installation

```bash
# 1. Install dependencies
cd /home/user/appointment_system/backend
pip install -r requirements.txt

# 2. Run database migration
alembic upgrade head

# 3. (Optional) Configure email for scheduled reports
# Edit .env and add:
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-password

# 4. Start the server
uvicorn app.main:app --reload
```

## Quick Examples

### 1. Generate a Monthly Report (PDF)

```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "monthly_summary",
    "format": "pdf",
    "start_date": "2026-01-01",
    "end_date": "2026-01-31"
  }' \
  --output report.pdf
```

### 2. Schedule a Weekly Report

```bash
curl -X POST "http://localhost:8000/api/v1/reports/scheduled" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly Summary",
    "report_type": "weekly_summary",
    "report_format": "pdf",
    "frequency": "weekly",
    "recipients": ["admin@clinic.com"]
  }'
```

### 3. List Available Report Types

```bash
curl "http://localhost:8000/api/v1/reports/templates" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. View Scheduled Reports

```bash
curl "http://localhost:8000/api/v1/reports/scheduled" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Report Types

| Type | Description |
|------|-------------|
| `daily_summary` | Daily appointments & revenue |
| `weekly_summary` | Weekly trends with charts |
| `monthly_summary` | Comprehensive monthly report |
| `doctor_performance` | Doctor KPIs |
| `revenue_report` | Revenue breakdown with charts |
| `patient_demographics` | Patient population analysis |
| `no_show_analysis` | No-show patterns |

## Formats

- **PDF**: Professional layout with charts (recommended)
- **XLSX**: Excel format for analysis
- **CSV**: Plain data export

## API Endpoints

```
GET    /api/v1/reports/templates              # List report types
POST   /api/v1/reports/generate               # Generate report
GET    /api/v1/reports/scheduled              # List scheduled
POST   /api/v1/reports/scheduled              # Create scheduled
GET    /api/v1/reports/scheduled/{id}         # Get details
PATCH  /api/v1/reports/scheduled/{id}         # Update
DELETE /api/v1/reports/scheduled/{id}         # Delete
POST   /api/v1/reports/scheduled/{id}/run-now # Generate now
```

## Scheduling Frequencies

- `daily` - Every day at 8 AM
- `weekly` - Every Monday at 9 AM
- `monthly` - 1st of month at 10 AM
- `custom` - Use cron expression

### Cron Examples

```
0 9 * * 1      # Monday at 9 AM
0 8 1,15 * *   # 1st and 15th at 8 AM
0 18 * * 1-5   # Weekdays at 6 PM
```

## Testing

```bash
# Run tests (when created)
pytest tests/test_report_generator.py -v
pytest tests/api/test_reports.py -v
```

## Documentation

- **Full API Docs**: `/home/user/appointment_system/backend/docs/REPORTS_API.md`
- **Implementation Details**: `/home/user/appointment_system/backend/REPORTS_IMPLEMENTATION.md`
- **Interactive Docs**: `http://localhost:8000/docs` (when server running)

## Files Created

```
backend/
├── app/
│   ├── models/
│   │   └── scheduled_report.py          # ScheduledReport model
│   ├── services/
│   │   ├── report_generator.py          # Report generation
│   │   └── report_scheduler.py          # Scheduling logic
│   └── api/v1/
│       └── reports.py                   # API endpoints
├── alembic/versions/
│   └── 004_add_scheduled_reports.py     # Database migration
└── docs/
    └── REPORTS_API.md                   # API documentation
```

## Troubleshooting

**Reports not generating?**
- Check logs for errors
- Verify user has clinic_id
- Ensure date range is valid

**Email not sending?**
- Verify SMTP config in .env
- Check scheduled report is active
- Review error logs

**Charts missing in PDF?**
- Ensure matplotlib installed
- Check /tmp is writable

## Support

For detailed documentation, see:
- `docs/REPORTS_API.md` - Complete API reference
- `REPORTS_IMPLEMENTATION.md` - Technical details
- `http://localhost:8000/docs` - Interactive API docs

---

**Quick Start Created**: 2026-01-04
