# Insurance & Billing System - Phase 14

## Overview

Phase 14 implements a comprehensive insurance and billing system for DocAssist Practice Manager, designed specifically for the Indian healthcare market with full GST compliance.

## Key Features

### 1. Insurance Company Management
- Master database of 20+ major Indian insurance companies and TPAs
- Company details including contact information, TPA details, and claim submission URLs
- Pre-authorization threshold configuration
- Cashless facility tracking

### 2. Patient Insurance Policies
- Multiple insurance policies per patient
- Primary/secondary insurance support
- Policy validity tracking
- Coverage types: Individual, Family Floater, Group, Senior Citizen, Critical Illness, Maternity
- Copay percentage and deductible configuration

### 3. Insurance Claims Management
- Complete claim lifecycle: Draft → Submitted → Under Review → Approved/Rejected → Settled
- Auto-generated internal claim numbers
- TPA claim number tracking
- Document attachment support
- Appeal workflow for rejected claims
- Patient liability calculation
- Claim status tracking with timestamps

### 4. Pre-Authorization Workflow
- Pre-authorization requests for planned procedures
- Threshold-based pre-auth requirements
- Auto-generated pre-auth reference numbers
- Validity period tracking
- Link pre-auth to claims

### 5. GST Compliance
- Automatic CGST+SGST calculation for intra-state transactions
- Automatic IGST calculation for inter-state transactions
- HSN/SAC code support for healthcare services
- GSTIN validation
- GST-exempt service handling
- Tax calculation with custom rates

### 6. Billing Service
- Patient vs insurance portion calculation
- Copay and deductible handling
- Partial insurance approval support
- Invoice totals with GST breakdown
- GST-compliant invoice data formatting

---

## API Endpoints

### Insurance Companies

#### Create Insurance Company
```http
POST /api/v1/insurance/companies
Authorization: Bearer <admin_token>

{
  "name": "Star Health Insurance",
  "code": "STAR",
  "contact_email": "claims@starhealth.in",
  "tpa_name": "Star Health",
  "cashless_available": true,
  "preauth_required": true,
  "preauth_threshold": 50000.00
}
```

#### List Insurance Companies
```http
GET /api/v1/insurance/companies?active_only=true
Authorization: Bearer <token>
```

#### Get Insurance Company
```http
GET /api/v1/insurance/companies/{company_id}
Authorization: Bearer <token>
```

### Patient Insurance

#### Add Patient Insurance
```http
POST /api/v1/insurance/patient-insurance
Authorization: Bearer <token>

{
  "patient_id": "uuid",
  "insurance_company_id": "uuid",
  "policy_number": "POL123456789",
  "valid_from": "2026-01-01",
  "valid_to": "2027-12-31",
  "coverage_type": "individual",
  "sum_insured": 500000.00,
  "copay_percentage": 10.00,
  "deductible_amount": 5000.00,
  "is_primary": true
}
```

#### List Patient Insurance
```http
GET /api/v1/insurance/patient-insurance?patient_id={uuid}&active_only=true
Authorization: Bearer <token>
```

### Insurance Claims

#### Create Claim
```http
POST /api/v1/insurance/claims
Authorization: Bearer <token>

{
  "patient_id": "uuid",
  "invoice_id": "uuid",
  "patient_insurance_id": "uuid",
  "claimed_amount": 10000.00,
  "preauthorization_id": "uuid",  // optional
  "notes": "Regular checkup claim",
  "documents_submitted": ["path/to/doc1.pdf", "path/to/doc2.pdf"]
}
```

#### Submit Claim to Insurance
```http
POST /api/v1/insurance/claims/{claim_id}/submit
Authorization: Bearer <token>

{
  "documents_submitted": ["path/to/additional.pdf"],
  "submitted_by": "Dr. John Doe"
}
```

#### Update Claim Status
```http
PATCH /api/v1/insurance/claims/{claim_id}
Authorization: Bearer <token>

{
  "status": "approved",
  "claim_number": "INS-2026-12345",
  "approved_amount": 9000.00,
  "tpa_reference_number": "TPA-REF-001",
  "processing_notes": "Claim approved with standard deductible"
}
```

#### List Claims
```http
GET /api/v1/insurance/claims?patient_id={uuid}&status_filter=submitted
Authorization: Bearer <token>
```

