# GitHub Actions Workflows

This directory contains CI/CD workflows for DocAssist Practice Manager.

## Status Badges

Add these badges to your main README.md:

```markdown
[![Backend Tests](https://github.com/drshailesh88/appointment_system/workflows/Backend%20Tests/badge.svg)](https://github.com/drshailesh88/appointment_system/actions/workflows/backend-tests.yml)
[![Flutter Tests](https://github.com/drshailesh88/appointment_system/workflows/Flutter%20Tests/badge.svg)](https://github.com/drshailesh88/appointment_system/actions/workflows/flutter-tests.yml)
[![Security Scan](https://github.com/drshailesh88/appointment_system/workflows/Security%20Scan/badge.svg)](https://github.com/drshailesh88/appointment_system/actions/workflows/security-scan.yml)
[![codecov](https://codecov.io/gh/drshailesh88/appointment_system/branch/main/graph/badge.svg)](https://codecov.io/gh/drshailesh88/appointment_system)
```

**Note:** Replace `drshailesh88/appointment_system` with your actual repository path.

## Workflows Overview

### 1. Backend Tests (`backend-tests.yml`)

**Triggers:**
- Push to `main` branch (when backend files change)
- Pull requests to `main` branch (when backend files change)

**What it does:**
- Tests on Python 3.11 and 3.12
- Sets up PostgreSQL test database
- Installs system dependencies (ffmpeg, tesseract, etc.)
- Runs linting (ruff) and type checking (mypy)
- Executes pytest with coverage
- Uploads coverage to Codecov
- Adds coverage comments to PRs
- Fails if coverage is below 70%

**Duration:** ~8-12 minutes

**Caching:**
- pip packages
- Python dependencies

### 2. Flutter Tests (`flutter-tests.yml`)

**Triggers:**
- Push to `main` branch (when mobile files change)
- Pull requests to `main` branch (when mobile files change)

**What it does:**
- Sets up Flutter stable channel
- Runs `flutter analyze` for code quality
- Checks code formatting
- Executes unit and widget tests
- Generates coverage reports
- Builds debug APK (Android)
- Builds debug iOS app (macOS runner, main branch only)
- Uploads coverage to Codecov

**Duration:** ~10-15 minutes (analyze + test), ~25 minutes (APK build)

**Caching:**
- Flutter SDK
- pub dependencies
- Gradle cache

### 3. Security Scan (`security-scan.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main` branch
- Weekly schedule (Mondays at 00:00 UTC)
- Manual workflow dispatch

**What it does:**
- **Bandit:** Scans Python code for security issues
- **Safety:** Checks Python dependencies for known vulnerabilities
- **Gitleaks:** Scans for leaked secrets in git history
- **CodeQL:** Advanced code analysis for security vulnerabilities
- Uploads results to GitHub Security tab
- Creates SARIF reports

**Duration:** ~15-20 minutes

**Security Levels:**
- Bandit: Medium severity and above
- CodeQL: Security-extended queries
- Gitleaks: All secrets

### 4. Dependabot (`dependabot.yml`)

**Updates:**
- Python pip packages (root and backend)
- Flutter pub packages (mobile)
- npm packages (web portal)
- GitHub Actions versions
- Docker base images

**Schedule:** Weekly on Mondays at 03:00 UTC

**Limits:**
- 5 PRs max for pip/pub/npm
- 3 PRs max for GitHub Actions/Docker

**Ignores:**
- Major version updates for critical packages (FastAPI, SQLAlchemy, React, Flutter)
- Flutter SDK updates (manual control)

## Required GitHub Secrets

To enable all features, add these secrets to your repository:

### Optional (for enhanced features)

```bash
CODECOV_TOKEN          # For coverage reporting (optional but recommended)
GITLEAKS_LICENSE       # For Gitleaks Pro (optional)
```

### How to add secrets:

1. Go to your repository settings
2. Navigate to Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with its value

## Workflow Configuration

### Timeouts

All workflows have timeout limits to prevent runaway jobs:

- Backend Tests: 15 minutes
- Flutter Analyze & Test: 20 minutes
- Flutter APK Build: 25 minutes
- Flutter iOS Build: 30 minutes
- Security Scans: 10-20 minutes

### Path Filtering

Workflows only run when relevant files change:

- **Backend Tests:** Triggered by changes to `backend/**` or `requirements.txt`
- **Flutter Tests:** Triggered by changes to `mobile/**`

This saves CI minutes and reduces unnecessary runs.

### Parallel Jobs

- Backend tests run in parallel for Python 3.11 and 3.12
- Flutter analyze/test runs before builds
- Security scans run multiple tools in parallel

## Coverage Requirements

### Backend
- Minimum threshold: 70% (warning if below)
- Target: 80%+ (green in PR comments)
- Reports: XML, HTML, Terminal

### Flutter
- No hard threshold (informational)
- LCOV reports generated
- HTML reports available as artifacts

## Artifact Retention

All artifacts are retained for 7 days (30 days for security reports):

- Coverage reports (XML + HTML)
- Test results
- APK builds
- Security scan reports

## Troubleshooting

### Backend tests failing?

1. Check PostgreSQL connection
2. Verify all system dependencies are installed
3. Review migration issues
4. Check environment variables in `.env.test`

### Flutter tests failing?

1. Ensure Flutter version matches (3.24.5)
2. Check for missing dependencies in `pubspec.yaml`
3. Run `flutter pub get` locally
4. Verify tests pass locally first

### Security scan alerts?

1. Review SARIF reports in GitHub Security tab
2. Check Bandit report artifact for details
3. Use `# nosec` comment for false positives (with justification)
4. Update vulnerable dependencies via Dependabot PRs

### Codecov not working?

1. Verify `CODECOV_TOKEN` secret is set
2. Check Codecov dashboard for repository setup
3. Ensure coverage files are generated correctly
4. Review Codecov upload step logs

## Performance Optimization

### Caching Strategy

All workflows use aggressive caching:

- **pip:** `~/.cache/pip` + `requirements.txt` hash
- **pub:** `~/.pub-cache` + `pubspec.lock` hash
- **Flutter:** SDK cached by version + channel
- **Gradle:** Java/Gradle cache for Android builds

### Best Practices

1. **Keep dependencies up to date** via Dependabot
2. **Run tests locally** before pushing
3. **Use draft PRs** for work-in-progress
4. **Review coverage reports** in PR comments
5. **Address security findings** promptly

## Monitoring

### GitHub Actions Usage

Monitor your CI/CD usage:
1. Go to repository Settings → Billing
2. Check Actions minutes used
3. Review storage for artifacts

### Free Tier Limits (Public Repos)

- ✅ Unlimited Actions minutes
- ✅ Unlimited storage
- ✅ All features enabled

### Private Repos (if applicable)

- 2,000 Actions minutes/month (free tier)
- 500 MB storage (free tier)
- Consider workflow optimization

## Maintenance

### Weekly Tasks

- Review Dependabot PRs
- Check security scan results
- Monitor coverage trends

### Monthly Tasks

- Review Actions usage
- Clean up old artifacts (automatic after retention period)
- Update workflow versions

### Quarterly Tasks

- Review and update Python/Flutter versions
- Audit security scan configurations
- Optimize caching strategies

## Contributing

When modifying workflows:

1. Test changes in a fork first
2. Use `act` for local workflow testing (optional)
3. Document changes in this README
4. Update timeout limits if needed
5. Keep caching strategies efficient

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Codecov Documentation](https://docs.codecov.com/)

---

**Last Updated:** 2026-01-05
**Maintained by:** DocAssist Development Team
