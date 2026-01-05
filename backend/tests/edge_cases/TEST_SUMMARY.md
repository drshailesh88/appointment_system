# Concurrency Tests - Quick Reference

## Test Coverage Summary

| Test Class | Test Count | Critical Issues Tested |
|------------|------------|----------------------|
| `TestDoubleBookingPrevention` | 3 | Appointment conflicts |
| `TestPaymentRaceConditions` | 3 | Payment over-collection |
| `TestDataModificationConflicts` | 2 | Lost updates |
| `TestResourceContention` | 3 | Duplicate IDs/numbers |
| `TestDatabaseLocking` | 3 | Deadlocks, locking |
| **TOTAL** | **14** | **All concurrency scenarios** |

---

## Test Matrix

### ✅ Double Booking Prevention

| # | Test | Concurrent Operations | Expected Result |
|---|------|---------------------|-----------------|
| 1 | Same slot booking | 2 patients → 1 slot | Only 1 succeeds |
| 2 | Double submit | 3 requests → 1 patient | Only 1 booking created |
| 3 | Booking during cancel | Book + Cancel | No overlap |

### ✅ Payment Race Conditions

| # | Test | Concurrent Operations | Expected Result |
|---|------|---------------------|-----------------|
| 4 | Double payment | 2 payments → 1 invoice | Total ≤ invoice amount |
| 5 | Payment during void | Pay + Void invoice | Consistent state |
| 6 | Concurrent refunds | 2 refunds → 1 payment | Total refund ≤ payment |

### ✅ Data Modification Conflicts

| # | Test | Concurrent Operations | Expected Result |
|---|------|---------------------|-----------------|
| 7 | Patient updates | Update name + phone | Both persist |
| 8 | Appointment status | Start + Cancel | Valid final state |

### ✅ Resource Contention

| # | Test | Concurrent Operations | Expected Result |
|---|------|---------------------|-----------------|
| 9 | Token numbers | 5 check-ins | All unique tokens |
| 10 | Invoice numbers | 5 invoices | All unique numbers |
| 11 | Waitlist positions | 5 additions | All unique positions |

### ✅ Database Locking

| # | Test | Concurrent Operations | Expected Result |
|---|------|---------------------|-----------------|
| 12 | Row-level locking | 3 updates with lock | Serialized execution |
| 13 | Optimistic locking | Version check pattern | Documented pattern |
| 14 | Deadlock prevention | Cross-resource locks | At least 1 completes |

---

## Critical Findings

### 🔴 HIGH RISK - Immediate Action Required

1. **Double Booking** (Test #1)
   - Current: Application-level check only
   - Risk: Race condition window ~10-50ms
   - Fix: Add database constraint or SELECT FOR UPDATE
   - Impact: Patient experience, schedule integrity

2. **Duplicate Token Numbers** (Test #9)
   - Current: `max() + 1` without locking
   - Risk: Multiple patients get same token
   - Fix: Use database sequence
   - Impact: Queue confusion, patient complaints

3. **Payment Over-Collection** (Test #4)
   - Current: Balance check not atomic
   - Risk: Invoice paid twice
   - Fix: Row-level lock on invoice during payment
   - Impact: Financial loss, refund complexity

### 🟡 MEDIUM RISK - Plan Mitigation

4. **Duplicate Invoice Numbers** (Test #10)
   - Current: Sequential generation
   - Risk: Accounting compliance issues
   - Fix: Use database sequence
   - Impact: Audit trail, legal compliance

5. **Lost Updates** (Test #7, #8)
   - Current: Last-write-wins
   - Risk: Data loss during concurrent edits
   - Fix: Add version fields
   - Impact: Data accuracy

### 🟢 LOW RISK - Monitor

6. **Deadlocks** (Test #14)
   - Current: Rare in single-server setup
   - Risk: Increases with load
   - Fix: Consistent lock ordering
   - Impact: User experience (retries)

---

## Quick Commands

```bash
# Run all concurrency tests
pytest tests/edge_cases/test_concurrency.py -v

# Run only high-risk tests
pytest tests/edge_cases/test_concurrency.py::TestDoubleBookingPrevention::test_concurrent_same_slot_booking_prevented -v
pytest tests/edge_cases/test_concurrency.py::TestResourceContention::test_concurrent_queue_number_generation -v
pytest tests/edge_cases/test_concurrency.py::TestPaymentRaceConditions::test_double_payment_prevention -v

# Run with stress (10 iterations)
for i in {1..10}; do pytest tests/edge_cases/test_concurrency.py -v; done

# Check for flaky tests
pytest tests/edge_cases/test_concurrency.py --count=20
```

---

## Metrics to Monitor

### Production Monitoring

```sql
-- Check for duplicate token numbers
SELECT doctor_id, token_number, COUNT(*)
FROM appointments
WHERE DATE(scheduled_start) = CURRENT_DATE
GROUP BY doctor_id, token_number
HAVING COUNT(*) > 1;

-- Check for double bookings
SELECT a1.doctor_id, a1.scheduled_start, COUNT(*)
FROM appointments a1
JOIN appointments a2 ON
    a1.doctor_id = a2.doctor_id AND
    a1.id != a2.id AND
    a1.scheduled_start < a2.scheduled_end AND
    a1.scheduled_end > a2.scheduled_start
WHERE a1.status NOT IN ('cancelled', 'no_show')
  AND a2.status NOT IN ('cancelled', 'no_show')
GROUP BY a1.doctor_id, a1.scheduled_start;

-- Check for over-payments
SELECT invoice_id, total_amount, paid_amount
FROM invoices
WHERE paid_amount > total_amount;

-- Check for over-refunds
SELECT id, amount, refund_amount
FROM payments
WHERE refund_amount > amount;
```

---

## Implementation Roadmap

### Week 1: Critical Fixes
- [ ] Add database constraint for appointment overlaps
- [ ] Implement SELECT FOR UPDATE for payments
- [ ] Add database sequences for token numbers

### Week 2: Database Improvements
- [ ] Add invoice number sequence
- [ ] Implement waitlist position locking
- [ ] Add transaction isolation where needed

### Week 3: Application Improvements
- [ ] Add version fields to critical models
- [ ] Implement optimistic locking checks
- [ ] Add retry logic for transient failures

### Week 4: Testing & Validation
- [ ] Load testing with Artillery/Locust
- [ ] Verify all tests pass consistently
- [ ] Document production monitoring

---

## Dependencies

### Python Packages Required
```python
pytest>=7.4.0
pytest-asyncio>=0.21.0
sqlalchemy>=2.0.0
```

### Database Requirements
- PostgreSQL 12+ (for advanced locking)
- SQLite 3.35+ (for testing)
- Proper transaction isolation level set

---

## Contact

For questions about these tests:
- Check: `CONCURRENCY_TESTS.md` (detailed documentation)
- Review: Test code comments in `test_concurrency.py`
- Monitor: Sentry for production race conditions

---

*Quick Reference v1.0 - 2026-01-05*
