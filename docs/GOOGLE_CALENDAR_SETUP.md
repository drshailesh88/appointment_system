# Google Calendar Sync Setup Guide

## Overview

Phase 11 adds bidirectional Google Calendar synchronization to DocAssist Practice Manager, allowing doctors to see their appointments in Google Calendar automatically.

## Features

- ✅ OAuth 2.0 authorization flow
- ✅ Automatic appointment sync to Google Calendar
- ✅ Create/update/delete calendar events
- ✅ Conflict detection
- ✅ Background sync every 15 minutes
- ✅ Encrypted token storage
- ✅ Multi-calendar support
- ✅ Recurring appointment support

## Prerequisites

1. Google Cloud Console account
2. Google Calendar API enabled
3. OAuth 2.0 credentials

## Step 1: Google Cloud Console Setup

### 1.1 Create a New Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name: "DocAssist Practice Manager"
4. Click "Create"

### 1.2 Enable Google Calendar API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Calendar API"
3. Click on it and press "Enable"

### 1.3 Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External (or Internal if using Google Workspace)
   - App name: DocAssist Practice Manager
   - User support email: your email
   - Developer contact: your email
   - Scopes: Add Google Calendar API scopes
     - `.../auth/calendar.events` (Read/write access to events)
     - `.../auth/calendar.readonly` (Read-only access to calendars)
   - Test users: Add doctor's email addresses
4. Return to Credentials → Create OAuth client ID:
   - Application type: Web application
   - Name: DocAssist Calendar Sync
   - Authorized redirect URIs:
     - `http://localhost:8000/api/v1/calendar/callback` (development)
     - `https://yourdomain.com/api/v1/calendar/callback` (production)
5. Click "Create"
6. Download the JSON file or copy Client ID and Client Secret

## Step 2: Backend Configuration

### 2.1 Install Dependencies

```bash
cd backend
pip install -r requirements-calendar.txt
```

### 2.2 Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the generated key.

### 2.3 Update Environment Variables

Add to `backend/.env`:

```env
# Google Calendar Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/calendar/callback
CALENDAR_ENCRYPTION_KEY=your-fernet-key-from-step-2.2
```

### 2.4 Run Database Migration

```bash
cd backend
alembic upgrade head
```

This creates:
- `doctor_calendar_settings` table
- Calendar sync columns in `appointments` table

## Step 3: Usage

### 3.1 Doctor Connects Calendar

**Frontend Flow:**

```typescript
// 1. Get authorization URL
const response = await fetch(
  `/api/v1/calendar/auth-url?doctor_id=${doctorId}`,
  {
    headers: { Authorization: `Bearer ${token}` }
  }
);
const { auth_url, state } = await response.json();

// 2. Redirect user to auth_url
window.location.href = auth_url;

// 3. User grants permission and is redirected back to callback

// 4. Handle callback (backend does this automatically)
// Doctor's calendar is now connected!
```

**Backend automatically handles:**
- OAuth token exchange
- Refresh token encryption and storage
- Calendar listing

### 3.2 Check Calendar Status

```bash
GET /api/v1/calendar/status?doctor_id={uuid}

Response:
{
  "connected": true,
  "sync_enabled": true,
  "last_synced_at": "2026-01-04T10:30:00Z",
  "calendar_id": "primary",
  "pending_sync_count": 5
}
```

### 3.3 Manual Sync Trigger

```bash
POST /api/v1/calendar/sync
{
  "doctor_id": "uuid",
  "force": false  // true to sync all appointments
}

Response:
{
  "synced": 25,
  "failed": 2,
  "errors": ["Event ID 123: Rate limit exceeded"]
}
```

### 3.4 Check for Conflicts

```bash
POST /api/v1/calendar/conflicts
{
  "doctor_id": "uuid",
  "start_time": "2026-01-05T10:00:00Z",
  "end_time": "2026-01-05T11:00:00Z"
}

Response:
{
  "has_conflict": true,
  "conflicts": [
    {
      "event_id": "abc123",
      "summary": "Meeting with Team",
      "start": "2026-01-04T10:00:00Z",
      "end": "2026-01-04T11:00:00Z"
    }
  ]
}
```

### 3.5 Disconnect Calendar

