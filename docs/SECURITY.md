# Security Documentation

This document outlines the security measures implemented in DocAssist Practice Manager.

## Overview

DocAssist Practice Manager implements multiple layers of security to protect patient data and prevent common attack vectors. All security measures are production-ready and follow OWASP best practices.

---

## 1. JWT Secret Validation ✅

### Implementation

**File:** `backend/app/core/config.py`

The application enforces secure JWT secret configuration:

- **Production Validation**: Application refuses to start if using default JWT secret in production
- **Length Check**: Minimum 32 characters required for production secrets
- **Development Warning**: Warns developers when using default secrets in non-production

### Configuration

```bash
# Generate a secure JWT secret
openssl rand -hex 32

# Set in environment
export JWT_SECRET_KEY="your-generated-secret-here"
```

### Error Messages

```
CRITICAL SECURITY ERROR: Default JWT secret detected in production.
Set JWT_SECRET_KEY environment variable to a secure random value.
Generate one with: openssl rand -hex 32
```

---

## 2. Rate Limiting ✅

### Implementation

**File:** `backend/app/main.py`

Uses SlowAPI middleware for comprehensive rate limiting:

- **Global Rate Limit**: 60 requests/minute per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- **Response Headers**: Exposes rate limit status via `X-RateLimit-*` headers
- **Endpoint-Specific Limits**: Critical endpoints have stricter limits

### Endpoint-Specific Limits

| Endpoint | Limit | Rationale |
|----------|-------|-----------|
| `POST /auth/register` | 5/minute | Prevent account creation abuse |
| `POST /auth/login` | 10/minute | Prevent brute-force attacks |
| `POST /auth/login/json` | 10/minute | Prevent brute-force attacks |
| `POST /auth/refresh` | 20/minute | Allow legitimate token refreshes |
| `POST /public/otp/send` | 5/minute | Prevent SMS/OTP abuse |
| `POST /public/otp/verify` | 10/minute | Prevent OTP brute-force |
| `POST /public/appointments` | 10/minute | Prevent booking spam |

### Configuration

```bash
# Set global rate limit
export RATE_LIMIT_PER_MINUTE=60
```

### Response Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1641024000
```

---

## 3. CORS Configuration ✅

### Implementation

**File:** `backend/app/main.py`

CORS is configured with explicit whitelisting:

**Allowed Methods:**
- GET
- POST
- PUT
- DELETE
- PATCH
- OPTIONS

**Allowed Headers:**
- Content-Type
- Authorization
- Accept
- Origin
- User-Agent
- DNT
- Cache-Control
- X-Requested-With

**Exposed Headers:**
- X-RateLimit-Limit
- X-RateLimit-Remaining
- X-RateLimit-Reset

**Credentials:** Enabled (for cookie-based auth if needed)

### Configuration

```bash
# Set allowed origins (JSON array)
export CORS_ORIGINS='["https://yourdomain.com", "https://app.yourdomain.com"]'
```

### Development vs Production

- **Development**: `http://localhost:*` allowed
- **Production**: Only whitelisted domains allowed

---

## 4. Security Headers ✅

### Implementation

**File:** `backend/app/main.py` (SecurityHeadersMiddleware)

All responses include security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Enable XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer leakage |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS (production only) |
| `Content-Security-Policy` | See below | Prevent XSS/injection |

