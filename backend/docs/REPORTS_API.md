# Reports API Documentation

## Overview

The Reports API provides comprehensive report generation and scheduling functionality for DocAssist Practice Manager. Reports can be generated on-demand or scheduled for automatic delivery via email.

## Features

- **Multiple Report Types**: Daily/Weekly/Monthly summaries, Doctor performance, Revenue reports, Patient demographics, No-show analysis
- **Multiple Formats**: PDF (with charts), Excel (.xlsx), CSV
- **On-Demand Generation**: Generate reports instantly via API
- **Scheduled Reports**: Automate report generation and email delivery
- **Professional Formatting**: Clinic branding, charts, and professional layouts

## Report Types

| Report Type | Description | Supports Charts |
|-------------|-------------|-----------------|
| `daily_summary` | Daily appointment and revenue summary | No |
| `weekly_summary` | Weekly performance with trends | Yes |
| `monthly_summary` | Comprehensive monthly analysis | Yes |
| `doctor_performance` | Individual doctor metrics | No |
| `revenue_report` | Detailed revenue breakdown | Yes |
| `patient_demographics` | Patient population analysis | No |
| `no_show_analysis` | No-show patterns by time/day | Yes |

## API Endpoints

### 1. List Report Templates

```http
GET /api/v1/reports/templates
```

Returns all available report types with their configurations.

**Response:**
```json
[
  {
    "type": "daily_summary",
    "name": "Daily Summary",
    "description": "Daily appointment and revenue summary",
    "supported_formats": ["pdf", "xlsx", "csv"],
    "default_format": "pdf",
    "parameters": []
  }
]
```

### 2. Generate Report (On-Demand)

```http
POST /api/v1/reports/generate
```

**Request Body:**
```json
{
  "report_type": "weekly_summary",
  "format": "pdf",
  "start_date": "2026-01-01",
  "end_date": "2026-01-07",
  "parameters": {
    "doctor_id": "uuid-here"  // optional, for doctor_performance
  }
}
```

**Response:**
- Returns the report file directly for download
- Content-Type: `application/pdf`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, or `text/csv`
- Content-Disposition: `attachment; filename=report.pdf`

**Example (cURL):**
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
  --output monthly_report.pdf
```

### 3. List Scheduled Reports

```http
GET /api/v1/reports/scheduled?active_only=true
```

**Response:**
```json
[
  {
    "id": "report-uuid",
    "name": "Weekly Performance Report",
    "description": "Weekly report sent every Monday",
    "report_type": "weekly_summary",
    "report_format": "pdf",
    "frequency": "weekly",
    "cron_expression": null,
    "recipients": ["admin@clinic.com", "doctor@clinic.com"],
    "parameters": null,
    "is_active": true,
    "last_run_at": "2026-01-01T09:00:00Z",
    "next_run_at": "2026-01-08T09:00:00Z",
    "last_run_status": "success",
    "created_at": "2025-12-01T10:00:00Z"
  }
]
```

### 4. Create Scheduled Report

```http
POST /api/v1/reports/scheduled
```

**Request Body:**
```json
{
  "name": "Weekly Performance Report",
  "description": "Automated weekly summary sent to management",
  "report_type": "weekly_summary",
  "report_format": "pdf",
  "frequency": "weekly",
  "recipients": ["admin@clinic.com", "manager@clinic.com"],
  "parameters": null
}
```

**Frequency Options:**
- `daily` - Daily at 8 AM
- `weekly` - Weekly on Monday at 9 AM
- `monthly` - Monthly on 1st at 10 AM
- `custom` - Use custom cron expression

**Custom Cron Expression Example:**
```json
{
  "name": "Bi-weekly Report",
  "frequency": "custom",
  "cron_expression": "0 9 * * 1,3",  // Monday and Wednesday at 9 AM
  "..."
}
```

**Response:**
```json
{
  "id": "new-report-uuid",
  "name": "Weekly Performance Report",
  "..."
}
```

### 5. Get Scheduled Report Details

```http
GET /api/v1/reports/scheduled/{report_id}
```

### 6. Update Scheduled Report

```http
PATCH /api/v1/reports/scheduled/{report_id}
```

**Request Body (all fields optional):**
```json
{
  "name": "Updated Report Name",
  "description": "New description",
  "recipients": ["new@email.com"],
  "is_active": false
}
```

### 7. Delete Scheduled Report

```http
DELETE /api/v1/reports/scheduled/{report_id}
```

### 8. Run Scheduled Report Now

```http
POST /api/v1/reports/scheduled/{report_id}/run-now?start_date=2026-01-01&end_date=2026-01-07
```

Generates the scheduled report immediately with optional custom date range.

## Usage Examples

### Example 1: Generate Monthly Revenue Report (Python)

```python
import httpx
from datetime import date, timedelta

