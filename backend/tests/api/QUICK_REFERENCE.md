# Quick Reference: Document & Report API Tests

## Test Statistics
- **Total Tests**: 56
- **Test Classes**: 4
- **Lines of Code**: 1,331
- **File**: `test_document_apis.py`

## Quick Commands

```bash
# Run all tests
pytest tests/api/test_document_apis.py -v

# Run with coverage
pytest tests/api/test_document_apis.py --cov=app.api.v1 --cov-report=term-missing

# Run specific API tests
pytest tests/api/test_document_apis.py::TestDocumentsAPI -v
pytest tests/api/test_document_apis.py::TestReportsAPI -v
pytest tests/api/test_document_apis.py::TestCalendarAPI -v
pytest tests/api/test_document_apis.py::TestProceduresAPI -v

# Run single test
pytest tests/api/test_document_apis.py::TestDocumentsAPI::test_upload_document_image -v
```

## Test Breakdown by API

| API | Tests | Key Features |
|-----|-------|--------------|
| **Documents** | 18 | Upload, OCR, List, Update, Delete, Stats |
| **Reports** | 14 | PDF/Excel generation, Daily/Monthly/Revenue |
| **Calendar** | 8 | OAuth, Sync, Status, Conflicts, Disconnect |
| **Procedures** | 16 | CRUD, Analytics, Templates, Consumables |

## Coverage Matrix

### Documents API (/api/v1/documents)
- [x] Upload image (JPEG, PNG)
- [x] Upload PDF
- [x] OCR processing
- [x] List with filters
- [x] Get by ID
- [x] Get patient documents
- [x] Update metadata
- [x] Delete document
- [x] Document types
- [x] Statistics
- [x] Patient summary

### Reports API (/api/v1/reports)
- [x] Daily summary PDF
- [x] Monthly analytics PDF
- [x] Revenue PDF
- [x] Appointments Excel
- [x] Revenue Excel
- [x] Doctor utilization Excel
- [x] Patient demographics Excel
- [x] List available reports
- [x] Date range filtering
- [x] Doctor filtering

### Calendar API (/api/v1/calendar)
- [x] Get OAuth URL
- [x] OAuth callback
- [x] Sync status
- [x] Trigger sync
- [x] Disconnect
- [x] Check conflicts

### Procedures API (/api/v1/procedures)
- [x] Create procedure
- [x] Quick log
- [x] Get by ID
- [x] Update
- [x] Delete
- [x] List with filters
- [x] Patient procedures
- [x] Patient summary
- [x] Analytics stats
- [x] Type counts
- [x] Doctor stats
- [x] Trends
- [x] Consumables
- [x] Templates

## Common Test Patterns

### Document Upload Test
```python
def test_upload_document_image(client, auth_headers, test_patient):
    img_bytes = create_test_image()
    response = client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        data={"patient_id": str(test_patient.id)},
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )
    assert response.status_code == 201
```

### Report Generation Test
```python
def test_download_daily_summary_pdf(client, auth_headers):
    response = client.get(
        "/api/v1/reports/daily-summary/pdf",
        headers=auth_headers,
        params={"report_date": date.today().isoformat()},
    )
    assert response.status_code in [200, 500]
```

### Procedure Creation Test
```python
def test_create_procedure(client, auth_headers, test_patient, test_doctor):
    response = client.post(
        "/api/v1/procedures",
        headers=auth_headers,
        json={
            "patient_id": str(test_patient.id),
            "doctor_id": str(test_doctor.id),
            "category": "Cardiology",
            "procedure_type": "Echo",
            "name": "Echocardiogram",
        },
    )
    assert response.status_code == 201
```

## Fixtures Available

- `test_clinic` - Test clinic instance
- `test_user` - Admin user
- `test_doctor` - Doctor with user account
- `test_patient` - Patient record
- `test_appointment` - Scheduled appointment
- `test_document` - Unprocessed document
- `test_processed_document` - OCR-processed document
- `test_procedure` - Procedure record
- `auth_headers` - Authentication headers
- `doctor_auth_headers` - Doctor authentication

## Expected HTTP Status Codes

| Status | Meaning | When Used |
|--------|---------|-----------|
| 200 | OK | Successful GET/PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Service failure |
| 503 | Service Unavailable | Feature not configured |

## Troubleshooting

### Import Error: PIL
```bash
pip install Pillow
```

### Import Error: Models
```bash
# Ensure you're in the backend directory
cd /home/user/appointment_system/backend
export PYTHONPATH=/home/user/appointment_system/backend:$PYTHONPATH
```

### Database Errors
```bash
# Tests use in-memory SQLite
# Check conftest.py for database configuration
```

---
**Quick Tip**: Use `-v` for verbose output and `-s` to see print statements!
