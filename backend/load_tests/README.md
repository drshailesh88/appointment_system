# DocAssist Practice Manager - Load Tests

Load testing infrastructure for performance validation and stress testing.

## Quick Start

### 1. Setup

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cd load_tests
cp .env.example .env
# Edit .env with your test credentials and IDs
```

### 2. Run a Test

```bash
./run_tests.sh mixed 100 dev
```

This runs a mixed load test with 100 concurrent users against the dev environment.

## Available Test Scenarios

| Test Type | Description | Command |
|-----------|-------------|---------|
| **mixed** | Realistic clinic traffic (40% reception, 30% doctor, 20% analytics, 10% mgmt) | `./run_tests.sh mixed 100 dev` |
| **booking** | Sequential booking workflow | `./run_tests.sh booking 50 dev` |
| **search** | Search-intensive operations | `./run_tests.sh search 200 dev` |
| **receptionist** | Front desk operations | `./run_tests.sh receptionist 100 dev` |
| **doctor** | Clinical workflows | `./run_tests.sh doctor 50 dev` |
| **analytics** | Reports and dashboards | `./run_tests.sh analytics 30 dev` |

## Usage

```bash
./run_tests.sh [test_type] [users] [environment] [spawn_rate] [run_time]
```

**Parameters:**
- `test_type`: Test scenario (see table above)
- `users`: Number of concurrent users (default: 100)
- `environment`: dev | staging | prod (default: dev)
- `spawn_rate`: Users spawned per second (default: 10)
- `run_time`: Test duration, e.g., 5m, 1h (default: 5m)

**Examples:**

```bash
# Baseline test - 100 users for 5 minutes
./run_tests.sh mixed 100 dev

# Stress test - 500 users for 10 minutes
./run_tests.sh mixed 500 dev 50 10m

# Search performance - 200 users
./run_tests.sh search 200 dev

# Long-running stability - 200 users for 1 hour
./run_tests.sh mixed 200 dev 20 1h
```

## Interactive Mode (with Web UI)

```bash
locust -f locustfile.py --host http://localhost:8000
```

Then open: http://localhost:8089

## Performance Targets

| Metric | Target |
|--------|--------|
| **Response Time (p95)** | < 200ms |
| **Requests/Second** | > 500 |
| **Concurrent Users** | 1000+ |
| **Error Rate** | < 0.1% |

## Reports

After each test, reports are generated in `reports/`:

- `report.html` - Locust HTML report with charts
- `summary.html` - Performance summary with target checks
- `summary.json` - Machine-readable metrics for CI/CD
- `stats_stats.csv` - Detailed per-endpoint statistics
- `locust.log` - Test execution log

## Test Structure

```
load_tests/
├── config.py                 # Environment configuration
├── locustfile.py            # Main test file
├── scenarios/
│   ├── booking_flow.py      # Sequential booking workflow
│   ├── search_heavy.py      # Search-intensive operations
│   └── mixed_load.py        # Realistic mixed traffic
├── run_tests.sh             # Test runner
├── generate_report.py       # Report generator
└── reports/                 # Generated reports
```

## Troubleshooting

### Backend Not Running

```
✗ Backend is not accessible at http://localhost:8000
```

**Solution:** Start the backend first:
```bash
cd backend
uvicorn app.main:app --reload
```

### Missing Test Data

If you get 404 errors for test entities:

**Solution:** Update `.env` with valid UUIDs:
```bash
# Get IDs from database or seed data
python scripts/seed_test_data.py
```

### High Error Rates

Check logs:
```bash
tail -f backend/logs/app.log
```

Monitor database:
```bash
docker stats backend-db
```

## CI/CD Integration

See `/docs/LOAD_TESTING.md` for GitHub Actions integration examples.

## Documentation

Full documentation: `/docs/LOAD_TESTING.md`

## Support

For issues or questions, refer to:
- [Load Testing Guide](../docs/LOAD_TESTING.md)
- [Locust Documentation](https://docs.locust.io/)
- Project Issues: https://github.com/yourusername/appointment_system/issues
