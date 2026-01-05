# Load Testing Quick Start Guide

## Installation (5 minutes)

### Step 1: Install Dependencies

```bash
cd /home/user/appointment_system/backend
pip install -r requirements.txt
```

This installs:
- `locust>=2.20.0` - Load testing framework
- `Faker>=22.0.0` - Test data generation

### Step 2: Configure Environment

```bash
cd load_tests
cp .env.example .env
```

Edit `.env` with your test configuration:

```bash
# Minimum required for dev testing
TEST_ENV=dev
DEV_HOST=http://localhost:8000
DEV_ADMIN_EMAIL=admin@clinic.com
DEV_ADMIN_PASSWORD=admin123

# Optional: Get these IDs from your database
DEV_CLINIC_ID=<your-clinic-uuid>
DEV_DOCTOR_ID=<your-doctor-uuid>
DEV_PATIENT_ID=<your-patient-uuid>
DEV_SERVICE_ID=<your-service-uuid>
```

### Step 3: Start Backend

```bash
cd /home/user/appointment_system/backend
uvicorn app.main:app --reload
```

Wait for: `INFO: Application startup complete.`

## Running Your First Test (1 minute)

### Quick Test - 50 Users

```bash
cd load_tests
./run_tests.sh mixed 50 dev
```

Output:
```
═══════════════════════════════════════════════════
  DocAssist Practice Manager - Load Test
═══════════════════════════════════════════════════

Test Configuration:
  Test Type:     mixed
  Users:         50
  Spawn Rate:    10 users/sec
  Run Time:      5m
  Environment:   dev

✓ Backend is running
Starting load test...

[Test runs for 5 minutes...]

═══════════════════════════════════════════════════
  Load Test Complete!
═══════════════════════════════════════════════════

PERFORMANCE SUMMARY
═══════════════════════════════════════════════════
Total Requests:      15,230
Total Failures:      5
Avg Response Time:   142.34ms
Requests/Second:     254.17
Error Rate:          0.0328%
═══════════════════════════════════════════════════

PERFORMANCE TARGETS:
  Response Time: ✓ PASS
  RPS:           ⚠ WARNING
  Error Rate:    ✓ PASS
```

### View Results

```bash
# HTML Report
open reports/<timestamp>_mixed_50users/report.html

# Summary Report
open reports/<timestamp>_mixed_50users/summary.html
```

## Common Test Scenarios

### 1. Baseline Performance (100 users)

```bash
./run_tests.sh mixed 100 dev
```

### 2. Booking Flow Test

```bash
./run_tests.sh booking 50 dev
```

### 3. Search Performance

```bash
./run_tests.sh search 200 dev
```

### 4. Stress Test (500 users)

```bash
./run_tests.sh mixed 500 dev 50 10m
```

### 5. Long Stability Test (1 hour)

```bash
./run_tests.sh mixed 200 dev 20 1h
```

## Interactive Mode with Web UI

```bash
locust -f locustfile.py --host http://localhost:8000
```

Then open: http://localhost:8089

- Set number of users: `100`
- Set spawn rate: `10`
- Click **Start**

## Understanding Results

### Key Metrics

| Metric | Good | Warning | Bad |
|--------|------|---------|-----|
| **p95 Response Time** | < 200ms | 200-500ms | > 500ms |
| **RPS** | > 500 | 400-500 | < 400 |
| **Error Rate** | < 0.1% | 0.1-1% | > 1% |

### Report Files

```
reports/20260105_143022_mixed_100users/
├── report.html          ← Locust HTML report
├── summary.html         ← Performance targets check
├── summary.json         ← Machine-readable metrics
├── stats_stats.csv      ← Per-endpoint stats
├── stats_failures.csv   ← Error details
└── locust.log          ← Execution log
```

## Troubleshooting

### Issue: Backend Not Running

```
✗ Backend is not accessible at http://localhost:8000
```

**Fix:**
```bash
cd /home/user/appointment_system/backend
uvicorn app.main:app --reload
```

### Issue: Authentication Failures

```
401 Unauthorized errors
```

**Fix:** Check credentials in `.env`:
```bash
DEV_ADMIN_EMAIL=admin@clinic.com
DEV_ADMIN_PASSWORD=admin123
```

### Issue: 404 Not Found for Test Entities

```
404 errors for patient, doctor, clinic IDs
```

**Fix:** Update `.env` with valid UUIDs from database:
```bash
# Get IDs from database
psql -d clinic_db -c "SELECT id, name FROM doctors LIMIT 1;"
psql -d clinic_db -c "SELECT id, full_name FROM patients LIMIT 1;"
```

### Issue: Low RPS

**Symptoms:** RPS < 500

**Potential causes:**
- Synchronous blocking operations
- Database connection pool exhaustion
- Missing indexes

**Solutions:**
```bash
# Check logs
tail -f backend/logs/app.log

# Monitor database
docker stats backend-db

# Profile slow queries
EXPLAIN ANALYZE SELECT ...
```

## Next Steps

1. **Read Full Documentation:** `/docs/LOAD_TESTING.md`
2. **Compare Against Baseline:** `python compare_baseline.py reports/latest dev.mixed_100_users`
3. **Create Custom Scenarios:** Edit `scenarios/my_scenario.py`
4. **CI/CD Integration:** See GitHub Actions examples in docs

## Performance Targets

| Environment | Users | RPS | p95 | Error Rate |
|-------------|-------|-----|-----|------------|
| **Dev** | 100 | 500+ | < 200ms | < 0.1% |
| **Staging** | 500 | 1000+ | < 200ms | < 0.1% |
| **Prod** | 1000+ | 2000+ | < 200ms | < 0.1% |

## Support

- Documentation: `/docs/LOAD_TESTING.md`
- Locust Docs: https://docs.locust.io/
- Issues: Create GitHub issue with logs

---

**Version:** 1.0.0
**Last Updated:** 2026-01-05
