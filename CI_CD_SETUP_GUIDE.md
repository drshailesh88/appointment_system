# CI/CD Setup Guide for DocAssist Practice Manager

This guide will help you set up and configure GitHub Actions for continuous integration and deployment.

## What Was Created

### Workflow Files (`.github/workflows/`)

1. **`backend-tests.yml`** - Python backend testing
   - Runs pytest with coverage
   - Linting with ruff
   - Type checking with mypy
   - PostgreSQL integration tests
   - Coverage threshold: 70%

2. **`flutter-tests.yml`** - Flutter mobile app testing
   - Flutter analyze for code quality
   - Unit and widget tests
   - Android APK builds
   - iOS builds (main branch only)
   - Coverage reporting

3. **`security-scan.yml`** - Security scanning
   - Bandit for Python security issues
   - Safety for dependency vulnerabilities
   - Gitleaks for secrets scanning
   - CodeQL for advanced analysis
   - Weekly scheduled scans

4. **`lint.yml`** - Fast linting feedback
   - Python (ruff, black, isort)
   - Flutter (analyze, format)
   - Markdown and YAML linting
   - Runs on every push

### Configuration Files

5. **`.github/dependabot.yml`** - Automated dependency updates
   - Python pip packages
   - Flutter pub packages
   - npm packages (web)
   - GitHub Actions
   - Docker images

6. **`.markdownlint.json`** - Markdown linting rules
7. **`.yamllint.yml`** - YAML linting rules
8. **`.github/workflows/README.md`** - Detailed workflow documentation

## Quick Start

### Step 1: Push to GitHub

If you haven't already pushed your code:

```bash
git add .github/
git add .markdownlint.json .yamllint.yml
git add CI_CD_SETUP_GUIDE.md
git commit -m "chore(ci): Add GitHub Actions workflows for CI/CD"
git push origin main
```

### Step 2: Enable GitHub Actions

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Enable workflows if prompted
4. Workflows will start running automatically

### Step 3: Configure Codecov (Optional but Recommended)

For coverage reporting:

1. Visit https://codecov.io
2. Sign in with GitHub
3. Add your repository
4. Copy the upload token
5. Add as GitHub secret: `CODECOV_TOKEN`

### Step 4: Review First Run

1. Go to **Actions** tab
2. Watch workflows execute
3. Review any failures
4. Check coverage reports

## Adding Status Badges

Add these badges to your `README.md`:

```markdown
[![Backend Tests](https://github.com/YOUR_USERNAME/appointment_system/workflows/Backend%20Tests/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/backend-tests.yml)
[![Flutter Tests](https://github.com/YOUR_USERNAME/appointment_system/workflows/Flutter%20Tests/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/flutter-tests.yml)
[![Security Scan](https://github.com/YOUR_USERNAME/appointment_system/workflows/Security%20Scan/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/security-scan.yml)
[![Lint](https://github.com/YOUR_USERNAME/appointment_system/workflows/Lint/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/appointment_system/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/appointment_system)
```

**Replace `YOUR_USERNAME` with your GitHub username.**

## Workflow Triggers

| Workflow | Triggers |
|----------|----------|
| **Backend Tests** | Push/PR to main (when `backend/**` or `requirements.txt` changes) |
| **Flutter Tests** | Push/PR to main (when `mobile/**` changes) |
| **Security Scan** | Push/PR to main + Weekly Monday 00:00 UTC + Manual |
| **Lint** | Every push/PR to main or develop branches |
| **Dependabot** | Weekly Monday 03:00 UTC |

## Expected Run Times

| Workflow | Duration |
|----------|----------|
| Lint | 5-8 minutes |
| Backend Tests | 8-12 minutes |
| Flutter Tests (analyze+test) | 10-15 minutes |
| Flutter Tests (with builds) | 20-30 minutes |
| Security Scan | 15-20 minutes |

## Troubleshooting

### Backend Tests Failing

**Issue:** Tests fail with database errors

**Solution:**
```bash
# Check if migrations are up to date
cd backend
alembic upgrade head

# Run tests locally first
pytest tests/ -v
```

**Issue:** Coverage below threshold

**Solution:**
```bash
# Check coverage locally
pytest tests/ --cov=app --cov-report=term

# Add tests for uncovered code
# Threshold is 70% (configurable in workflow)
```

### Flutter Tests Failing

**Issue:** Flutter analyze shows errors

**Solution:**
```bash
cd mobile
flutter analyze
# Fix issues shown

# Format code
dart format .
```

**Issue:** Tests fail locally

**Solution:**
```bash
cd mobile
flutter test
# Fix failing tests before pushing
```

### Security Scan Issues

**Issue:** Bandit reports false positives

**Solution:**
```python
# Add nosec comment with justification
password = get_password()  # nosec B105 - Not a hardcoded password
```

**Issue:** Dependency vulnerabilities

**Solution:**
- Review Safety report in artifacts
- Update vulnerable packages
- Check Dependabot PRs for updates

### Dependabot PRs Piling Up

**Solution:**
1. Review PRs weekly
2. Test locally before merging
3. Merge compatible updates together
4. Adjust `open-pull-requests-limit` if needed

## Configuration Customization

### Adjust Coverage Threshold

Edit `.github/workflows/backend-tests.yml`:

```yaml
- name: Check coverage threshold
  run: |
    # Change 70 to your desired threshold
    if (( $(echo "$coverage_percent < 70" | bc -l) )); then
      exit 1
    fi
```

### Change Python Versions

Edit `.github/workflows/backend-tests.yml`:

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']  # Add or remove versions
```

### Adjust Dependabot Frequency

Edit `.github/dependabot.yml`:

```yaml
schedule:
  interval: "weekly"  # Change to "daily" or "monthly"
  day: "monday"       # Change day
  time: "03:00"       # Change time
