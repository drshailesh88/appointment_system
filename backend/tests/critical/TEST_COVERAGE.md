# Appointment Booking Test Coverage

## Test File Location
`/home/user/appointment_system/backend/tests/critical/test_appointment_booking.py`

## Statistics
- **Total Lines:** 1,652
- **Test Methods:** 49
- **Test Classes:** 9

## Test Coverage by Category

### 1. Happy Path Tests (TestAppointmentBookingHappyPath)
✅ Book new appointment with valid data
✅ Book appointment with minimal data (required fields only)
✅ Reschedule existing appointment
✅ Cancel appointment with reason
✅ Get appointment by ID
✅ List appointments by doctor
✅ List appointments by patient
✅ List appointments by date range
✅ List appointments by status filter

### 2. Edge Cases (TestAppointmentBookingEdgeCases)
✅ Prevent double booking same slot
✅ Prevent overlapping appointments
✅ Booking in past (allowed for walk-ins)
✅ Booking outside clinic hours (allowed, validated elsewhere)
✅ Booking with non-existent patient (404 error)
✅ Booking with non-existent doctor (404 error)
✅ Patient and doctor from different clinics (400 error)
✅ Valid status transitions: scheduled → checked_in → in_progress → completed
✅ Invalid transition: start without check-in (400 error)
✅ Invalid transition: complete without start (400 error)
✅ Cannot cancel completed appointment
✅ Cannot cancel already cancelled appointment
✅ Mark patient as no-show

### 3. Validation Tests (TestAppointmentBookingValidation)
✅ Missing required field: patient_id (422 error)
✅ Missing required field: doctor_id (422 error)
✅ Missing required field: scheduled_start (422 error)
✅ Invalid UUID format for patient_id (422 error)
✅ Invalid UUID format for doctor_id (422 error)
✅ Invalid datetime format (422 error)
✅ Duration too short (< 5 minutes) (422 error)
✅ Duration too long (> 120 minutes) (422 error)
✅ Chief complaint exceeds max length (500 chars) (422 error)
✅ Chief complaint at exactly max length (201 success)
✅ Invalid appointment_type enum (422 error)
✅ Invalid booking_source enum (422 error)
✅ Get non-existent appointment (404 error)
✅ Update non-existent appointment (404 error)
✅ Cancel non-existent appointment (404 error)

### 4. Slot Availability Tests (TestAppointmentSlotAvailability)
✅ Get available slots for doctor on specific date
✅ Available slots exclude booked times
✅ Slot availability for non-existent doctor (404 error)

### 5. Doctor Schedule Tests (TestAppointmentDoctorSchedule)
✅ Get doctor's schedule for today
✅ Get doctor's schedule for specific date
✅ Schedule correctly counts appointments by status

### 6. Concurrency Tests (TestAppointmentConcurrency)
✅ Concurrent booking attempts for same slot handled correctly

### 7. Integration Tests (TestAppointmentIntegrations)
✅ Appointment creation triggers calendar sync
✅ Appointment succeeds even if calendar sync fails (non-blocking)

### 8. Token Generation Tests (TestAppointmentTokenGeneration)
✅ Token number auto-generated on check-in
✅ Token numbers increment per doctor per day
✅ Custom token number can be provided on check-in

## Key Features Tested

### Double Booking Prevention
- ✅ Same slot, same doctor detection
- ✅ Overlapping time detection
- ✅ Conflict returns 409 status

### Status Workflow
- ✅ scheduled → checked_in → in_progress → completed
- ✅ Invalid transitions blocked with 400 errors
- ✅ Cancelled and completed states are terminal

### Data Validation
- ✅ Required fields enforced
- ✅ UUID format validation
- ✅ DateTime format validation
- ✅ Duration constraints (5-120 minutes)
- ✅ Text length limits (chief_complaint: 500 chars)
- ✅ Enum validation (appointment_type, booking_source)

### Business Rules
- ✅ Patient and doctor must be in same clinic
- ✅ Walk-ins can be backdated (flexibility)
- ✅ Token numbers auto-increment per day/doctor
- ✅ Calendar sync is non-blocking

### Error Handling
- ✅ 404 for non-existent resources
- ✅ 400 for business rule violations
- ✅ 409 for conflicts
- ✅ 422 for validation errors

## Test Framework
- **Framework:** pytest
- **Async Support:** pytest-asyncio
- **HTTP Testing:** FastAPI TestClient
- **Database:** SQLite in-memory (via conftest.py)
- **Fixtures:** Clinic, User, Doctor, Patient, Appointment, Auth headers

## Running the Tests

```bash
# Run all appointment booking tests
pytest tests/critical/test_appointment_booking.py -v

# Run specific test class
pytest tests/critical/test_appointment_booking.py::TestAppointmentBookingHappyPath -v

# Run with coverage
pytest tests/critical/test_appointment_booking.py --cov=app.api.v1.appointments --cov-report=html

# Run specific test
pytest tests/critical/test_appointment_booking.py::TestAppointmentBookingEdgeCases::test_prevent_double_booking_same_slot -v
```

## Dependencies
- pytest
- pytest-asyncio
- httpx
- fastapi
- sqlalchemy
- pydantic

## Notes
- All tests use the fixtures from `tests/conftest.py`
- Tests are independent and can run in isolation
- External dependencies (CalendarSyncService) are mocked
- Database is reset between tests
- All datetime operations use timezone-aware timestamps