#### Get Claims Summary
```http
GET /api/v1/insurance/claims/summary?insurance_company_id={uuid}&date_from=2026-01-01
Authorization: Bearer <token>
```

### Pre-Authorization

#### Create Pre-Authorization Request
```http
POST /api/v1/insurance/preauthorizations
Authorization: Bearer <token>

{
  "patient_id": "uuid",
  "patient_insurance_id": "uuid",
  "procedure_name": "Angioplasty",
  "procedure_code": "CPT-92920",
  "diagnosis": "Coronary artery disease",
  "requested_amount": 150000.00,
  "requested_date": "2026-01-04",
  "planned_procedure_date": "2026-01-15",
  "notes": "Emergency procedure required",
  "requested_by": "Dr. Cardiologist"
}
```

#### Submit Pre-Authorization
```http
POST /api/v1/insurance/preauthorizations/{preauth_id}/submit
Authorization: Bearer <token>

{
  "documents_submitted": ["path/to/medical_report.pdf"]
}
```

#### Update Pre-Authorization Status
```http
PATCH /api/v1/insurance/preauthorizations/{preauth_id}
Authorization: Bearer <token>

{
  "status": "approved",
  "auth_number": "AUTH-STAR-12345",
  "approved_amount": 140000.00,
  "valid_from": "2026-01-10",
  "valid_to": "2026-02-10",
  "tpa_notes": "Approved with conditions"
}
```

#### Check Pre-Auth Validity
```http
GET /api/v1/insurance/preauthorizations/{preauth_id}/validity
Authorization: Bearer <token>
```

---

## Billing Service Usage

### GST Calculation

```python
from app.services.billing import BillingService
from decimal import Decimal

# Intra-state transaction (CGST + SGST)
gst = BillingService.calculate_gst(
    amount=Decimal("10000.00"),
    clinic_state="MH",        # Maharashtra
    patient_state="MH",       # Maharashtra
    is_exempt=False,
)
# Result: {"cgst": 900.00, "sgst": 900.00, "igst": 0.00, "total_tax": 1800.00}

# Inter-state transaction (IGST)
gst = BillingService.calculate_gst(
    amount=Decimal("10000.00"),
    clinic_state="MH",        # Maharashtra
    patient_state="KA",       # Karnataka
    is_exempt=False,
)
# Result: {"cgst": 0.00, "sgst": 0.00, "igst": 1800.00, "total_tax": 1800.00}
```

### Insurance Split Calculation

```python
from app.services.billing import BillingService
from decimal import Decimal

# Calculate patient vs insurance portion
split = BillingService.calculate_insurance_split(
    total_amount=Decimal("10000.00"),
    copay_percentage=Decimal("10.00"),    # 10% copay
    deductible=Decimal("2000.00"),        # Rs 2000 deductible
    approved_amount=Decimal("7000.00"),   # Insurance approved 7k
)

# Result:
# {
#   "patient_portion": 3800.00,
#   "insurance_portion": 7000.00,
#   "patient_deductible": 2000.00,
#   "patient_copay": 800.00,
#   "patient_additional": 1000.00
# }
```

---

## Database Schema

### Insurance Companies
- `id`: UUID primary key
- `name`: Company name (unique)
- `code`: Short code (unique)
- `contact_email`, `contact_phone`, `contact_address`
- `tpa_name`, `tpa_email`, `tpa_phone`
- `claim_submission_url`, `claim_submission_email`
- `cashless_available`: Boolean
- `preauth_required`: Boolean
- `preauth_threshold`: Decimal
- `network_type`: String
- `is_active`: Boolean

### Patient Insurances
- `id`: UUID primary key
- `patient_id`: FK to patients
- `insurance_company_id`: FK to insurance_companies
- `policy_number`: String (indexed)
- `group_number`, `member_id`: String
- `valid_from`, `valid_to`: Date
- `coverage_type`: Enum
- `sum_insured`: Decimal
- `copay_percentage`: Decimal
- `deductible_amount`: Decimal
- `is_primary`: Boolean
- `priority_order`: Integer