### Content Security Policy

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self' data:;
connect-src 'self';
frame-ancestors 'none';
```

**Note:** `unsafe-inline` and `unsafe-eval` are temporary for framework compatibility. Tighten in production.

---

## 5. Structured Logging ✅

### Implementation

**File:** `backend/app/main.py`

Replaces `print()` statements with proper logging:

- **Development**: Human-readable format with timestamps
- **Production**: JSON-structured logs for log aggregation (ELK, Splunk, etc.)

### Log Levels

- **INFO**: Application lifecycle events (startup, shutdown)
- **WARNING**: Security warnings (default JWT secret, deprecated features)
- **ERROR**: Unhandled exceptions, database errors

### Sample Production Log

```json
{
  "timestamp": "2026-01-05T10:30:00Z",
  "logger": "app.main",
  "level": "INFO",
  "message": "Starting DocAssist Practice Manager API..."
}
```

---

## 6. Global Exception Handler ✅

### Implementation

**File:** `backend/app/main.py`

Catches all unhandled exceptions and prevents information leakage:

### Production Behavior

- **No Stack Traces**: Never exposed to clients
- **Safe Error Messages**: Generic error message returned
- **Request ID**: Unique ID for error tracking
- **Logging**: Full exception logged server-side

### Response Format

**Production:**
```json
{
  "detail": "An internal server error occurred. Please contact support.",
  "request_id": 140234567890
}
```

**Development:**
```json
{
  "detail": "division by zero",
  "type": "ZeroDivisionError",
  "request_id": 140234567890
}
```

---

## 7. Docker Security ✅

### Implementation

**File:** `docker-compose.yml`

Environment variables replace hardcoded credentials:

### Changed From:
```yaml
POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/docassist
DEBUG: "true"
JWT_SECRET_KEY: dev-secret-key-change-in-production
```

### Changed To:
```yaml
POSTGRES_USER: ${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
DEBUG: ${DEBUG:-false}
JWT_SECRET_KEY: ${JWT_SECRET_KEY:-dev-secret-key-change-in-production}
```

### Configuration Files

- `.env.docker.example`: Template for Docker environment variables
- `backend/.env.example`: Template for backend environment variables

---

## 8. API Documentation Security ✅

### Implementation

**File:** `backend/app/main.py`

Swagger UI and ReDoc are disabled in production:

```python
docs_url="/docs" if settings.debug else None,
redoc_url="/redoc" if settings.debug else None,
```

**Rationale:** Prevents API schema exposure in production.

---

## Security Checklist for Production Deployment

Before deploying to production, ensure:

- [ ] `JWT_SECRET_KEY` is set to a unique 32+ character secret
- [ ] `POSTGRES_PASSWORD` is changed from default
- [ ] `DEBUG=false` is set
- [ ] `ENVIRONMENT=production` is set
- [ ] CORS origins are whitelisted (no wildcards)
- [ ] HTTPS is enabled (SSL/TLS certificates configured)
- [ ] Rate limiting is tested and configured appropriately
- [ ] Database backups are configured
- [ ] Log aggregation is set up (optional but recommended)
- [ ] Firewall rules restrict database access to backend only
- [ ] API documentation is disabled (`/docs` and `/redoc` return 404)

---

## Environment Variables Reference

### Critical Security Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | ✅ | ⚠️ | JWT signing secret (min 32 chars) |
| `POSTGRES_PASSWORD` | ✅ | ⚠️ | Database password |
| `ENVIRONMENT` | ✅ | `development` | Environment mode |
| `DEBUG` | ⚠️ | `false` | Debug mode (disable in prod) |
| `CORS_ORIGINS` | ✅ | `[]` | Allowed CORS origins (JSON array) |
| `RATE_LIMIT_PER_MINUTE` | ⚠️ | `60` | Global rate limit |

---

## Threat Model

### Threats Mitigated

| Threat | Mitigation |
|--------|------------|
| **Brute Force Attacks** | Rate limiting on auth endpoints |
| **JWT Compromise** | Strong secret validation, short token expiry |
| **SQL Injection** | SQLAlchemy ORM with parameterized queries |
| **XSS** | CSP headers, input validation |
| **CSRF** | SameSite cookies, CORS whitelisting |
| **Clickjacking** | X-Frame-Options: DENY |
| **Information Leakage** | Safe error messages, no stack traces in prod |
| **MIME Sniffing** | X-Content-Type-Options: nosniff |
| **Man-in-the-Middle** | HSTS (force HTTPS) |

### Threats NOT Mitigated (Requires Additional Setup)

| Threat | Required Action |
|--------|-----------------|
| **DDoS Attacks** | Use CloudFlare, AWS Shield, or similar |
| **Database Compromise** | Enable database encryption at rest |
| **Log Tampering** | Use immutable log storage (AWS CloudWatch, etc.) |
| **Insider Threats** | Role-based access control (RBAC) - already implemented |
| **Physical Security** | Secure server hosting environment |

---

## Incident Response

If a security incident occurs:

1. **Isolate**: Disconnect affected systems from network
2. **Assess**: Review logs for unauthorized access
3. **Contain**: Revoke compromised tokens, rotate secrets
4. **Notify**: Inform affected users (if patient data compromised)
5. **Remediate**: Patch vulnerabilities, restore from backups
6. **Document**: Create incident report for compliance

---

## Compliance Notes

### Indian Healthcare Data Protection

- **Patient Data**: Stored locally (offline-first), no cloud lock-in
- **Consent**: Required for appointment booking (implicit via OTP)
- **Data Portability**: Export features (PDF/Excel) enable patient data transfer
- **Audit Logs**: All sensitive actions logged with timestamps

### HIPAA Considerations (if applicable)

- **Encryption in Transit**: HTTPS enforced via HSTS
- **Encryption at Rest**: Database encryption recommended (not enforced)
- **Access Control**: RBAC implemented (doctor, staff, admin roles)
- **Audit Trails**: Comprehensive logging of all data access

---

## Contact

For security concerns or vulnerability reports:

**Email:** security@docassist.example.com
**PGP Key:** [Not yet configured]

**Please DO NOT open public GitHub issues for security vulnerabilities.**

---

*Last Updated: 2026-01-05*
*Security Version: 1.0*
