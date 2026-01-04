# Phase 12: Patient Booking Portal - Quick Start Guide

## 🚀 What Was Built

A complete **Practo-killer** patient booking portal with:
- ✅ Next.js 14 web application (TypeScript + Tailwind CSS)
- ✅ Backend public API endpoints
- ✅ OTP-based patient authentication
- ✅ Real-time slot booking
- ✅ Appointment management
- ✅ Mobile-responsive design

---

## 📁 Files Created

### Backend (6 files)
```
backend/app/
├── models/otp.py                    # OTP model for authentication
├── schemas/public.py                # Public API request/response schemas
├── services/otp_service.py          # OTP generation and verification
└── api/v1/public.py                 # Public booking API endpoints
```

### Frontend (13 files)
```
web/
├── src/
│   ├── lib/api-client.ts           # Backend API client
│   ├── components/
│   │   ├── DoctorCard.tsx          # Doctor preview card
│   │   ├── SlotPicker.tsx          # Interactive slot selector
│   │   ├── OTPVerification.tsx     # OTP login modal
│   │   └── AppointmentCard.tsx     # Appointment display
│   └── app/
│       ├── page.tsx                # Home page
│       ├── layout.tsx              # Root layout
│       ├── doctors/
│       │   ├── page.tsx            # Doctors listing
│       │   └── [id]/page.tsx       # Doctor detail + booking
│       └── appointments/
│           ├── page.tsx            # My appointments
│           └── [id]/page.tsx       # Appointment detail
├── .env.local                      # Environment config
└── README.md                       # Documentation
```

---

## ⚡ Quick Start

### 1. Setup Backend

```bash
# No additional packages needed - all dependencies already installed
cd /home/user/appointment_system/backend

# Create database migration for OTP table
alembic revision --autogenerate -m "Add OTP model"
alembic upgrade head

# Backend is ready! (Already running if main server is up)
```

### 2. Setup Frontend

```bash
cd /home/user/appointment_system/web

# Dependencies already installed during creation
# Just verify the build
npm run build

# Start development server
npm run dev
```

### 3. Access the Portal

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/v1/public
- **API Docs**: http://localhost:8000/docs (check `/public` endpoints)

---

## 🔗 API Endpoints

### Public (No Auth Required)
```
GET  /api/v1/public/doctors              # List doctors
GET  /api/v1/public/doctors/{id}         # Doctor details
GET  /api/v1/public/doctors/{id}/slots   # Available slots
POST /api/v1/public/otp/send             # Send OTP
POST /api/v1/public/otp/verify           # Verify OTP
```

### Authenticated (OTP Token Required)
```
POST   /api/v1/public/appointments       # Book appointment
GET    /api/v1/public/appointments       # My appointments
GET    /api/v1/public/appointments/{id}  # Appointment detail
DELETE /api/v1/public/appointments/{id}  # Cancel appointment
```

---

## 🧪 Testing the Flow

### 1. Browse Doctors (No Login)
```bash
# List all doctors
curl http://localhost:8000/api/v1/public/doctors

# Get doctor details
curl http://localhost:8000/api/v1/public/doctors/{DOCTOR_ID}

# Get available slots for a date
curl "http://localhost:8000/api/v1/public/doctors/{DOCTOR_ID}/slots?date_param=2026-01-05"
```

### 2. OTP Authentication
```bash
# Send OTP
curl -X POST http://localhost:8000/api/v1/public/otp/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "9876543210"}'

# Check backend logs for OTP code (development mode)
# In production, this will be sent via SMS

# Verify OTP
curl -X POST http://localhost:8000/api/v1/public/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "9876543210", "otp_code": "123456"}'

# Save the access_token from response
```