### Insurance Claims
- `id`: UUID primary key
- `patient_id`: FK to patients
- `invoice_id`: FK to invoices
- `patient_insurance_id`: FK to patient_insurances
- `insurance_company_id`: FK to insurance_companies
- `preauthorization_id`: FK to preauthorizations (nullable)
- `claim_number`: String (from TPA)
- `internal_claim_number`: String (unique, auto-generated)
- `claimed_amount`, `approved_amount`, `settled_amount`: Decimal
- `patient_liability`: Decimal
- `status`: Enum (draft, submitted, under_review, approved, rejected, settled, appealed)
- `submitted_at`, `acknowledged_at`, `approved_at`, `settled_at`: DateTime
- `documents_submitted`: JSONB
- `rejection_reason`, `appeal_notes`: Text

### Pre-Authorizations
- `id`: UUID primary key
- `patient_id`: FK to patients
- `patient_insurance_id`: FK to patient_insurances
- `insurance_company_id`: FK to insurance_companies
- `procedure_id`: FK to procedures (nullable)
- `auth_number`: String (from TPA)
- `internal_ref_number`: String (unique, auto-generated)
- `procedure_name`, `procedure_code`, `diagnosis`: String
- `requested_amount`, `approved_amount`: Decimal
- `status`: Enum (pending, requested, approved, rejected, expired, cancelled)
- `requested_date`, `planned_procedure_date`: Date
- `valid_from`, `valid_to`: Date
- `documents_submitted`: JSONB

---

## Seed Data

Load 20 Indian insurance companies:

```bash
cd backend
python -m app.scripts.seed_insurance_companies
```

Includes:
- **Major Insurers**: Star Health, HDFC Ergo, ICICI Lombard, Care Health, Bajaj Allianz, Max Bupa, Aditya Birla, Niva Bupa
- **PSU Insurers**: New India, United India, Oriental
- **Others**: Cholamandalam, Manipal Cigna, SBI General
- **Major TPAs**: Medi Assist, MD India, Paramount TPA, Good Health, Heritage

---

## GST Rules for Healthcare

### GST Rates
- **Standard Healthcare Services**: 18% (9% CGST + 9% SGST for intra-state, or 18% IGST for inter-state)
- **Most healthcare services are EXEMPT** under Section 12 of CGST Act

### Exempt Services
- Healthcare services by clinical establishments
- Diagnostic tests prescribed by doctors
- Hospital room charges below Rs 5,000/day
- Ambulance services for patient transportation

### HSN/SAC Codes
- **9993**: Healthcare services (consultation, diagnostic, surgery, hospital services, lab tests, imaging)
- **9994**: Ambulance services

### GSTIN Format
- Format: `27AABCT1234F1Z5`
- 2 digits (state code) + 10 alphanumeric (PAN) + 1 alphanumeric + Z + 1 alphanumeric

---

## Testing

Run tests:

```bash
cd backend
pytest tests/test_billing_service.py -v
pytest tests/test_insurance_claims_service.py -v
```

Test coverage includes:
- GST calculation (intra-state, inter-state, exempt)
- Invoice totals with discounts
- Insurance split calculations
- Claim lifecycle (create, submit, approve, reject, appeal)
- Pre-authorization workflow
- GSTIN validation
- HSN code retrieval

---

## Migration

Apply database migration:

```bash
cd backend
alembic upgrade head
```

This creates:
- `insurance_companies` table
- `patient_insurances` table
- `insurance_claims` table
- `preauthorizations` table

---

## Mobile Integration (Future)

Mobile UI components needed:
- Insurance selection during billing
- Pre-auth request form
- Claims tracking screen
- Payment collection with insurance split
- Real-time claim status updates

---

## Next Steps

1. **Invoice PDF Generation**: Add GST-compliant invoice PDF with insurance breakdown
2. **TPA Integration**: Integrate with major TPA APIs for real-time claim submission
3. **Mobile UI**: Build Flutter screens for insurance and billing
4. **Reports**: Add insurance analytics and claim reports
5. **Automated Reminders**: Send reminders for pending claims and pre-auths

---

## Support

For issues or questions:
- Backend: `/backend/app/services/billing.py`, `/backend/app/services/insurance_claims.py`
- API: `/backend/app/api/v1/insurance.py`
- Models: `/backend/app/models/insurance.py`
- Tests: `/backend/tests/test_billing_service.py`, `/backend/tests/test_insurance_claims_service.py`

---

*Last Updated: 2026-01-04*
*Phase 14: Insurance & Billing - Complete*
