# Financial Services Tests - Quick Start Guide

## 🚀 Quick Commands

```bash
# Run all financial tests
pytest backend/tests/services/test_financial_services.py -v

# Run only billing tests
pytest backend/tests/services/test_financial_services.py::TestGSTCalculation -v

# Run only insurance tests
pytest backend/tests/services/test_financial_services.py::TestInsuranceClaimsService -v

# Run with coverage report
pytest backend/tests/services/test_financial_services.py --cov=app.services --cov-report=term-missing

# Run specific test
pytest backend/tests/services/test_financial_services.py::TestGSTCalculation::test_intra_state_gst -v
```

---

## 📋 Test Examples by Use Case

### Use Case 1: Testing GST Calculation for Mumbai Clinic

**Test:** `test_intra_state_gst`

```python
# Clinic in Maharashtra, Patient in Maharashtra
# Expected: 9% CGST + 9% SGST = 18% total

result = BillingService.calculate_gst(
    amount=Decimal("10000.00"),  # Rs 10,000
    clinic_state="MH",           # Maharashtra
    patient_state="MH",          # Maharashtra
    is_exempt=False,
)

# Assertions:
# CGST: Rs 900 (9%)
# SGST: Rs 900 (9%)
# IGST: Rs 0
# Total: Rs 1,800
```

**When to use:** Validating intra-state GST for same-state transactions.

---

### Use Case 2: Testing Cross-State Treatment

**Test:** `test_inter_state_gst`

```python
# Clinic in Maharashtra, Patient from Karnataka
# Expected: 18% IGST (no CGST/SGST)

result = BillingService.calculate_gst(
    amount=Decimal("10000.00"),
    clinic_state="MH",    # Maharashtra
    patient_state="KA",   # Karnataka
    is_exempt=False,
)

# Assertions:
# CGST: Rs 0
# SGST: Rs 0
# IGST: Rs 1,800 (18%)
```

**When to use:** Validating inter-state GST for cross-state patients.

---

### Use Case 3: Testing Large Hospital Bills (Crore Range)

**Test:** `test_large_amount_crore_range`

```python
# Testing Rs 1 Crore surgery bill
result = BillingService.calculate_gst(
    amount=Decimal("10000000.00"),  # 1 crore
    clinic_state="MH",
    patient_state="MH",
)

# Expected:
# CGST: Rs 9,00,000
# SGST: Rs 9,00,000
# Total Tax: Rs 18,00,000
```

**When to use:** Ensuring calculations work correctly for high-value procedures.

---

### Use Case 4: Testing Insurance Claim Workflow

**Test:** `test_create_claim_success`

```python
# Complete workflow: Create → Submit → Approve
service = InsuranceClaimsService(db_session)

# Step 1: Create claim
claim = await service.create_claim(
    patient_id=patient.id,
    invoice_id=invoice.id,
    patient_insurance_id=insurance.id,
    claimed_amount=Decimal("10000.00"),
)

# Step 2: Submit to TPA
await service.submit_claim(
    claim_id=claim.id,
    submitted_by="Dr. Smith",
)

# Step 3: TPA approves
await service.update_claim_status(
    claim_id=claim.id,
    status=ClaimStatus.APPROVED,
    approved_amount=Decimal("9000.00"),
)

# Result: Patient liability = Rs 1,000
```

**When to use:** Testing end-to-end claim submission and approval.

---

### Use Case 5: Testing Pre-Authorization for Surgery

**Test:** `test_create_preauthorization`

```python
# Pre-auth for Rs 1 lakh angioplasty
service = InsuranceClaimsService(db_session)

preauth = await service.create_preauthorization(
    patient_id=patient.id,
    patient_insurance_id=insurance.id,
    procedure_name="Angioplasty",
    requested_amount=Decimal("100000.00"),
    requested_date=date.today(),
    diagnosis="Coronary artery disease",
)

# Expected:
# Status: PENDING
# Internal number: PA-YYYYMMDD-COMPANY-0001
```

**When to use:** Testing pre-authorization workflow for expensive procedures.

---

### Use Case 6: Testing Patient Copay Calculation

**Test:** `test_with_copay_and_deductible`

```python
# Bill: Rs 10,000
# Deductible: Rs 1,000
# Copay: 10%

result = BillingService.calculate_insurance_split(
    total_amount=Decimal("10000.00"),
    copay_percentage=Decimal("10.00"),
    deductible=Decimal("1000.00"),
)

# Expected breakdown:
# Patient deductible: Rs 1,000
# Remaining: Rs 9,000
# Patient copay (10% of 9k): Rs 900
# Insurance pays: Rs 8,100
# Patient total: Rs 1,900
```

**When to use:** Calculating patient vs insurance portions.

---

### Use Case 7: Testing Multiple Insurance Policies

**Test:** `test_multiple_insurance_policies_same_patient`

```python
# Patient has:
# - Primary: Star Health (Rs 3 lakh cover)
# - Secondary: HDFC Ergo (Rs 2 lakh cover)

# Create both policies with priority
primary = PatientInsurance(
    policy_number="PRIMARY-001",
    is_primary=True,
    priority_order=1,
    sum_insured=Decimal("300000.00"),
)

secondary = PatientInsurance(
    policy_number="SECONDARY-001",
    is_primary=False,
    priority_order=2,
    sum_insured=Decimal("200000.00"),
)

# Verify priority ordering
policies = await db.query(PatientInsurance).filter_by(
    patient_id=patient.id
).order_by(PatientInsurance.priority_order).all()

assert policies[0].is_primary == True
```

**When to use:** Testing patients with multiple active insurance policies.

---

### Use Case 8: Testing Decimal Precision (Paisa)

**Test:** `test_decimal_precision_paisa`

