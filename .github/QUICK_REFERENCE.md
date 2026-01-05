# CI/CD Quick Reference Card

## 🚀 Commands to Run Locally Before Pushing

### Backend (Python)
```bash
cd backend

# Linting
ruff check app/ --fix
black app/
isort app/

# Type checking
mypy app/ --ignore-missing-imports

# Tests with coverage
pytest tests/ -v --cov=app --cov-report=term
```

### Mobile (Flutter)
```bash
cd mobile

# Format code
dart format .

# Analyze
flutter analyze

# Run tests
flutter test --coverage
```

## 📊 Workflow Status

| Workflow | Trigger | Duration | Purpose |
|----------|---------|----------|---------|
| **Lint** | Every push | 5-8 min | Fast code quality checks |
| **Backend Tests** | Push to main (backend changes) | 8-12 min | Python testing + coverage |
| **Flutter Tests** | Push to main (mobile changes) | 10-30 min | Flutter testing + builds |
| **Security Scan** | Push + Weekly Mon 00:00 | 15-20 min | Security analysis |

## 🎯 Coverage Thresholds

- **Backend:** 70% minimum (configured in workflow)
- **Flutter:** No hard limit (informational)

## 🔧 Quick Fixes

### Lint Failures
```bash
# Python
ruff check --fix .
black .
isort .

# Flutter
dart format .
flutter analyze
```

### Test Failures
```bash
# Run tests locally with verbose output
pytest -v
flutter test --verbose
```

### Security Issues
```bash
# Check for security issues locally
pip install bandit
bandit -r backend/app -ll

# Check dependencies
pip install safety
safety check
```

## 📦 Dependabot PRs

Weekly automated PRs for:
- Python pip packages
- Flutter pub packages
- npm packages (web)
- GitHub Actions
- Docker images

**Review → Test Locally → Merge**

## 🎫 Status Badges

Add to your README.md:

```markdown
[![Backend Tests](https://github.com/YOUR_USERNAME/appointment_system/workflows/Backend%20Tests/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/backend-tests.yml)
[![Flutter Tests](https://github.com/YOUR_USERNAME/appointment_system/workflows/Flutter%20Tests/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/flutter-tests.yml)
[![Security Scan](https://github.com/YOUR_USERNAME/appointment_system/workflows/Security%20Scan/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/security-scan.yml)
[![Lint](https://github.com/YOUR_USERNAME/appointment_system/workflows/Lint/badge.svg)](https://github.com/YOUR_USERNAME/appointment_system/actions/workflows/lint.yml)
```

## 🔐 Required Secrets

Optional but recommended:

```
CODECOV_TOKEN - For coverage reporting
```

Add at: Repository Settings → Secrets and variables → Actions

## 📁 Artifact Downloads

Available for 7 days after workflow run:

- Coverage reports (HTML + XML)
- Test results
- Security scan reports
- APK builds
- iOS builds

Access: Actions → Workflow Run → Artifacts section

## 🐛 Troubleshooting

### Workflow not running?
1. Check Actions enabled in repo settings
2. Verify branch name matches trigger
3. Check path filters match changed files

### Tests pass locally but fail in CI?
1. Check Python/Flutter versions match
2. Verify environment variables
3. Check database migrations
4. Review workflow logs

### Coverage too low?
1. Run locally: `pytest --cov=app --cov-report=html`
2. Open `htmlcov/index.html` to see gaps
3. Add tests for uncovered code

## 📞 Quick Links

- [Full Setup Guide](../CI_CD_SETUP_GUIDE.md)
- [Workflow Documentation](.github/workflows/README.md)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Codecov Dashboard](https://codecov.io)

## 💡 Pro Tips

1. **Run tests locally** before pushing
2. **Use draft PRs** for work in progress
3. **Fix lint issues** immediately
4. **Review Dependabot PRs** weekly
5. **Monitor coverage trends** in Codecov
6. **Check Security tab** for CodeQL findings

---

**Need help?** See [CI_CD_SETUP_GUIDE.md](../CI_CD_SETUP_GUIDE.md)
