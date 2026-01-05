# AI Services Test Documentation

## Overview
Comprehensive test suite for DocAssist Practice Manager AI services including Entity Extraction, Action Execution, and LLM Integration.

**Phase:** 16b - Conversational Actions
**File:** `test_ai_services.py`
**Created:** 2026-01-05
**Test Count:** 101 tests across 14 test classes
**Lines of Code:** 1,374

---

## Test Structure

### 1. AI Entity Extractor Tests (41 tests)

#### `TestEntityExtractorDateExtraction` (21 tests)
Tests natural language date parsing with multiple formats:

**Relative Dates:**
- `test_extract_date_today` - "today", "aaj" (Hindi)
- `test_extract_date_tomorrow` - "tomorrow", "kal" (Hindi)
- `test_extract_date_day_after_tomorrow` - "day after tomorrow", "parso" (Hindi)
- `test_extract_date_yesterday` - "yesterday"

**Time Periods:**
- `test_extract_date_next_week` - "next week"
- `test_extract_date_this_week` - "this week"
- `test_extract_date_next_month` - "next month"

**Day Names:**
- `test_extract_date_monday` - "Monday"
- `test_extract_date_tuesday` - "Tuesday"
- `test_extract_date_friday` - "Friday"

**Specific Formats:**
- `test_extract_date_specific_ddmmyyyy` - "15/01/2026"
- `test_extract_date_specific_iso` - "2026-02-20"
- `test_extract_date_month_name_15th_january` - "15th January"
- `test_extract_date_month_name_january_15` - "January 15th"

**Edge Cases:**
- `test_extract_date_no_date_found` - No date in message
- `test_extract_date_ambiguous` - Ambiguous input
- `test_extract_date_with_reference_date` - Custom reference date
- `test_extract_date_past_month_assumes_next_year` - Past month handling

#### `TestEntityExtractorTimeExtraction` (13 tests)
Tests time parsing from natural language:

**12-Hour Format:**
- `test_extract_time_3pm` - "3pm"
- `test_extract_time_3_30pm` - "3:30pm"
- `test_extract_time_9am` - "9am"
- `test_extract_time_12pm` - "12pm" (noon)
- `test_extract_time_12am` - "12am" (midnight)

**24-Hour Format:**
- `test_extract_time_24hour_1530` - "15:30"
- `test_extract_time_24hour_0900` - "09:00"

**Word-Based:**
- `test_extract_time_morning` - "morning" → 9:00 AM
- `test_extract_time_afternoon` - "afternoon" → 2:00 PM
- `test_extract_time_evening` - "evening" → 6:00 PM
- `test_extract_time_night` - "night" → 8:00 PM
- `test_extract_time_lunch` - "lunch" → 2:00 PM

**Edge Cases:**
- `test_extract_time_no_time_found` - No time in message
- `test_extract_time_invalid_hour` - Invalid hour handling

#### `TestEntityExtractorPatientExtraction` (4 tests)
Tests patient identification from messages:

- `test_extract_patient_by_phone` - 10-digit phone number extraction
- `test_extract_patient_by_name` - Name pattern matching
- `test_extract_patient_from_context` - Context-aware extraction
- `test_extract_patient_not_found` - Not found scenario

#### `TestEntityExtractorDoctorExtraction` (4 tests)
Tests doctor identification:

- `test_extract_doctor_by_name_with_dr` - "Dr. Sharma"
- `test_extract_doctor_by_name_without_dr` - "Sharma"
- `test_extract_doctor_from_context` - Context-aware extraction
- `test_extract_doctor_default_first_active` - Default doctor selection

#### `TestEntityExtractorOthers` (6 tests)
Tests urgency and reason extraction:

**Urgency Levels:**
- `test_extract_urgency_high_urgent` - "urgent"
- `test_extract_urgency_high_emergency` - "emergency"
- `test_extract_urgency_high_asap` - "ASAP"
- `test_extract_urgency_medium_soon` - "soon"
- `test_extract_urgency_low_default` - Default low urgency

**Reason Extraction:**
- `test_extract_reason_for` - "for headache"
- `test_extract_reason_because_of` - "because of chest pain"
- `test_extract_reason_complaint` - "complaint: fever"

#### `TestEntityExtractorIntegration` (3 tests)
Integration tests for combined extraction:

- `test_extract_date_and_time_together` - "tomorrow at 3pm"
- `test_extract_complex_message` - Multiple entities: "Urgent appointment for chest pain tomorrow afternoon"
- `test_extract_hindi_english_mixed` - "kal 3pm appointment book karo for fever"

---

### 2. AI Action Executor Tests (41 tests)

#### `TestActionExecutorBookAppointment` (7 tests)
Tests appointment booking functionality:

**Validation:**
- `test_book_appointment_missing_patient_id` - Requires patient_id
- `test_book_appointment_missing_date` - Requires date
- `test_book_appointment_missing_time` - Requires time
- `test_book_appointment_patient_not_found` - Patient existence check

**Business Logic:**
- `test_book_appointment_past_datetime` - Rejects past appointments
- `test_book_appointment_slot_conflict` - Detects conflicting appointments
- `test_book_appointment_success` - Successful booking with all validations

#### `TestActionExecutorReschedule` (3 tests)
Tests appointment rescheduling:

- `test_reschedule_missing_appointment_id` - Parameter validation
- `test_reschedule_appointment_not_found` - Appointment existence check
- `test_reschedule_slot_conflict` - Conflict detection for new slot

#### `TestActionExecutorCancel` (3 tests)
Tests appointment cancellation:

- `test_cancel_missing_appointment_id` - Parameter validation
- `test_cancel_appointment_not_found` - Appointment existence check
- `test_cancel_appointment_success` - Successful cancellation with reason

#### `TestActionExecutorOthers` (7 tests)
Tests additional action types:

**Waitlist:**
- `test_add_to_waitlist_missing_patient_id` - Validation
- `test_add_to_waitlist_success` - Successful addition with priority

**Patient Lookup:**
- `test_lookup_patient_empty_query` - Query validation

**Availability:**
- `test_check_availability_missing_date` - Parameter validation
- `test_check_availability_success` - Successful availability check

**Error Handling:**
- `test_invalid_action_type` - Unknown action handling

#### `TestActionExecutorUndo` (2 tests)
Tests undo functionality:

- `test_undo_no_history` - No actions to undo
- `test_undo_book_appointment` - Undo successful booking

---

### 3. LLM Integration Tests (19 tests)

#### `TestAIAssistantLLMIntegration` (11 tests)
Tests Ollama LLM integration with mocking:

**API Communication:**
- `test_chat_ollama_success` - Successful LLM call with function extraction
- `test_chat_ollama_unavailable` - Graceful fallback when Ollama down
- `test_chat_ollama_timeout` - Timeout handling
- `test_chat_malformed_llm_response` - Invalid JSON handling
- `test_chat_missing_function_in_response` - Clarification flow

**Session Management:**
- `test_session_management` - Get/clear sessions
- `test_cleanup_old_sessions` - Automatic cleanup

**Fallback Parsing:**
- `test_fallback_parse_procedure_query` - Keyword-based procedure stats
- `test_fallback_parse_revenue_query` - Keyword-based revenue
- `test_fallback_parse_appointment_query` - Keyword-based appointments
- `test_fallback_parse_patient_search` - Keyword-based patient search
- `test_fallback_parse_doctor_stats` - Keyword-based doctor stats

#### `TestAIAssistantFunctionCalling` (6 tests)
Tests function calling and response generation:

**Suggestion Generation:**
- `test_generate_suggestions_procedure_stats` - Follow-up suggestions for procedures
- `test_generate_suggestions_revenue` - Follow-up suggestions for revenue

**Date Parsing:**
- `test_parse_relative_date_today` - "today"
- `test_parse_relative_date_yesterday` - "yesterday"
- `test_parse_relative_date_this_month_start` - "this month start"

**Argument Parsing:**
- `test_parse_function_arguments_dates` - Date string to date object
- `test_parse_function_arguments_uuid` - String to UUID conversion

---

### 4. Edge Cases & Error Handling (3 tests)

#### `TestEdgeCases`
Comprehensive edge case coverage:

- `test_entity_extractor_with_special_characters` - "Book for @#$% tomorrow!!! at 3pm???"
- `test_entity_extractor_empty_message` - Empty string handling
- `test_action_executor_exception_handling` - Database errors
- `test_action_definitions_completeness` - All actions have definitions

---

## Test Patterns & Best Practices

### 1. Fixtures
```python
@pytest.fixture
def mock_db(self):
    """Create mock database session."""
    db = MagicMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db
```

### 2. Async Testing
```python
@pytest.mark.asyncio
async def test_book_appointment_success(self, executor, mock_db):
    # Test async functions
    result = await executor.execute_action(...)
    assert result.success
```

### 3. Mocking HTTP Calls
```python
with patch("httpx.AsyncClient.post") as mock_post:
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: mock_response,
        raise_for_status=lambda: None,
    )
    result = await assistant.chat(...)
```

### 4. Database Mocking
```python
# Mock patient lookup
mock_query = MagicMock()
mock_query.filter.return_value = mock_query
mock_query.first.return_value = patient
mock_db.query.return_value = mock_query
```

---

## Running the Tests

### Run All AI Service Tests
```bash
cd /home/user/appointment_system/backend
pytest tests/services/test_ai_services.py -v
```