```python
# Amount: Rs 1,234.56
# Tax: 18%
# Expected precision: Down to paisa (0.01)

result = BillingService.calculate_gst(
    amount=Decimal("1234.56"),
    clinic_state="MH",
    patient_state="MH",
)

# 9% CGST = Rs 111.1104 → rounds to Rs 111.11
# 9% SGST = Rs 111.1104 → rounds to Rs 111.11
# Total = Rs 222.22
```

**When to use:** Ensuring no rounding errors in financial calculations.

---

## 🔍 Common Test Patterns

### Pattern 1: Arrange-Act-Assert (AAA)

```python
async def test_example(async_session, test_patient):
    # ARRANGE - Set up test data
    service = InsuranceClaimsService(async_session)

    # ACT - Perform the action
    claim = await service.create_claim(
        patient_id=test_patient.id,
        # ... other params
    )

    # ASSERT - Verify results
    assert claim.status == ClaimStatus.DRAFT.value
    assert claim.claimed_amount == Decimal("10000.00")
```

### Pattern 2: Error Testing

```python
async def test_invalid_input(async_session):
    service = InsuranceClaimsService(async_session)

    with pytest.raises(ValueError, match="not found"):
        await service.create_claim(
            patient_id=uuid4(),  # Non-existent ID
            # ...
        )
```

### Pattern 3: Fixture Reuse

```python
@pytest_asyncio.fixture
async def test_claim(async_session, test_patient, test_invoice):
    """Reusable claim fixture."""
    service = InsuranceClaimsService(async_session)
    return await service.create_claim(
        patient_id=test_patient.id,
        invoice_id=test_invoice.id,
        # ...
    )

async def test_submit_claim(test_claim):
    # Use the fixture directly
    assert test_claim.status == ClaimStatus.DRAFT.value
```

---

## 🐛 Debugging Failed Tests

### Issue: Test fails with "Patient insurance not found"

```python
# Problem: Insurance fixture not created or committed
# Solution: Ensure fixture uses await commit()

@pytest_asyncio.fixture
async def test_patient_insurance(async_session, test_patient):
    insurance = PatientInsurance(...)
    async_session.add(insurance)
    await async_session.commit()  # ← Important!
    await async_session.refresh(insurance)
    return insurance
```

### Issue: Decimal precision mismatch

```python
# Problem: Comparing Decimal with float
# ❌ Wrong:
assert result["total"] == 1800.00

# ✅ Correct:
assert result["total"] == Decimal("1800.00")
```

### Issue: Async test not running

```python
# Problem: Missing @pytest.mark.asyncio decorator
# ❌ Wrong:
class TestClaims:
    async def test_create_claim(self):  # Won't run!
        ...

# ✅ Correct:
@pytest.mark.asyncio
class TestClaims:
    async def test_create_claim(self):
        ...
```

---

## 📊 Test Data Reference

### Valid GSTIN Examples
```python
"27AABCT1234F1Z5"  # Maharashtra
"29AABCT1234F1Z5"  # Karnataka
"07AABCT1234F1Z5"  # Delhi
```

### State Codes
```python
"MH" - Maharashtra
"KA" - Karnataka
"TN" - Tamil Nadu
"DL" - Delhi
"GJ" - Gujarat
```

### Amount Ranges for Testing
```python
Decimal("0.00")           # Zero amount
Decimal("100.50")         # Small amount
Decimal("10000.00")       # Standard (Rs 10k)
Decimal("500000.00")      # Lakh range (Rs 5 lakh)
Decimal("10000000.00")    # Crore range (Rs 1 crore)
Decimal("12345.67")       # Decimal precision test
```

### HSN/SAC Codes
```python
"9993" - Healthcare services (consultation, diagnostic)
"9994" - Ambulance services
```

---

## 🎯 Best Practices

### 1. Always Use Decimal for Money
```python
# ❌ Wrong - Float has precision issues
amount = 10000.50

# ✅ Correct - Decimal maintains precision
amount = Decimal("10000.50")
```

### 2. Use Fixtures for Common Setup
```python
# Instead of repeating setup in each test,
# create reusable fixtures in conftest.py or test file
```

### 3. Test Edge Cases
```python
# Don't just test happy path
# Test: zero amounts, negative scenarios, boundary values
```

### 4. Descriptive Test Names
```python
# ❌ Unclear
def test_claim():
    ...

# ✅ Clear
def test_create_claim_with_expired_insurance_raises_error():
    ...
```

### 5. Async Session Management
```python
# Always use async context properly
async with AsyncSessionLocal() as session:
    # Do work
    await session.commit()
```

---

## 📚 Related Files

- **Service Implementation:**
  - `/backend/app/services/billing.py`
  - `/backend/app/services/insurance_claims.py`

- **Models:**
  - `/backend/app/models/invoice.py`
  - `/backend/app/models/insurance.py`

- **API Endpoints:**
  - `/backend/app/api/v1/billing.py`
  - `/backend/app/api/v1/insurance.py`

---

## 🤝 Contributing New Tests

When adding new financial tests:

1. **Choose appropriate test class** based on functionality
2. **Use existing fixtures** where possible
3. **Follow AAA pattern** (Arrange-Act-Assert)
4. **Test both success and failure** cases
5. **Add docstring** explaining what the test validates
6. **Update this guide** with new use cases

Example template:
```python
async def test_new_feature(
    async_session: AsyncSession,
    test_patient: Patient,
    test_invoice: Invoice,
):
    """Test description: what this validates and why."""
    # ARRANGE
    service = InsuranceClaimsService(async_session)

    # ACT
    result = await service.new_feature(...)

    # ASSERT
    assert result.expected_field == expected_value
```

---

**Last Updated:** 2026-01-05
**For Questions:** See TEST_COVERAGE_SUMMARY.md or CLAUDE.md
