# Critical Test Suite for DocAssist Practice Manager

This directory contains comprehensive tests for critical business functionality including data integrity, security, and core workflows.

## Test Files

### test_appointment_booking.py
Comprehensive appointment booking system tests covering:
- Happy path scenarios
- Edge cases and error conditions
- Input validation
- Business rule enforcement
- Status transitions
- Concurrency handling

**Coverage:** 49 test methods across 8 test classes

## Test Organization

Each test file is organized by functionality:
```
TestAppointmentBookingHappyPath       - Successful scenarios
TestAppointmentBookingEdgeCases       - Error conditions & business rules
TestAppointmentBookingValidation      - Input validation
TestAppointmentSlotAvailability       - Slot checking
TestAppointmentDoctorSchedule         - Schedule management
TestAppointmentConcurrency            - Concurrent access
TestAppointmentIntegrations           - External integrations
TestAppointmentTokenGeneration        - Queue token logic
```

## Running Tests

```bash
# All critical tests
pytest tests/critical/ -v

# Specific test file
pytest tests/critical/test_appointment_booking.py -v

# With coverage
pytest tests/critical/ --cov=app --cov-report=html

# Parallel execution
pytest tests/critical/ -n auto
```

## Test Standards

1. **Independence:** Each test can run in isolation
2. **Fixtures:** Use conftest.py fixtures for setup
3. **Mocking:** External services are mocked
4. **Naming:** Descriptive test names following pattern `test_<action>_<expected_result>`
5. **Assertions:** Clear, specific assertions with helpful messages
6. **Coverage:** Aim for >90% code coverage on critical paths

## Adding New Tests

When adding critical tests:
1. Create descriptive test class names
2. Use proper fixtures from conftest.py
3. Mock external dependencies
4. Test both success and failure paths
5. Include edge cases
6. Document complex test scenarios

## Dependencies

- pytest
- pytest-asyncio
- pytest-cov
- httpx
- FastAPI TestClient