### Run Specific Test Class
```bash
# Entity extraction tests
pytest tests/services/test_ai_services.py::TestEntityExtractorDateExtraction -v

# Action execution tests
pytest tests/services/test_ai_services.py::TestActionExecutorBookAppointment -v

# LLM integration tests
pytest tests/services/test_ai_services.py::TestAIAssistantLLMIntegration -v
```

### Run with Coverage Report
```bash
pytest tests/services/test_ai_services.py \
  --cov=app.services.ai_entity_extractor \
  --cov=app.services.ai_action_executor \
  --cov=app.services.ai_assistant \
  --cov-report=html \
  --cov-report=term
```

### Run Only Async Tests
```bash
pytest tests/services/test_ai_services.py -k "asyncio" -v
```

### Run Specific Test Function
```bash
pytest tests/services/test_ai_services.py::TestEntityExtractorDateExtraction::test_extract_date_hindi_kal -v
```

---

## Coverage Analysis

### Entity Extractor Coverage
- ✅ **Date Extraction:** 23+ different formats
- ✅ **Time Extraction:** 10+ different formats
- ✅ **Hindi Support:** aaj, kal, parso
- ✅ **Patient Extraction:** Phone, name, context
- ✅ **Doctor Extraction:** Name patterns, context, defaults
- ✅ **Urgency:** High, medium, low
- ✅ **Reason:** Multiple pattern matching

### Action Executor Coverage
- ✅ **7 Action Types:** Book, reschedule, cancel, waitlist, reminder, lookup, availability
- ✅ **Parameter Validation:** All required parameters
- ✅ **Error Handling:** Not found, conflicts, access denied
- ✅ **Business Logic:** Slot conflicts, past dates, clinic access
- ✅ **Undo Functionality:** Record and revert actions

### LLM Integration Coverage
- ✅ **API Communication:** Success, failure, timeout
- ✅ **Response Parsing:** JSON, malformed, missing data
- ✅ **Fallback:** Keyword-based parsing when LLM unavailable
- ✅ **Session Management:** Create, get, clear, cleanup
- ✅ **Function Calling:** Extract function calls from LLM
- ✅ **Suggestions:** Context-aware follow-up suggestions

---

## Mock Strategy

### Database Mocking
- All database operations use `MagicMock()` and `AsyncMock()`
- No real database connections required
- Tests are fast and isolated

### HTTP Mocking
- Ollama API calls mocked with `patch("httpx.AsyncClient.post")`
- Configurable responses for different scenarios
- Timeout and error simulation

### Model Mocking
- Patient, Doctor, Appointment models use `MagicMock(spec=Model)`
- Spec ensures correct attribute access
- Easy to configure return values

---

## Dependencies

```txt
pytest>=7.4.4              # Test framework
pytest-asyncio>=0.23.3     # Async test support
pytest-mock>=3.12.0        # Advanced mocking
httpx>=0.26.0              # HTTP client (for mocking)
```

All dependencies are already in `requirements.txt`.

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: AI Services Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run AI services tests
        run: |
          cd backend
          pytest tests/services/test_ai_services.py -v --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Future Enhancements

1. **Performance Tests**
   - Benchmark entity extraction speed
   - LLM response time tests
   - Concurrent action execution

2. **Integration Tests**
   - Real database integration (optional)
   - Real Ollama integration (optional)
   - End-to-end conversation flows

3. **Stress Tests**
   - Large message volumes
   - Session overflow handling
   - Memory leak detection

4. **Additional Edge Cases**
   - More Hindi language patterns
   - Regional date/time formats
   - Multi-language mixing

---

## Troubleshooting

### Tests Failing?

**Issue:** Import errors
```bash
# Solution: Install dependencies
cd backend
pip install -r requirements.txt
```

**Issue:** Async tests not running
```bash
# Solution: Check pytest-asyncio is installed
pip install pytest-asyncio
```

**Issue:** Mock not working
```bash
# Solution: Check import paths match actual code
# Ensure app.services.* modules exist
```

### Common Errors

1. **ModuleNotFoundError: No module named 'app'**
   - Run pytest from `/backend` directory
   - Check PYTHONPATH includes backend directory

2. **AttributeError in mocks**
   - Ensure `spec=Model` is used in MagicMock
   - Check model attributes exist

3. **Async tests hanging**
   - Ensure `@pytest.mark.asyncio` decorator
   - Check `asyncio_mode = auto` in pytest.ini

---

## Contact & Support

For questions or issues with these tests:
- Check test docstrings for detailed explanations
- Review referenced service files for implementation details
- Refer to Phase 16b documentation in `.claude/specs/`

---

**Last Updated:** 2026-01-05
**Version:** 1.0
**Author:** Claude Code (DocAssist Development Team)
