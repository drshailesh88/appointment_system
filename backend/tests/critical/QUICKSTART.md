# Quick Start Guide - Authentication Tests

## Run All Tests

```bash
cd /home/user/appointment_system/backend

# Run all authentication tests
pytest tests/critical/test_auth_flows.py -v

# Run with coverage report
pytest tests/critical/test_auth_flows.py --cov=app.api.v1.auth --cov=app.core.security --cov-report=html

# Run specific test class
pytest tests/critical/test_auth_flows.py::TestLoginLogout -v

# Run specific test method
pytest tests/critical/test_auth_flows.py::TestLoginLogout::test_login_with_email_success -v
```

## Test Organization

```
tests/critical/
├── __init__.py                  # Package initialization
├── test_auth_flows.py          # Main test file (40 tests)
├── README.md                   # Comprehensive documentation
└── QUICKSTART.md              # This file
```

## Test Classes

1. **TestLoginLogout** - Login/logout flows (8 tests)
2. **TestTokenRefresh** - Token refresh (6 tests)
3. **TestTokenSecurity** - Token security (8 tests)
4. **TestRoleBasedAccessControl** - RBAC (5 tests)
5. **TestOTPAuthentication** - OTP for patients (8 tests)
6. **TestEdgeCases** - Edge cases (11 tests)

## Common Commands

```bash
# Run only async tests
pytest tests/critical/test_auth_flows.py -k "asyncio" -v

# Run only OTP tests
pytest tests/critical/test_auth_flows.py::TestOTPAuthentication -v

# Run only RBAC tests
pytest tests/critical/test_auth_flows.py::TestRoleBasedAccessControl -v

# Run and stop on first failure
pytest tests/critical/test_auth_flows.py -x

# Run with verbose output and show print statements
pytest tests/critical/test_auth_flows.py -vv -s

# Run with timing information
pytest tests/critical/test_auth_flows.py --durations=10
```

## Expected Output

```
tests/critical/test_auth_flows.py::TestLoginLogout::test_login_with_email_success PASSED
tests/critical/test_auth_flows.py::TestLoginLogout::test_login_with_phone_success PASSED
tests/critical/test_auth_flows.py::TestLoginLogout::test_login_json_endpoint PASSED
...
================================ 40 passed in 5.23s =================================
```

## Troubleshooting

### Missing Dependencies

```bash
pip install pytest pytest-asyncio fastapi[all] sqlalchemy python-jose[cryptography] passlib[bcrypt]
```

### Database Issues

If tests fail with database errors, ensure:
- PostgreSQL is running (or SQLite for tests)
- Test database exists
- Connection string is correct in conftest.py

### Async Issues

For async test failures, ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

## Quick Test

Run this single test to verify setup:
```bash
pytest tests/critical/test_auth_flows.py::TestLoginLogout::test_login_with_email_success -v
```

If it passes, your setup is correct!
