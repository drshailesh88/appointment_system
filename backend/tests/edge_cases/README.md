# Edge Case Tests - Comprehensive Test Suite

## Overview

Comprehensive test suite for edge cases in DocAssist Practice Manager:
- **Network Failures** - External service failures and offline scenarios
- **Concurrency** - Race conditions and data integrity under concurrent load
- **I18n Data** - International character handling

## Test Files

### 1. Network Failures & Offline Scenarios
**File:** `test_network_failures.py`
- **Lines of Code:** 1,213
- **Test Classes:** 12
- **Test Functions:** 46
- **Documentation:** See sections below

### 2. Concurrency & Race Conditions
**File:** `test_concurrency.py`
- **Lines of Code:** 1,175
- **Test Classes:** 5
- **Test Functions:** 14
- **Documentation:** `CONCURRENCY_TESTS.md` (detailed) | `TEST_SUMMARY.md` (quick ref)

### 3. International Data Handling
**File:** `test_i18n_data.py`
- **Lines of Code:** ~1,200
- **Test Classes:** Multiple
- **Coverage:** Unicode, RTL text, Indian languages

---

## 🔒 Concurrency & Race Condition Tests

**Quick Reference:** See `TEST_SUMMARY.md` | **Details:** See `CONCURRENCY_TESTS.md`

### Test Categories (14 tests)

1. **Double Booking Prevention** (3 tests) - Prevents appointment conflicts
2. **Payment Race Conditions** (3 tests) - Prevents over-payment/over-refund
3. **Data Modification Conflicts** (2 tests) - Prevents lost updates
4. **Resource Contention** (3 tests) - Prevents duplicate IDs/tokens
5. **Database Locking** (3 tests) - Tests locking mechanisms

### Critical Issues Tested

| Issue | Risk Level | Test Count | Status |
|-------|-----------|------------|--------|
| Double booking appointments | 🔴 HIGH | 3 | ⚠️ Needs DB constraint |
| Duplicate token numbers | 🔴 HIGH | 1 | ⚠️ Needs sequence |
| Payment over-collection | 🔴 HIGH | 1 | ⚠️ Needs row locking |
| Duplicate invoice numbers | 🟡 MEDIUM | 1 | ⚠️ Needs sequence |
| Lost data updates | 🟡 MEDIUM | 2 | ⚠️ Needs versioning |
| Deadlocks | 🟢 LOW | 1 | ✅ Monitor only |

### Running Concurrency Tests

```bash
# All concurrency tests
pytest tests/edge_cases/test_concurrency.py -v

# High-risk tests only
pytest tests/edge_cases/test_concurrency.py::TestDoubleBookingPrevention -v
pytest tests/edge_cases/test_concurrency.py::TestPaymentRaceConditions -v

# Stress test (10 iterations)
for i in {1..10}; do pytest tests/edge_cases/test_concurrency.py -v; done
```

---

## 🌐 Network Failure Tests

### Test Coverage

### 1. External Service Failures (20 tests)

#### Razorpay Payment Gateway (5 tests)
- ✅ `test_razorpay_timeout` - API timeout handling
- ✅ `test_razorpay_500_error` - Server error (500) handling
- ✅ `test_razorpay_network_error` - Network connection failures
- ✅ `test_razorpay_not_configured` - Missing API credentials
- ✅ `test_razorpay_refund_failure` - Refund operation failures

#### SMS/MSG91 Gateway (4 tests)
- ✅ `test_sms_timeout` - SMS API timeout
- ✅ `test_sms_not_configured` - Missing SMS credentials
- ✅ `test_whatsapp_fallback_to_sms` - WhatsApp→SMS fallback
- ✅ `test_sms_api_500_error` - Gateway errors

#### Google Calendar API (5 tests)
- ✅ `test_google_calendar_not_configured` - Missing OAuth credentials
- ✅ `test_google_calendar_token_refresh_failure` - Token refresh errors
- ✅ `test_google_calendar_create_event_404` - Non-existent calendar
- ✅ `test_google_calendar_delete_missing_event` - Already deleted events
- ✅ `test_google_calendar_network_timeout` - API timeouts

#### Firebase Push Notifications (3 tests)
- ✅ `test_firebase_not_initialized` - Firebase SDK not initialized
- ✅ `test_firebase_invalid_token_cleanup` - Invalid token deactivation
- ✅ `test_firebase_topic_send_failure` - Topic broadcast failures

#### Ollama/AI Assistant (4 tests)
- ✅ `test_ollama_not_running` - Ollama service unavailable
- ✅ `test_ollama_timeout` - LLM API timeout
- ✅ `test_ollama_malformed_response` - Invalid JSON responses
- ✅ `test_ollama_500_error` - Ollama server errors

### 2. Database Connection Issues (6 tests)

#### PostgreSQL Connection (3 tests)
- ✅ `test_database_timeout` - Query timeouts
- ✅ `test_database_connection_lost` - Connection dropped mid-query
- ✅ `test_connection_pool_exhausted` - Pool limit reached

#### EMR SQLite Database (4 tests)
- ✅ `test_emr_database_not_found` - Database file missing
- ✅ `test_emr_database_locked` - File locked by another process
- ✅ `test_emr_corrupted_database` - Corrupted database file
- ✅ `test_emr_sync_timeout` - Sync operation timeout

### 3. Qdrant Vector Database (3 tests)
- ✅ `test_qdrant_not_available` - Qdrant not installed
- ✅ `test_qdrant_connection_refused` - Qdrant server down
- ✅ `test_qdrant_search_timeout` - Search query timeout
- ✅ `test_fastembed_not_available` - FastEmbed not installed

