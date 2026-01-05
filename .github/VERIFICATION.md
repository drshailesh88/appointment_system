# CI/CD Verification Checklist

## ✅ Pre-Push Verification

Before pushing to GitHub, verify all files are created:

### Required Files
- [x] `.github/workflows/backend-tests.yml`
- [x] `.github/workflows/flutter-tests.yml`
- [x] `.github/workflows/security-scan.yml`
- [x] `.github/workflows/lint.yml`
- [x] `.github/dependabot.yml`
- [x] `.github/workflows/README.md`
- [x] `.github/QUICK_REFERENCE.md`
- [x] `.markdownlint.json`
- [x] `.yamllint.yml`
- [x] `CI_CD_SETUP_GUIDE.md`
- [x] `CI_CD_SUMMARY.md`

### YAML Validation
All YAML files have been validated for syntax correctness.

Run locally to verify:
```bash
python3 -c "
import yaml
files = [
    '.github/workflows/backend-tests.yml',
    '.github/workflows/flutter-tests.yml',
    '.github/workflows/security-scan.yml',
    '.github/workflows/lint.yml',
    '.github/dependabot.yml'
]
for f in files:
    with open(f) as file:
        yaml.safe_load(file)
    print(f'✅ {f}')
"
```

## 📋 Post-Push Checklist

After pushing to GitHub:

### 1. Enable GitHub Actions
- [ ] Go to repository → Actions tab
- [ ] Enable Actions if prompted
- [ ] Verify workflows appear

### 2. First Run Verification
- [ ] Trigger a workflow (push a commit)
- [ ] Watch workflow execute
- [ ] Verify all jobs complete
- [ ] Check for any errors

### 3. Configure Secrets (Optional)
- [ ] Go to Settings → Secrets and variables → Actions
- [ ] Add `CODECOV_TOKEN` (optional but recommended)
- [ ] Verify secrets are available to workflows

### 4. Add Status Badges
- [ ] Copy badge markdown from CI_CD_SETUP_GUIDE.md
- [ ] Add to README.md
- [ ] Replace YOUR_USERNAME with actual username
- [ ] Verify badges display correctly

### 5. Branch Protection (Recommended)
- [ ] Go to Settings → Branches
- [ ] Add protection rule for main
- [ ] Require status checks: Lint, Backend Tests, Flutter Tests
- [ ] Require pull request reviews
- [ ] Enable linear history

### 6. Review First Security Scan
- [ ] Wait for weekly security scan or trigger manually
- [ ] Go to Security → Code scanning
- [ ] Review findings
- [ ] Address any critical issues

### 7. Monitor Dependabot
- [ ] Wait for first Monday after push
- [ ] Review Dependabot PRs
- [ ] Test locally
- [ ] Merge compatible updates

## 🧪 Local Testing

Before pushing, test workflows locally (optional):

### Install act (GitHub Actions local runner)
```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

### Run workflow locally
```bash
# Test lint workflow
act -j python-lint

# Test backend tests (requires Docker)
act -j test -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:full-latest
```

## 🔍 Troubleshooting

### Workflows not appearing?
1. Check `.github/workflows/` path is correct
2. Verify YAML syntax (run validation script above)
3. Ensure repository has Actions enabled
4. Check for typos in workflow names

### Workflows not running?
1. Check branch name matches trigger (main)
2. Verify path filters (backend/** or mobile/**)
3. Check if Actions are enabled
4. Review workflow run history for errors

### Secrets not working?
1. Verify secret name matches workflow
2. Check secret is available to workflows
3. Ensure no typos in secret names
4. Verify secret scope (repo-level)

### Coverage upload failing?
1. Verify CODECOV_TOKEN is set
2. Check Codecov repository configuration
3. Ensure coverage files are generated
4. Review upload step logs

## 📊 Expected Workflow Status

After first successful run, you should see:

### Actions Tab
- ✅ 4 workflows listed
- ✅ All showing green checkmarks
- ✅ Coverage artifacts available
- ✅ No errors in logs

### Security Tab
- ✅ CodeQL analysis complete
- ✅ Dependabot alerts configured
- ✅ Secret scanning enabled (if available)
- ✅ SARIF uploads successful

### Pull Requests
- ✅ Status checks appear
- ✅ Coverage comments added
- ✅ Lint results shown
- ✅ Tests run automatically

## 🎯 Success Metrics

Your CI/CD is working correctly when:

1. **Lint workflow** completes in < 10 minutes
2. **Backend tests** complete in < 15 minutes
3. **Flutter tests** complete in < 30 minutes
4. **Security scans** complete in < 25 minutes
5. **Dependabot** creates PRs weekly
6. **Coverage** reports appear in PR comments
7. **Status badges** show "passing"
8. **Security findings** appear in Security tab

## 📝 Maintenance Schedule

### Daily (Automated)
- Workflows run on push/PR
- Lint checks on every commit

### Weekly (Automated)
- Monday 00:00 UTC: Security scans
- Monday 03:00 UTC: Dependabot updates

### Monthly (Manual)
- Review workflow efficiency
- Update Python/Flutter versions
- Check Actions usage
- Review security findings

### Quarterly (Manual)
- Audit security configurations
- Update workflow best practices
- Review coverage trends
- Optimize caching strategies

## 🆘 Getting Help

If you encounter issues:

1. Check workflow logs in Actions tab
2. Review [CI_CD_SETUP_GUIDE.md](../CI_CD_SETUP_GUIDE.md)
3. Consult [workflows/README.md](workflows/README.md)
4. Search GitHub Actions documentation
5. Check for common issues below

### Common Issues

**Issue:** Tests pass locally but fail in CI
- **Fix:** Check Python/Flutter versions match
- **Fix:** Verify environment variables
- **Fix:** Check database setup

**Issue:** Coverage below threshold
- **Fix:** Run coverage locally to identify gaps
- **Fix:** Add tests for uncovered code
- **Fix:** Adjust threshold if needed

**Issue:** Dependabot PR conflicts
- **Fix:** Update local dependencies
- **Fix:** Resolve conflicts manually
- **Fix:** Test updated dependencies

**Issue:** Security scan false positives
- **Fix:** Add nosec comments with justification
- **Fix:** Review Bandit configuration
- **Fix:** Dismiss findings in Security tab

## ✨ Quick Commands

### Push CI/CD to GitHub
```bash
git add .github/ .markdownlint.json .yamllint.yml CI_CD_*.md
git commit -m "chore(ci): Add comprehensive CI/CD pipeline

- Add backend testing with coverage
- Add Flutter testing and builds
- Add security scanning (Bandit, Safety, CodeQL, Gitleaks)
- Add automated linting
- Add Dependabot for dependency updates
- Add comprehensive documentation"
git push origin main
```

### Trigger Manual Security Scan
```bash
gh workflow run security-scan.yml
```

### View Workflow Runs
```bash
gh run list --workflow=backend-tests.yml
gh run list --workflow=flutter-tests.yml
gh run list --workflow=security-scan.yml
```

### Download Artifacts
```bash
gh run download <run-id>
```

## 🎉 Final Checklist

Before considering CI/CD setup complete:

- [ ] All files created and validated
- [ ] Pushed to GitHub
- [ ] Actions enabled
- [ ] First successful workflow run
- [ ] Status badges added to README
- [ ] Codecov configured (optional)
- [ ] Branch protection enabled (recommended)
- [ ] Team notified about new workflows
- [ ] Documentation reviewed
- [ ] Maintenance schedule understood

---

**Congratulations!** Your CI/CD pipeline is ready for production use.

---

*Last Updated: 2026-01-05*
