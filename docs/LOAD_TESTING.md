# Load Testing Guide - DocAssist Practice Manager

This guide covers load testing infrastructure and best practices for ensuring DocAssist Practice Manager meets performance targets.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Scenarios](#test-scenarios)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Performance Targets](#performance-targets)
- [Analyzing Results](#analyzing-results)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

---

## Overview

The load testing infrastructure uses **Locust**, a modern Python-based load testing framework. It simulates realistic clinic usage patterns to ensure the system can handle expected production traffic.

### Architecture

```
backend/load_tests/
├── config.py                      # Environment configuration
├── locustfile.py                  # Main test file with user classes
├── scenarios/
│   ├── booking_flow.py           # Sequential booking workflow
│   ├── search_heavy.py           # Search-intensive operations
│   └── mixed_load.py             # Realistic mixed traffic
├── run_tests.sh                   # Test runner script
├── generate_report.py             # Report generator
└── reports/                       # Generated test reports
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in `backend/load_tests/`:

```bash
# Development
DEV_HOST=http://localhost:8000
DEV_ADMIN_EMAIL=admin@clinic.com
DEV_ADMIN_PASSWORD=admin123
DEV_CLINIC_ID=your-clinic-uuid
DEV_DOCTOR_ID=your-doctor-uuid
DEV_PATIENT_ID=your-patient-uuid
DEV_SERVICE_ID=your-service-uuid

# Staging (optional)
STAGING_HOST=https://staging.docassist.com
STAGING_ADMIN_EMAIL=loadtest@staging.com
STAGING_ADMIN_PASSWORD=secure_password

# Production (optional - use with caution!)
PROD_HOST=https://api.docassist.com
PROD_ADMIN_EMAIL=loadtest@prod.com
PROD_ADMIN_PASSWORD=very_secure_password
```

### 3. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload
```

### 4. Run a Quick Test

```bash
cd load_tests
./run_tests.sh mixed 50 dev
```

This runs a mixed load test with 50 concurrent users against the development environment.

---

## Test Scenarios

### 1. Mixed Load (Recommended for Baseline)

**File:** `scenarios/mixed_load.py`

Simulates realistic clinic traffic:
- 40% Reception operations (search, booking, check-in)
- 30% Doctor operations (schedule viewing, patient details)
- 20% Analytics operations (dashboards, reports)
- 10% Management operations (staff, settings)

**Run:**
```bash
./run_tests.sh mixed 100 dev
```

### 2. Booking Flow (Sequential Workflow)

**File:** `scenarios/booking_flow.py`

Tests complete appointment booking workflow:
1. Search for patient
2. Check slot availability
3. Book appointment
4. Verify booking
5. View today's appointments

**Run:**
```bash
./run_tests.sh booking 50 dev
```

### 3. Search Heavy (Stress Test)

**File:** `scenarios/search_heavy.py`

Tests search-intensive operations:
- RAG semantic search (most intensive)
- Patient search by name/phone
- Appointment search
- Complex analytics queries

**Run:**
```bash
./run_tests.sh search 200 dev
```

### 4. Individual User Classes

**File:** `locustfile.py`

- **ReceptionistUser**: Front desk operations
- **DoctorUser**: Clinical workflows
- **AnalyticsUser**: Reporting and analytics
- **SearchHeavyUser**: Search operations

**Run:**
```bash
./run_tests.sh receptionist 100 dev
./run_tests.sh doctor 50 dev
./run_tests.sh analytics 30 dev
```

---

## Configuration

### Environment-Based Settings

Edit `config.py` to customize performance targets:

```python
@dataclass
class LoadTestConfig:
    # Performance targets
    target_response_time_ms: int = 200  # p95
    target_rps: int = 500
    target_concurrent_users: int = 1000
    target_error_rate: float = 0.001  # 0.1%

    # Test duration
    spawn_rate: int = 10  # users per second
    run_time: str = "5m"
```

### Test Data

The tests use **Faker** library to generate realistic Indian data:
- Names (Indian locale)
- Phone numbers (+91 format)
- Addresses (Indian cities)
- Medical terms

---

## Running Tests

### Basic Usage

```bash
./run_tests.sh [test_type] [users] [environment] [spawn_rate] [run_time]
```

**Parameters:**
- `test_type`: mixed | booking | search | receptionist | doctor | analytics
- `users`: Number of concurrent users (default: 100)
- `environment`: dev | staging | prod (default: dev)
- `spawn_rate`: Users spawned per second (default: 10)
- `run_time`: Test duration (default: 5m)

### Examples

#### Baseline Performance Test
```bash
./run_tests.sh mixed 100 dev
```

#### Stress Test (High Load)
```bash
./run_tests.sh mixed 500 dev 50 10m
```

#### Search Performance Test
```bash
./run_tests.sh search 200 dev
```

#### Long-Running Stability Test
```bash
./run_tests.sh mixed 200 dev 20 1h
```

### Interactive Mode (with Web UI)

```bash
cd load_tests
locust -f locustfile.py --host http://localhost:8000
```

Then open: http://localhost:8089

### Headless Mode (CI/CD)

```bash
locust -f locustfile.py \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --host http://localhost:8000 \
    --headless \
    --html reports/report.html \
    --csv reports/stats
```

---

## Performance Targets

### Production Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Response Time (p95)** | < 200ms | Fast UI responsiveness |
| **Requests/Second** | > 500 | Handle 100+ concurrent clinics |
| **Concurrent Users** | 1000+ | Peak load capacity |
| **Error Rate** | < 0.1% | High reliability |
| **Uptime** | 99.9% | 8.76 hours downtime/year |

### Endpoint-Specific Targets

| Endpoint | Target (p95) | Priority |
|----------|--------------|----------|
| `/api/v1/appointments/today` | < 100ms | High |
| `/api/v1/patients/search` | < 150ms | High |
| `/api/v1/search/rag` | < 500ms | Medium |
| `/api/v1/analytics/dashboard` | < 1000ms | Low |
| `/api/v1/appointments/` (POST) | < 200ms | High |

### Scaling Milestones

| Phase | Clinics | Concurrent Users | Doctors | Daily Appointments |
|-------|---------|------------------|---------|-------------------|
| **Phase 1** | 10 | 100 | 20 | 500 |
| **Phase 2** | 50 | 500 | 100 | 2,500 |
| **Phase 3** | 100 | 1,000 | 200 | 5,000 |
| **Phase 4** | 500 | 5,000 | 1,000 | 25,000 |

---

## Analyzing Results

### Generated Reports

After each test run, the following reports are generated:

1. **HTML Report** (`report.html`)
   - Request statistics
   - Response time charts
   - RPS graphs
   - Error summary

2. **Summary Report** (`summary.html`)
   - Performance targets status
   - Endpoint performance breakdown
   - Slow endpoint warnings
   - Failure analysis

3. **CSV Stats** (`stats_stats.csv`)
   - Detailed per-endpoint metrics
   - Response time percentiles
   - Request counts

4. **JSON Summary** (`summary.json`)
   - Machine-readable metrics
   - For CI/CD integration

### Key Metrics to Monitor

#### 1. Response Time

```
✓ GOOD:    p95 < 200ms
⚠ WARNING: p95 200-500ms
✗ BAD:     p95 > 500ms
```

#### 2. Error Rate

```
✓ GOOD:    < 0.1%
⚠ WARNING: 0.1-1%
✗ BAD:     > 1%
```

#### 3. Requests Per Second

```
✓ GOOD:    > target RPS
⚠ WARNING: 80-100% of target
✗ BAD:     < 80% of target
```

### Sample Report Output

```
═══════════════════════════════════════════════════
PERFORMANCE SUMMARY
═══════════════════════════════════════════════════
Total Requests:      45,230
Total Failures:      12
Avg Response Time:   142.34ms
Requests/Second:     754.17
Error Rate:          0.0265%
═══════════════════════════════════════════════════

PERFORMANCE TARGETS:
  Response Time: ✓ PASS
  RPS:           ✓ PASS
  Error Rate:    ✓ PASS
```

---

## Troubleshooting

### High Response Times

**Symptoms:**
- p95 > 200ms
- Slow endpoint warnings

**Potential Causes:**
1. Database query optimization needed
2. Missing database indexes
3. Synchronous blocking operations
4. External API latency (Qdrant, Ollama)

**Solutions:**
```bash
# Check database query performance
EXPLAIN ANALYZE SELECT ...

# Add missing indexes
CREATE INDEX idx_appointments_doctor_date
ON appointments(doctor_id, scheduled_start);

# Profile slow endpoints
cProfile -o profile.prof app/api/v1/appointments.py
```

### High Error Rates

**Symptoms:**
- Error rate > 0.1%
- 500 Internal Server Errors

**Potential Causes:**
1. Database connection pool exhaustion
2. Race conditions
3. Memory leaks
4. Unhandled exceptions

**Solutions:**
```bash
# Check logs
tail -f backend/logs/app.log | grep ERROR

# Monitor database connections
SELECT count(*) FROM pg_stat_activity;

# Check memory usage
docker stats backend-api
```

### Low RPS

**Symptoms:**
- RPS < target
- High CPU usage
- Thread pool exhaustion

**Potential Causes:**
1. Synchronous operations
2. GIL contention
3. CPU bottleneck
4. Network bandwidth

**Solutions:**
```bash
# Use async everywhere
async def get_appointments(...):
    result = await db.execute(...)

# Scale horizontally
docker-compose up --scale api=4

# Use gunicorn with multiple workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/load-test.yml`:

```yaml
name: Load Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

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

      - name: Start backend
        run: |
          cd backend
          uvicorn app.main:app &
          sleep 10

      - name: Run load tests
        run: |
          cd backend/load_tests
          ./run_tests.sh mixed 100 dev 10 2m

      - name: Check performance targets
        run: |
          cd backend/load_tests
          python generate_report.py reports/latest

      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: load-test-reports
          path: backend/load_tests/reports/

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const summary = fs.readFileSync(
              'backend/load_tests/reports/latest/summary.json',
              'utf8'
            );
            const data = JSON.parse(summary);

            const comment = `
            ## Load Test Results

            - Total Requests: ${data.metrics.total_requests}
            - Avg Response Time: ${data.metrics.avg_response_time_ms}ms
            - RPS: ${data.metrics.total_rps}
            - Error Rate: ${data.metrics.error_rate_percent}%

            [Full Report](link-to-artifact)
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Performance Regression Detection

Create a baseline:

```bash
./run_tests.sh mixed 100 dev
cp reports/latest/summary.json reports/baseline.json
```

Compare against baseline:

```python
import json

with open('reports/baseline.json') as f:
    baseline = json.load(f)

with open('reports/latest/summary.json') as f:
    current = json.load(f)

# Check for regression
if current['metrics']['avg_response_time_ms'] > baseline['metrics']['avg_response_time_ms'] * 1.1:
    print("⚠️ Performance regression detected!")
    exit(1)
```

---

## Best Practices

### 1. Test Data Management

- Use separate test database
- Seed consistent test data before runs
- Clean up after tests

```bash
# Before tests
python scripts/seed_test_data.py

# After tests
python scripts/cleanup_test_data.py
```

### 2. Progressive Load Testing

Start small and scale up:

```bash
# Step 1: Baseline (50 users)
./run_tests.sh mixed 50 dev

# Step 2: Normal load (100 users)
./run_tests.sh mixed 100 dev

# Step 3: Peak load (200 users)
./run_tests.sh mixed 200 dev

# Step 4: Stress test (500 users)
./run_tests.sh mixed 500 dev
```

### 3. Monitoring During Tests

```bash
# Terminal 1: Run load test
./run_tests.sh mixed 200 dev

# Terminal 2: Monitor backend
docker stats backend-api

# Terminal 3: Monitor database
watch -n 1 'psql -c "SELECT count(*) FROM pg_stat_activity"'

# Terminal 4: Monitor logs
tail -f backend/logs/app.log
```

### 4. Test Schedule

- **Daily**: Smoke test (50 users, 2 minutes)
- **Weekly**: Full test suite (100-500 users, 10 minutes)
- **Monthly**: Stress test (1000+ users, 30 minutes)
- **Before Release**: Comprehensive suite (all scenarios)

---

## Advanced Usage

### Custom Test Scenarios

Create a custom scenario in `scenarios/my_scenario.py`:

```python
from locust import HttpUser, task, between
from config import CONFIG

class MyCustomUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        response = self.client.post(
            "/api/v1/auth/login/json",
            json={
                "email": CONFIG.admin_email,
                "password": CONFIG.admin_password,
            }
        )
        self.token = response.json()["access_token"]

    @task
    def my_custom_workflow(self):
        # Your custom logic here
        self.client.get(
            "/api/v1/my-endpoint",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

Run it:

```bash
locust -f scenarios/my_scenario.py --host http://localhost:8000
```

### Distributed Load Testing

Run load tests across multiple machines:

```bash
# Master node
locust -f locustfile.py --master --expect-workers 4

# Worker nodes (on different machines)
locust -f locustfile.py --worker --master-host <master-ip>
locust -f locustfile.py --worker --master-host <master-ip>
locust -f locustfile.py --worker --master-host <master-ip>
locust -f locustfile.py --worker --master-host <master-ip>
```

---

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/load-testing)
- [API Performance Optimization](https://fastapi.tiangolo.com/advanced/performance/)

---

**Last Updated:** 2026-01-05
**Version:** 1.0
**Maintainer:** DocAssist Team
