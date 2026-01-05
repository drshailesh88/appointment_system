# Document and Report API Integration Tests

## Overview

Comprehensive integration test suite for DocAssist Practice Manager's document management, reporting, calendar integration, and procedure tracking APIs.

**File:** `test_document_apis.py`
**Total Tests:** 56 test methods across 4 test classes
**Lines of Code:** 1,331

## Test Coverage

### 1. Documents API (18 tests)

Tests the complete document management lifecycle including upload, OCR processing, retrieval, and deletion.

**Endpoints Tested:**
- `POST /api/v1/documents/upload` - Upload image/PDF documents
- `POST /api/v1/documents/{id}/ocr` - Trigger OCR processing
- `GET /api/v1/documents` - List documents with pagination/filters
- `GET /api/v1/documents/patient/{id}` - Get patient documents
- `GET /api/v1/documents/{id}` - Get specific document
- `GET /api/v1/documents/{id}/text` - Get extracted OCR text
- `PATCH /api/v1/documents/{id}` - Update document metadata
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/documents/types/available` - List document types
- `GET /api/v1/documents/stats/summary` - Document statistics
- `GET /api/v1/documents/patient/{id}/summary` - Patient summary

**Key Test Scenarios:**
- ✅ Image upload (JPEG, PNG)
- ✅ PDF upload
- ✅ Invalid file type rejection
- ✅ Invalid patient ID validation
- ✅ OCR processing with mocked service
- ✅ Document listing with filters (patient, type, status)
- ✅ Pagination support
- ✅ Document metadata updates
- ✅ Soft deletion verification
- ✅ Statistics aggregation
- ✅ Patient document summary

### 2. Reports API (14 tests)

Tests PDF and Excel report generation across various report types.

**Endpoints Tested:**
- `GET /api/v1/reports/daily-summary/pdf` - Daily summary PDF
- `GET /api/v1/reports/monthly/pdf` - Monthly analytics PDF
- `GET /api/v1/reports/revenue/pdf` - Revenue report PDF
- `GET /api/v1/reports/appointments/excel` - Appointments Excel
- `GET /api/v1/reports/revenue/excel` - Revenue Excel
- `GET /api/v1/reports/doctors/utilization/excel` - Doctor utilization Excel
- `GET /api/v1/reports/patients/demographics/excel` - Demographics Excel
- `GET /api/v1/reports/available` - List available reports

**Key Test Scenarios:**
- ✅ PDF generation with correct MIME types
- ✅ Excel export with correct format
- ✅ Default date handling (today)
- ✅ Custom date range filtering
- ✅ Doctor-specific filtering
- ✅ Period-based filtering (week, month, quarter, year)
- ✅ Month validation (1-12)
- ✅ Report metadata listing
- ✅ Content-Disposition headers
- ✅ Empty report handling

### 3. Calendar API (8 tests)

Tests Google Calendar integration including OAuth flow and synchronization.

**Endpoints Tested:**
- `GET /api/v1/calendar/auth-url` - Get OAuth authorization URL
- `POST /api/v1/calendar/callback` - OAuth callback handler
- `POST /api/v1/calendar/sync` - Trigger manual sync
- `GET /api/v1/calendar/status` - Get sync status
- `DELETE /api/v1/calendar/disconnect` - Disconnect calendar
- `POST /api/v1/calendar/conflicts` - Check for conflicts

**Key Test Scenarios:**
- ✅ OAuth URL generation with state token
- ✅ Configuration validation
- ✅ Invalid doctor handling
- ✅ Sync status (connected/disconnected)
- ✅ Manual sync triggering
- ✅ Calendar disconnection
- ✅ Conflict detection
- ✅ Error handling for unconfigured services

### 4. Procedures API (16 tests)

Tests procedure tracking for all medical specialties.

**Endpoints Tested:**
- `POST /api/v1/procedures` - Create procedure record
- `POST /api/v1/procedures/quick` - Quick log procedure
- `GET /api/v1/procedures/{id}` - Get procedure by ID
- `PUT /api/v1/procedures/{id}` - Update procedure
- `DELETE /api/v1/procedures/{id}` - Delete procedure
- `GET /api/v1/procedures` - List procedures with filters
- `GET /api/v1/procedures/patient/{id}` - Patient procedures
- `GET /api/v1/procedures/patient/{id}/summary` - Patient summary
- `GET /api/v1/procedures/analytics/stats` - Overall statistics
- `GET /api/v1/procedures/analytics/types` - Type counts
- `GET /api/v1/procedures/analytics/doctors` - Doctor statistics
- `GET /api/v1/procedures/analytics/trend` - Daily trends
- `GET /api/v1/procedures/analytics/consumables` - Consumables usage
- `GET /api/v1/procedures/templates` - Procedure templates
- `GET /api/v1/procedures/templates/{category}` - Category templates

**Key Test Scenarios:**
- ✅ Full procedure creation (all fields)
- ✅ Quick logging (minimal fields)
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Multi-filter support (patient, doctor, category, type, outcome, date)
- ✅ Patient procedure history
- ✅ Analytics aggregation
- ✅ Type-based statistics
- ✅ Doctor-wise performance metrics
- ✅ Daily trend analysis
- ✅ Consumables tracking
- ✅ Template retrieval (Cardiology, Orthopedics, etc.)
- ✅ Invalid category handling

## Test Fixtures

### Helper Functions

```python
create_test_image() -> io.BytesIO
```
Generates a test JPEG image (100x100 red square) for upload testing.

```python
create_test_pdf() -> io.BytesIO
```
Creates a minimal valid PDF file for document upload testing.

### Database Fixtures

**test_document**
- Unprocessed document linked to test patient
- Type: lab_report
- Size: 1KB

**test_processed_document**
- OCR-processed document with extracted text
- Type: prescription
- Includes structured data extraction
- OCR confidence: 0.95

**test_procedure**
- Cardiology echo procedure
- Linked to test patient and doctor
- Outcome: success
- Billable: ₹2,500

## Running the Tests

### Run All Tests
```bash
pytest backend/tests/api/test_document_apis.py -v
```

### Run Specific Test Class
```bash
# Documents API only
pytest backend/tests/api/test_document_apis.py::TestDocumentsAPI -v