### 4. Graceful Degradation (5 tests)
- ✅ `test_appointment_creation_without_sms` - Works without SMS
- ✅ `test_appointment_creation_without_calendar_sync` - Works without calendar
- ✅ `test_search_without_qdrant` - Falls back to database search
- ✅ `test_payment_without_razorpay` - Manual payments without gateway
- ✅ App continues functioning when optional services fail

### 5. Retry Logic (3 tests)
- ✅ `test_razorpay_retry_on_timeout` - Retry pattern verification
- ✅ `test_exponential_backoff_simulation` - Exponential backoff
- ✅ `test_max_retry_limit` - Respects max retry limits

### 6. Data Consistency (4 tests)
- ✅ `test_transaction_rollback_on_failure` - Database rollback
- ✅ `test_idempotent_payment_creation` - Duplicate prevention
- ✅ `test_duplicate_webhook_handling` - Webhook idempotency
- ✅ `test_partial_sync_recovery` - Recovers from partial failures

### 7. Offline Queue (3 tests)
- ✅ `test_queue_failed_sms_for_retry` - Queue failed SMS
- ✅ `test_queue_failed_push_notification` - Dead letter queue
- ✅ `test_process_queued_operations_on_reconnect` - Process queue on reconnect

## Key Features Tested

### Offline-First Architecture
- ✅ App continues without internet
- ✅ Local SQLite operations work independently
- ✅ Queues operations for later sync

### Graceful Fallbacks
- ✅ WhatsApp → SMS fallback
- ✅ Qdrant → Database search fallback
- ✅ Ollama → Rule-based fallback
- ✅ Firebase → Logs warning, continues

### Error Recovery
- ✅ Invalid FCM token cleanup
- ✅ Transaction rollback on failures
- ✅ EMR sync recovery from partial failures
- ✅ Webhook duplicate prevention

### Configuration Safety
- ✅ Checks service availability before use
- ✅ Graceful handling of missing credentials
- ✅ Clear error messages for configuration issues

## Running the Tests

### All Edge Case Tests
```bash
# Run all edge case tests
pytest tests/edge_cases/ -v

# Run with coverage
pytest tests/edge_cases/ --cov=app --cov-report=html

# Run in parallel (careful with concurrency tests!)
pytest tests/edge_cases/test_network_failures.py -n 4
```

### Network Failure Tests Only
```bash
# Run all network failure tests
pytest tests/edge_cases/test_network_failures.py -v

# Run specific test class
pytest tests/edge_cases/test_network_failures.py::TestRazorpayNetworkFailures -v

# Run specific test
pytest tests/edge_cases/test_network_failures.py::TestRazorpayNetworkFailures::test_razorpay_timeout -v
```

### Concurrency Tests Only
```bash
# Run all concurrency tests
pytest tests/edge_cases/test_concurrency.py -v

# Run specific category
pytest tests/edge_cases/test_concurrency.py::TestDoubleBookingPrevention -v
pytest tests/edge_cases/test_concurrency.py::TestPaymentRaceConditions -v

# Stress test
for i in {1..20}; do pytest tests/edge_cases/test_concurrency.py -q; done | grep -E "passed|FAILED"
```

## Test Technologies

- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **unittest.mock** - Mocking framework
- **httpx** - HTTP client (for external APIs)
- **SQLAlchemy** - Database ORM

## Expected Behavior

All tests verify that:
1. **No crashes** - App handles errors gracefully
2. **Clear logging** - Errors are logged with context
3. **User feedback** - Users see meaningful error messages
4. **Data safety** - No data corruption on failures
5. **Recovery** - Operations can retry/resume

## Integration with CI/CD

These tests should be run:
- ✅ On every commit (pre-commit hook)
- ✅ In CI pipeline (GitHub Actions, GitLab CI)
- ✅ Before production deployments
- ✅ During stress testing

## Future Enhancements

### Network Failures
- [ ] Add circuit breaker pattern tests
- [ ] Test rate limiting scenarios
- [ ] Add chaos engineering tests
- [ ] Test partial network failures (slow connections)
- [ ] Add distributed tracing verification
- [ ] Test cross-service failure cascades

### Concurrency
- [ ] Implement database constraints for double booking
- [ ] Add database sequences for token/invoice numbers
- [ ] Add version fields for optimistic locking
- [ ] Implement row-level locking for payments
- [ ] Add distributed locking (Redis) for multi-server
- [ ] Load testing with Artillery/Locust

### I18n
- [ ] Test more Indian languages (Tamil, Telugu, Bengali)
- [ ] Test emoji handling in patient names
- [ ] Test mixed RTL/LTR text
- [ ] Test PDF generation with Unicode
- [ ] Test SMS encoding for various languages

---

## Documentation Index

- **README.md** (this file) - Overview of all edge case tests
- **CONCURRENCY_TESTS.md** - Detailed concurrency test documentation
- **TEST_SUMMARY.md** - Quick reference for concurrency tests
- **test_network_failures.py** - Network failure test implementation
- **test_concurrency.py** - Concurrency test implementation
- **test_i18n_data.py** - International data test implementation

---

**Last Updated:** 2026-01-05
**Test Suite Version:** 2.0
**Total Test Count:** 60+ tests across all edge cases
**Coverage:** Network Failures, Concurrency, Race Conditions, I18n, Data Integrity
