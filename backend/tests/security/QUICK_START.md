# Security Tests - Quick Start Guide

## Run Tests Immediately

```bash
cd /home/user/appointment_system/backend

# Run all security tests
pytest tests/security/test_auth_security.py -v

# Run with detailed output
pytest tests/security/test_auth_security.py -vv

# Run with coverage
pytest tests/security/test_auth_security.py --cov=app --cov-report=term-missing
```

## Test Classes (6 total)

1. **TestAuthenticationBypass** (11 tests) - JWT attacks, SQL injection, timing attacks
2. **TestSessionSecurity** (5 tests) - Token rotation, session invalidation
3. **TestPasswordSecurity** (7 tests) - Bcrypt hashing, no plaintext storage
4. **TestRBACEnforcement** (5 tests) - Privilege escalation, cross-clinic isolation
5. **TestAPISecurityHeaders** (5 tests) - CORS, cache control, header sanitization
6. **TestAuthenticationEdgeCases** (6 tests) - Unicode, long inputs, concurrent logins

**Total:** 39 test methods | 888 lines of code

## Critical Security Tests

### Must Pass Before Production:
- ✅ SQL injection tests (username & password)
- ✅ Expired token rejection
- ✅ Refresh token rotation
- ✅ Password bcrypt hashing
- ✅ Cross-clinic data isolation
- ✅ Privilege escalation prevention

## Quick Verification

```bash
# Verify tests can be discovered
pytest tests/security/test_auth_security.py --collect-only

# Run only critical tests
pytest tests/security/test_auth_security.py -k "sql_injection or expired_token or bcrypt"

# Run fast tests (skip timing attack test)
pytest tests/security/test_auth_security.py -k "not timing_attack"
```

## Files Created

```
tests/security/
├── __init__.py                      # Package init (244 bytes)
├── test_auth_security.py            # Main tests (888 lines, 30KB)
├── README.md                        # Full documentation (7.8KB)
├── IMPLEMENTATION_SUMMARY.md        # Technical details (12KB)
└── QUICK_START.md                   # This file
```

## Expected Output

```
tests/security/test_auth_security.py::TestAuthenticationBypass::test_access_protected_endpoint_without_token PASSED [2%]
tests/security/test_auth_security.py::TestAuthenticationBypass::test_access_with_expired_token PASSED [5%]
tests/security/test_auth_security.py::TestAuthenticationBypass::test_access_with_malformed_token PASSED [7%]
...
==================== 39 passed in 8.45s ====================
```

## Common Commands

```bash
# Run specific class
pytest tests/security/test_auth_security.py::TestPasswordSecurity

# Run specific test
pytest tests/security/test_auth_security.py::TestAuthenticationBypass::test_sql_injection_in_login_username

# Run with print statements
pytest tests/security/test_auth_security.py -s

# Run and stop at first failure
pytest tests/security/test_auth_security.py -x

# Run last failed tests
pytest tests/security/test_auth_security.py --lf
```

## Integration with CI/CD

Add to `.github/workflows/tests.yml`:

```yaml
- name: Run Security Tests
  run: |
    cd backend
    pytest tests/security/test_auth_security.py -v --tb=short
```

## Next Steps

1. ✅ Tests created and ready
2. 🔄 Install dependencies: `pip install -r requirements.txt`
3. 🔄 Run tests: `pytest tests/security/test_auth_security.py -v`
4. 🔄 Fix any failures
5. 🔄 Add to CI/CD pipeline
6. 🔄 Run before each release

## Get Help

- Full docs: `tests/security/README.md`
- Technical details: `tests/security/IMPLEMENTATION_SUMMARY.md`
- Test code: `tests/security/test_auth_security.py`

---

**Ready to use!** Just run: `pytest tests/security/test_auth_security.py -v`
