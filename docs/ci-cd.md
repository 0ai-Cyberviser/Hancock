# Hancock CI/CD Guide

Overview of the GitHub Actions workflows, testing strategy, and deployment process.

---

## Workflows Overview

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| **Python Package** | `python-package.yml` | `push` | Basic lint + pytest |
| **Test** | `test.yml` | `push main`, PRs, daily | Full matrix test (3.10–3.12) + security scan |
| **Benchmark** | `benchmark.yml` | PRs to `main` | Performance regression check + PR comment |
| **Security** | `security.yml` | `push main`, PRs, weekly | SAST, dependency audit, container scan |
| **Deploy** | `deploy.yml` | `push main` (docs path) | Netlify docs deployment |
| **Release** | `release.yml` | `push v*.*.*` tag | Docker build/push + GitHub Release |
| **CodeQL** | `codeql.yml` | `push main`, PRs, weekly | Static analysis |

---

## Test Strategy

### Unit tests

Located in `tests/test_hancock_api.py` — tests all Flask endpoints with a mocked OpenAI client.

```bash
pytest tests/test_hancock_api.py -v
```

### Integration tests

Located in `tests/test_integration_deployment.py` — end-to-end endpoint availability.

```bash
pytest tests/test_integration_deployment.py -v
```

### Performance tests

Located in `tests/test_performance.py` — latency and throughput assertions.

```bash
pytest tests/test_performance.py -v
```

### Benchmark suite

Located in `tests/benchmark_suite.py` — statistical latency report.

```bash
pytest tests/benchmark_suite.py -v
# or standalone:
python tests/benchmark_suite.py --n 50
```

### Load tests

Located in `tests/load_test_locust.py` — Locust-based user simulation.

```bash
locust -f tests/load_test_locust.py --host http://localhost:5000
```

---

## Deployment Process

### Development → Staging → Production

```
Feature branch
    ↓ PR to main
    ↓ test.yml (matrix tests) + benchmark.yml (perf check) + CodeQL
    ↓ Merge to main
    ↓ deploy.yml (Netlify docs)
    ↓ Manual: tag release (v0.x.y)
    ↓ release.yml (Docker build/push + GitHub Release)
```

### Creating a release

```bash
# 1. Update version in hancock_agent.py
# VERSION = "0.6.0"

# 2. Commit and push
git add hancock_agent.py
git commit -m "chore: bump version to 0.6.0"
git push origin main

# 3. Create and push tag
git tag v0.6.0
git push origin v0.6.0
# → Triggers release.yml automatically
```

---

## Rollback Procedures

### Rollback Docker Hub image

```bash
# Pull specific version
docker pull cyberviser/hancock:0.4.0

# Update Kubernetes deployment
kubectl set image deployment/hancock hancock=cyberviser/hancock:0.4.0 -n hancock
```

### Rollback Kubernetes deployment

```bash
kubectl rollout undo deployment/hancock -n hancock
# Check status
kubectl rollout status deployment/hancock -n hancock
```

### Re-run a failed workflow

1. Go to **Actions** tab in GitHub
2. Select the failed workflow run
3. Click **Re-run all jobs**

---

## Adding New Tests

New test files should:
1. Be placed in `tests/`
2. Follow existing patterns (see `tests/test_hancock_api.py`)
3. Use `conftest.py` fixtures where possible
4. Pass `pytest tests/ -v` locally before pushing

---

## Secrets Required

| Secret | Used by | Description |
|---|---|---|
| `DOCKERHUB_USERNAME` | `release.yml` | Docker Hub login |
| `DOCKERHUB_TOKEN` | `release.yml` | Docker Hub access token |
| `NETLIFY_AUTH_TOKEN` | `deploy.yml` | Netlify deploy token |
| `NETLIFY_SITE_ID` | `deploy.yml` | Netlify site identifier |

Set these at: **GitHub repo → Settings → Secrets and variables → Actions**