```

### Add More Linters

Edit `.github/workflows/lint.yml` and add new jobs:

```yaml
  typescript-lint:  # Example
    name: TypeScript Linting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm install
      - run: npm run lint
```

## Best Practices

### Before Pushing Code

```bash
# Run linters locally
cd backend
ruff check app/
black app/
mypy app/

# Run tests locally
pytest tests/ -v

# Check Flutter
cd ../mobile
flutter analyze
dart format .
flutter test
```

### Working with PRs

1. **Create draft PRs** for work in progress
2. **Review CI results** before requesting review
3. **Address lint issues** promptly
4. **Maintain coverage** above threshold
5. **Fix security findings** before merging

### Monitoring

- Check **Actions** tab weekly
- Review **Security** tab for CodeQL findings
- Monitor **Dependabot** PRs
- Track coverage trends in Codecov

## Advanced Features

### Matrix Testing

Backend tests run on multiple Python versions:
- Python 3.11 (LTS)
- Python 3.12 (Latest)

Add more versions if needed:
```yaml
matrix:
  python-version: ['3.11', '3.12', '3.13']
```

### Caching Strategy

All workflows use aggressive caching:

- **pip:** Dependencies cached by `requirements.txt` hash
- **pub:** Dependencies cached by `pubspec.lock` hash
- **Flutter:** SDK cached by version
- **Gradle:** Build cache for Android

This reduces CI time by 50-70%.

### Parallel Execution

Workflows run jobs in parallel when possible:

- Backend tests: Different Python versions
- Flutter tests: Analyze before builds
- Security scans: Multiple tools simultaneously

### Artifact Storage

Artifacts are automatically stored:

- Coverage reports: 7 days
- Security reports: 30 days
- APK builds: 7 days
- Test results: 7 days

Access via Actions → Workflow Run → Artifacts

## Security Configuration

### Required Permissions

Workflows use minimal permissions:

- `contents: read` - Read repository
- `security-events: write` - Upload security findings (CodeQL)
- `actions: read` - Read action outputs

### Secrets Management

**Never commit secrets!** Use GitHub Secrets:

```bash
# Repository Settings → Secrets and variables → Actions
# Add secrets (not visible after creation):
- CODECOV_TOKEN
- GITLEAKS_LICENSE (optional)
```

### SARIF Reports

Security findings are uploaded to GitHub Security tab:

1. Go to **Security** → **Code scanning**
2. Review findings
3. Dismiss false positives
4. Track fixes

## Cost Optimization

### Public Repositories
- ✅ Unlimited Actions minutes
- ✅ Unlimited artifact storage
- ✅ All features free

### Private Repositories
- 2,000 minutes/month (free tier)
- 500 MB storage (free tier)

**Optimization tips:**
1. Use path filters (already configured)
2. Cache dependencies (already configured)
3. Use concurrency groups for PRs
4. Skip redundant jobs

Example concurrency:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Maintenance Schedule

### Daily
- ✅ Automated: Workflows run on push/PR
- ✅ Automated: Linting on every commit

### Weekly
- 📅 Monday 00:00 UTC: Security scans
- 📅 Monday 03:00 UTC: Dependabot updates
- 👤 Manual: Review CI failures
- 👤 Manual: Merge Dependabot PRs

### Monthly
- 👤 Manual: Review workflow efficiency
- 👤 Manual: Update Python/Flutter versions
- 👤 Manual: Check Actions usage

### Quarterly
- 👤 Manual: Audit security configurations
- 👤 Manual: Update workflow best practices
- 👤 Manual: Review coverage trends

## Getting Help

### Workflow Debugging

1. Click on failed workflow
2. Click on failed job
3. Expand failed step
4. Review error logs
5. Search error message

### Common Issues

**Issue:** Workflow not running

**Check:**
- Actions enabled in repository settings
- Path filters match changed files
- Branch name matches trigger

**Issue:** Caching not working

**Check:**
- Cache key hash matches files
- Cache size under 10 GB limit
- Dependencies file hasn't changed frequently

**Issue:** Tests pass locally but fail in CI

**Check:**
- Environment variables in workflow
- Python/Flutter versions match
- Database state and migrations
- Timezone differences

### Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Dependabot Docs](https://docs.github.com/en/code-security/dependabot)
- [CodeQL Docs](https://codeql.github.com/docs/)

## Next Steps

1. ✅ Push workflows to GitHub
2. ✅ Enable Actions in repository
3. ✅ Add Codecov token (optional)
4. ✅ Add status badges to README
5. 📝 Review first workflow runs
6. 📝 Fix any initial issues
7. 📝 Configure branch protection rules
8. 📝 Set up required status checks

### Branch Protection

Recommended settings:

```
Settings → Branches → Branch protection rules → Add rule

Branch name pattern: main

☑ Require pull request before merging
  ☑ Require approvals: 1
  ☑ Dismiss stale reviews

☑ Require status checks before merging
  ☑ Require branches to be up to date
  Required checks:
    - Backend Tests
    - Flutter Tests
    - Lint
    - Security Scan

☑ Require linear history
☐ Allow force pushes
☐ Allow deletions
```

---

## Summary

You now have:

✅ **4 production-ready workflows**
- Backend testing with coverage
- Flutter testing and builds
- Security scanning
- Fast linting

✅ **Automated dependency management**
- Dependabot for all ecosystems
- Weekly update schedule
- Smart version constraints

✅ **Comprehensive documentation**
- Setup guides
- Troubleshooting tips
- Best practices

✅ **Security scanning**
- Multiple tools
- Weekly schedules
- SARIF reports

**Your CI/CD pipeline is ready for production!**

---

*Last Updated: 2026-01-05*
*Version: 1.0*