# Calculate last month
today = date.today()
first_of_month = today.replace(day=1)
last_month_end = first_of_month - timedelta(days=1)
last_month_start = last_month_end.replace(day=1)

# Generate report
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/reports/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "report_type": "revenue_report",
            "format": "pdf",
            "start_date": last_month_start.isoformat(),
            "end_date": last_month_end.isoformat(),
        }
    )

    # Save report
    with open("revenue_report.pdf", "wb") as f:
        f.write(response.content)
```

### Example 2: Schedule Daily Summary Email

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/reports/scheduled",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Daily Practice Summary",
            "description": "Daily summary sent every morning at 8 AM",
            "report_type": "daily_summary",
            "report_format": "pdf",
            "frequency": "daily",
            "recipients": [
                "admin@clinic.com",
                "doctor@clinic.com"
            ],
        }
    )

    scheduled_report = response.json()
    print(f"Created report: {scheduled_report['id']}")
    print(f"Next run: {scheduled_report['next_run_at']}")
```

### Example 3: Generate Doctor Performance Report (JavaScript)

```javascript
const token = 'YOUR_AUTH_TOKEN';
const doctorId = 'doctor-uuid-here';

const response = await fetch('http://localhost:8000/api/v1/reports/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    report_type: 'doctor_performance',
    format: 'xlsx',
    start_date: '2026-01-01',
    end_date: '2026-01-31',
    parameters: {
      doctor_id: doctorId
    }
  })
});

const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'doctor_performance.xlsx';
a.click();
```

## Report Formats

### PDF
- Professional layout with clinic branding
- Charts and graphs (for supported reports)
- Table formatting with alternating row colors
- Page headers and footers
- Suitable for printing

### Excel (.xlsx)
- Formatted tables with headers
- Color-coded rows
- Auto-adjusted column widths
- Ready for further analysis in Excel

### CSV
- Plain text format
- Easy to import into databases
- Compatible with all spreadsheet applications
- Smallest file size

## Email Configuration

For scheduled reports to work, configure SMTP settings in your environment:

```bash
# .env file
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=reports@docassist.com
```

## Cron Expression Reference

For custom scheduling, use standard cron expressions:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

**Examples:**
- `0 9 * * 1` - Every Monday at 9 AM
- `0 8 1 * *` - 1st of every month at 8 AM
- `0 18 * * 1-5` - Every weekday at 6 PM
- `0 9 1,15 * *` - 1st and 15th of month at 9 AM

## Error Handling

### Invalid Report Type
```json
{
  "detail": "Invalid report type: invalid_type"
}
```

### Invalid Date Range
```json
{
  "detail": "start_date must be before end_date"
}
```

### Scheduled Report Not Found
```json
{
  "detail": "Scheduled report not found"
}
```

## Performance Considerations

- **Large Date Ranges**: Reports covering >3 months may take longer to generate
- **PDF with Charts**: Slightly slower than CSV/Excel due to chart rendering
- **Scheduled Reports**: Run in background, won't block API
- **Concurrent Generation**: Multiple reports can generate simultaneously

## Database Migration

Run the migration to create the scheduled_reports table:

```bash
cd /home/user/appointment_system/backend
alembic upgrade head
```

This creates the `scheduled_reports` table with all necessary indexes.

## Testing

### Unit Tests
```bash
pytest tests/test_report_generator.py -v
pytest tests/test_report_scheduler.py -v
pytest tests/api/test_reports.py -v
```

### Manual Testing
1. Generate a daily summary report
2. Schedule a weekly report
3. Verify email delivery
4. Test different formats (PDF, Excel, CSV)
5. Test custom date ranges

## Troubleshooting

### Reports Not Being Sent
1. Check SMTP configuration in `.env`
2. Verify `is_active=true` for scheduled report
3. Check logs for scheduler errors
4. Ensure `next_run_at` is in the future

### PDF Generation Fails
1. Ensure matplotlib backend is set to 'Agg'
2. Check reportlab installation
3. Verify /tmp directory is writable (for chart images)

### Charts Not Appearing
1. Matplotlib must be installed
2. Backend must be 'Agg' (non-interactive)
3. Check for chart generation errors in logs

## Future Enhancements

- [ ] Custom report templates
- [ ] Multiple recipients with different formats
- [ ] Report history/archive
- [ ] WhatsApp delivery option
- [ ] Dashboard widgets from reports
- [ ] Interactive charts in PDF
- [ ] Scheduled report analytics

---

**Last Updated:** 2026-01-04
**API Version:** v1