### 3. Book Appointment (Authenticated)
```bash
# Book appointment
curl -X POST http://localhost:8000/api/v1/public/appointments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "doctor_id": "DOCTOR_UUID",
    "scheduled_start": "2026-01-05T10:00:00Z",
    "duration_minutes": 15,
    "first_name": "John",
    "last_name": "Doe",
    "phone": "9876543210",
    "email": "john@example.com",
    "chief_complaint": "Regular checkup"
  }'
```

### 4. View Appointments
```bash
# Get my appointments
curl http://localhost:8000/api/v1/public/appointments \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get specific appointment
curl http://localhost:8000/api/v1/public/appointments/{APPOINTMENT_ID} \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 🎨 Frontend Features

### Home Page (/)
- Search doctors by specialization and city
- Popular specializations quick access
- Feature highlights

### Doctors Listing (/doctors)
- Filter by specialization and city
- View all active doctors
- Click to see details

### Doctor Detail (/doctors/[id])
- Complete doctor profile
- Interactive slot picker (7 days)
- Patient details form
- OTP login (if not authenticated)
- Book appointment

### My Appointments (/appointments)
- OTP login required
- View all appointments
- Filter by status (scheduled, completed, cancelled)
- Cancel appointments
- View details

---

## 🔐 OTP Flow (Development)

**Important:** In development mode, OTP codes are logged to the console:

```python
# backend/app/services/otp_service.py
logger.info(f"OTP for {phone}: {otp_code} (expires in 10min)")
```

**Production Setup:**
1. Configure MSG91 credentials in `.env`
2. Update `otp_service.py` to send SMS
3. Remove console logging

---

## 🗄️ Database Migration

The OTP table needs to be created:

```sql
CREATE TABLE otps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0,
    patient_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_otps_phone ON otps(phone);
CREATE INDEX idx_otps_created_at ON otps(created_at);
```

Or use Alembic:
```bash
cd /home/user/appointment_system/backend
alembic revision --autogenerate -m "Add OTP model"
alembic upgrade head
```

---

## 🚨 Important Notes

### Security
- OTP expires in 10 minutes
- Max 3 verification attempts
- JWT tokens expire in 24 hours
- Tokens stored in localStorage (client-side)

### Data Flow
1. Patient browses doctors (no auth)
2. Selects slot and fills form
3. OTP sent to phone
4. OTP verified → JWT token
5. Appointment created with token
6. Patient record auto-created if new

### Patient Creation
- Automatic on first booking
- Uses phone from OTP token
- Linked to doctor's clinic
- Additional details from booking form

---

## 📊 Next Steps

### Immediate (Required)
1. ✅ Run database migration
2. ⏳ Configure SMS gateway (MSG91)
3. ⏳ Test OTP flow end-to-end
4. ⏳ Deploy frontend to Vercel
5. ⏳ Update CORS settings

### Short-term (Recommended)
1. Add email confirmation
2. Implement appointment reminders
3. Add doctor availability rules
4. Enable online payment (Phase 14)
5. Add analytics tracking

### Long-term (Nice to Have)
1. Embeddable booking widget
2. Multi-language support
3. Patient portal (medical history)
4. Doctor ratings and reviews
5. Mobile apps (iOS/Android)

---

## 📚 Documentation

- **Full Implementation**: `PHASE_12_IMPLEMENTATION_SUMMARY.md`
- **Web README**: `web/README.md`
- **API Documentation**: http://localhost:8000/docs

---

## ✅ Verification Checklist

- [x] Next.js project created
- [x] TypeScript configured
- [x] Tailwind CSS working
- [x] Backend API endpoints created
- [x] OTP model and service implemented
- [x] API client created
- [x] All components built
- [x] All pages created
- [x] Production build successful
- [x] Mobile-responsive design
- [ ] Database migration run
- [ ] SMS gateway configured
- [ ] End-to-end testing
- [ ] Production deployment

---

**Status:** ✅ READY FOR TESTING
**Phase:** 12 COMPLETE
**Build:** ✅ SUCCESS

Start the servers and visit http://localhost:3000 to see it live!