# Reports API only
pytest backend/tests/api/test_document_apis.py::TestReportsAPI -v

# Calendar API only
pytest backend/tests/api/test_document_apis.py::TestCalendarAPI -v

# Procedures API only
pytest backend/tests/api/test_document_apis.py::TestProceduresAPI -v
```

### Run Specific Test
```bash
pytest backend/tests/api/test_document_apis.py::TestDocumentsAPI::test_upload_document_image -v
```

### With Coverage Report
```bash
pytest backend/tests/api/test_document_apis.py \
  --cov=app.api.v1.documents \
  --cov=app.api.v1.reports \
  --cov=app.api.v1.calendar \
  --cov=app.api.v1.procedures \
  --cov-report=html
```

### Run with Output
```bash
pytest backend/tests/api/test_document_apis.py -v -s
```

## Dependencies

All dependencies are already included in `requirements.txt`:

- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **httpx** - HTTP client for FastAPI testing
- **Pillow** (PIL) - Image generation for test files
- **sqlalchemy** - Database ORM
- **fastapi** - Web framework

## Edge Cases Covered

### Validation
- ✅ Invalid patient IDs (404)
- ✅ Invalid doctor IDs (404)
- ✅ Invalid file types (400)
- ✅ Invalid date ranges (400)
- ✅ Month out of range (400)
- ✅ Missing configuration (503)

### Data Handling
- ✅ Empty result sets
- ✅ Pagination edge cases
- ✅ Filter combinations
- ✅ Default parameter values
- ✅ Optional fields (null handling)

### File Operations
- ✅ File size validation
- ✅ File type validation
- ✅ File deletion verification
- ✅ Temporary file handling

### Business Logic
- ✅ Date range calculations (today, week, month, quarter, year)
- ✅ Statistics aggregation
- ✅ Multi-level filtering
- ✅ Resource ownership validation (clinic_id checks)

## Test Architecture

### Class Organization
```
test_document_apis.py
├── Helper Functions
│   ├── create_test_image()
│   └── create_test_pdf()
├── Fixtures
│   ├── test_document
│   ├── test_processed_document
│   └── test_procedure
└── Test Classes
    ├── TestDocumentsAPI (18 tests)
    ├── TestReportsAPI (14 tests)
    ├── TestCalendarAPI (8 tests)
    └── TestProceduresAPI (16 tests)