```bash
DELETE /api/v1/calendar/disconnect
{
  "doctor_id": "uuid"
}

Response:
{
  "success": true,
  "message": "Calendar disconnected successfully"
}
```

## Step 4: Automatic Sync

### How It Works

1. **Appointment Creation:** Calendar event created immediately
2. **Appointment Update:** Calendar event updated immediately
3. **Appointment Cancellation:** Calendar event deleted immediately
4. **Background Sync:** Every 15 minutes, syncs any missed changes

### Background Sync

The background sync service:
- Runs every 15 minutes
- Syncs appointments modified since last sync
- Retries failed syncs with exponential backoff
- Logs all operations

**View logs:**
```bash
tail -f logs/calendar_sync.log
```

## Step 5: Calendar Event Details

### Event Format

**Summary:**
```
Appointment: John Doe
```

**Description:**
```
Patient: John Doe
Phone: +91 9876543210
Type: New Consultation
Reason: Regular checkup

---
Booked via DocAssist Practice Manager
```

**Time:** Matches appointment scheduled_start and scheduled_end

**Visibility:** Private by default (configurable per doctor)

**Reminders:** 30 minutes before (configurable)

## Advanced Configuration

### Change Sync Interval

In `backend/app/main.py`:

```python
await start_background_sync(interval_minutes=10)  # Sync every 10 minutes
```

### Custom Event Visibility

Update doctor calendar settings:

```sql
UPDATE doctor_calendar_settings
SET event_visibility = 'public'  -- or 'private', 'default'
WHERE doctor_id = '...';
```

### Custom Reminders

Update doctor calendar settings:

```sql
UPDATE doctor_calendar_settings
SET event_reminders = '{
  "useDefault": false,
  "overrides": [
    {"method": "popup", "minutes": 30},
    {"method": "email", "minutes": 1440}
  ]
}'::jsonb
WHERE doctor_id = '...';
```

## Troubleshooting

### "Google Calendar not configured"

**Solution:** Ensure environment variables are set:
```bash
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET
```

### "Invalid state token"

**Solution:** State tokens expire. User must restart OAuth flow.

### "Token refresh failed"

**Solution:**
1. Check if refresh token is still valid
2. User may need to re-authorize
3. Check Google Cloud Console for API quota limits

### "Rate limit exceeded"

**Solution:**
- Google Calendar API has quotas (10,000 requests/day)
- Reduce sync frequency if hitting limits
- Use batch requests for multiple events

### Sync not happening

**Check:**
1. Background service started: Look for "Background calendar sync initialized" in logs
2. Doctor has `sync_enabled = true`
3. Check `last_sync_error` in `doctor_calendar_settings`

## Security Best Practices

1. **Never commit credentials:**
   - Add `.env` to `.gitignore`
   - Use environment variables in production

2. **Rotate encryption keys:**
   - Generate new key
   - Re-encrypt all refresh tokens
   - Update `CALENDAR_ENCRYPTION_KEY`

3. **OAuth scope minimal:**
   - Only request calendar.events (not full calendar access)

4. **HTTPS in production:**
   - Always use HTTPS for redirect URIs
   - Enable secure cookies

## API Rate Limits

**Google Calendar API Limits:**
- Queries per day: 1,000,000
- Queries per 100 seconds per user: 1,000
- Queries per 100 seconds: 50,000

**Best Practices:**
- Use batch requests when syncing multiple events
- Implement exponential backoff on errors
- Cache calendar data when possible

## Production Deployment Checklist

- [ ] Google Cloud Console project created
- [ ] OAuth credentials created with production redirect URI
- [ ] Environment variables set in production
- [ ] Database migration run
- [ ] HTTPS enabled
- [ ] Background sync service running
- [ ] Monitoring and logging configured
- [ ] Rate limiting configured
- [ ] Backup strategy for calendar settings

## Testing

Run tests:

```bash
cd backend
pytest tests/test_calendar_sync.py -v
```

## Support

For issues:
1. Check logs: `logs/calendar_sync.log`
2. Review Google Cloud Console API dashboard
3. Check database: `SELECT * FROM doctor_calendar_settings;`

## References

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/guides/overview)
- [OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Last Updated:** 2026-01-04
**Version:** 1.0
**Phase:** 11 - Google Calendar Sync
