# CI/CD Pipeline Documentation

This document explains each GitHub Actions workflow in `.github/workflows/`.

---

## Workflows overview

| File | Trigger | Purpose |
|------|---------|---------|
| `test.yml` | Push / PR | Lint + test matrix |
| `benchmark.yml` | PR / manual | Run benchmarks, post comment |
| `security.yml` | Push, PR, weekly | SAST + dependency audit + container scan |
| `release.yml` | Tag push / manual | Docker build & push + GitHub Release |

Existing workflows (`codeql.yml`, `deploy.yml`, `finetune.yml`,
`python-package.yml`) are unchanged.

---

## test.yml — Matrix CI

**Triggers:** push to `main` or feature branches; PRs to `main`

### Jobs

#### `lint`

Runs `flake8 . --count --select=E9,F63,F7,F82` to catch syntax errors
and undefined names.  Must pass before `test` runs.

#### `test`

Runs `pytest tests/ -v --tb=short` on Python **3.10, 3.11, 3.12**.
Uses `strategy.matrix` with `fail-fast: false` so a failure on one
Python version doesn't cancel the others.

Coverage report is uploaded as an artifact from the Python 3.11 run.

### Configuration

No secrets required.  Dependencies are installed inline:

```yaml
run: pip install flask openai python-dotenv xmltodict requests pytest python-json-logger
```

---

## benchmark.yml — Benchmarks

**Triggers:** PRs to `main`; manual `workflow_dispatch`

### Job: `benchmark`

1. Installs dependencies
2. Runs `python tests/benchmark_suite.py` — outputs p50/p95/p99 latency
3. Uploads `benchmark_results.txt` as an artifact
4. Posts the results as a **PR comment** (on pull_request events)

### Interpreting the comment

Look for regressions in p95/p99 compared to the previous run.
The benchmark suite asserts hard limits (e.g. p95 `/v1/chat` < 5 s)
that will fail the job if exceeded.

---

## security.yml — Security scanning

**Triggers:** push/PR to `main`; weekly schedule (Monday 09:00 UTC); manual

### Jobs

#### `bandit` — SAST

[Bandit](https://bandit.readthedocs.io/) scans Python source for common
security issues (SQL injection, subprocess, hardcoded secrets, etc.).

```bash
bandit -r . --exclude .venv,data,docs,tests -ll
```

The job continues (`|| true`) on findings and uploads a JSON report.
Adjust `-ll` (medium/high) to enforce stricter gates.

#### `pip-audit` — Dependency audit

[pip-audit](https://pypi.org/project/pip-audit/) checks `requirements.txt`
against the OSV vulnerability database.

#### `trivy` — Container scan

[Trivy](https://trivy.dev/) scans the repository filesystem for known
CVEs at CRITICAL and HIGH severity.  Set `exit-code: "1"` to block
merges on findings.

---

## release.yml — Docker build & GitHub Release

**Triggers:** push of a `v*.*.*` tag; manual `workflow_dispatch`

### Job: `build-and-push`

1. Checks out code
2. Sets up Docker Buildx (multi-platform support)
3. Authenticates to GHCR with `GITHUB_TOKEN`
4. Extracts tags from the Git tag (e.g. `v0.6.0` → `:0.6.0`, `:0.6`, `:latest`)
5. Builds `deploy/Dockerfile` and pushes to `ghcr.io/0ai-cyberviser/hancock`

### Job: `create-release`

Uses `softprops/action-gh-release` to create a GitHub Release with
auto-generated release notes from merged PRs.

### How to release

```bash
git tag v0.7.0
git push origin v0.7.0
```

The workflow triggers automatically and publishes:
- Docker image at `ghcr.io/0ai-cyberviser/hancock:0.7.0`
- GitHub Release with changelog

---

## Adding a new workflow

1. Create `.github/workflows/my-workflow.yml`
2. Follow the naming convention: `<verb>-<noun>.yml`
3. Add a `workflow_dispatch:` trigger for manual runs
4. Document it in this file

---

## Secrets required

| Secret | Used by | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | `release.yml` | Auto-provided by GitHub — no setup needed |

No other secrets are required for CI.  The `OPENAI_API_KEY` is never
needed in CI because tests use mocked clients.