```

### Test Pattern
Each test follows this pattern:
1. **Arrange** - Set up test data using fixtures
2. **Act** - Call the API endpoint
3. **Assert** - Verify response status, data structure, and business logic

### Mocking Strategy
- OCR service is mocked to avoid external dependencies
- Google Calendar integration is mocked for OAuth tests
- File system operations use temporary files
- Database uses in-memory SQLite for isolation

## Integration Points

### Documents API → EMR Integration
- Documents can be synced to EMR system
- `synced_to_emr` flag tracks sync status
- `emr_document_id` links to EMR records

### Calendar API → Google Calendar
- OAuth 2.0 flow for authentication
- Bidirectional sync support
- Conflict detection
- Refresh token encryption

### Procedures API → Specialty Templates
- Pre-configured templates for:
  - Cardiology (Echo, Angioplasty, Stent)
  - Orthopedics (Surgery, Joint replacement)
  - Ophthalmology (Cataract, LASIK)
  - And more...

## Best Practices Demonstrated

1. **Comprehensive Coverage** - All CRUD operations tested
2. **Edge Case Handling** - Invalid inputs, missing data, errors
3. **Fixture Reuse** - Shared fixtures from conftest.py
4. **Clear Naming** - Descriptive test method names
5. **Isolation** - Each test is independent
6. **Documentation** - Docstrings explain test purpose
7. **Assertions** - Multiple assertions per test for thorough validation
8. **Status Codes** - Proper HTTP status code validation

## Maintenance Notes

### Adding New Tests
1. Create test method with `test_` prefix
2. Use existing fixtures or create new ones
3. Follow the Arrange-Act-Assert pattern
4. Add assertions for status code and response data
5. Update this README with new test details

### Updating Fixtures
- Fixtures are in `conftest.py` (shared) or local to this file
- Update fixture data when API schemas change
- Ensure backward compatibility when possible

### Troubleshooting
- **Import errors**: Ensure all dependencies installed via `pip install -r requirements.txt`
- **Database errors**: Check that test database is properly configured
- **File errors**: Verify temp directory permissions
- **OCR errors**: Check that mocking is properly configured

## Related Files

- **API Endpoints**: `backend/app/api/v1/documents.py`
- **API Endpoints**: `backend/app/api/v1/reports.py`
- **API Endpoints**: `backend/app/api/v1/calendar.py`
- **API Endpoints**: `backend/app/api/v1/procedures.py`
- **Models**: `backend/app/models/document.py`
- **Models**: `backend/app/models/procedure.py`
- **Schemas**: `backend/app/schemas/document.py`
- **Schemas**: `backend/app/schemas/procedure.py`
- **Fixtures**: `backend/tests/conftest.py`

## Future Enhancements

- [ ] Add performance benchmarks
- [ ] Test file size limits (large file uploads)
- [ ] Multi-page PDF processing tests
- [ ] Calendar recurring event tests
- [ ] Procedure batch operations
- [ ] Report generation stress tests
- [ ] Concurrent upload handling
- [ ] Rate limiting tests

---

**Last Updated:** 2026-01-05
**Version:** 1.0
**Author:** Claude Code
**Project:** DocAssist Practice Manager
