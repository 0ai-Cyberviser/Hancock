# CI/CD Guide

Hancock uses GitHub Actions for continuous integration, security scanning, benchmarking, and releases. All workflows live in `.github/workflows/`.

---

## Table of Contents

- [Workflow Overview](#workflow-overview)
- [Test Workflow](#test-workflow)
- [Benchmark Workflow](#benchmark-workflow)
- [Security Workflow](#security-workflow)
- [Release Workflow](#release-workflow)
- [Supporting Workflows](#supporting-workflows)
- [Required Secrets](#required-secrets)
- [Local Equivalents](#local-equivalents)

---

## Workflow Overview

| Workflow file | Trigger | Purpose |
|---|---|---|
| `test.yml` | Push to `main`/`master`, PRs | Lint + unit tests on Python 3.10–3.12 |
| `benchmark.yml` | PRs to `main`/`master` | Latency benchmark, posts p99 table to PR |
| `security.yml` | Push, PR, weekly (Monday) | Bandit SAST, pip-audit, Trivy container scan |
| `release.yml` | Tagged push (`v*.*.*`) | Build/push Docker image, create GitHub Release |
| `deploy.yml` | Push to `main` (docs/**) | Deploy `docs/` to Netlify |
| `python-package.yml` | All pushes | Secondary lint + pytest run |
| `finetune.yml` | Manual `workflow_dispatch` | Fine-tune Hancock on Modal GPU |
| `codeql.yml` | Push, PR, schedule | CodeQL static analysis |

---

## Test Workflow

**File:** `.github/workflows/test.yml`  
**Triggers:** Push to `main`/`master`, all pull requests

Runs a matrix build across Python **3.10**, **3.11**, and **3.12**.

### Steps

1. **Lint (critical errors only)** — `flake8` with `--select E9,F63,F7,F82`. These flags catch syntax errors, undefined names, and broken imports. The build fails on any match.
2. **pytest** — Runs the full test suite in `tests/`.

### Passing Requirements

All three Python versions must pass. A red check on any matrix leg blocks merge.

### Running Locally

```bash
# Lint (matches CI exactly)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Tests
pytest tests/ -v
```

---

## Benchmark Workflow

**File:** `.github/workflows/benchmark.yml`  
**Triggers:** Pull requests to `main`/`master`

Runs `tests/benchmark_suite.py` and posts a latency summary table as a PR comment.

### What It Measures

- p50, p95, and p99 response times for `/health`, `/models`, `/mode`, and `/chat`
- 50 iterations per endpoint after a 5-request warm-up
- Hard failure if p99 > 500 ms on non-LLM endpoints

### Interpreting Results

The PR comment shows a table like:

```
| Endpoint    | p50   | p95    | p99    | Status |
|-------------|-------|--------|--------|--------|
| GET /health | 3 ms  | 6 ms   | 9 ms   | ✅     |
| POST /chat  | 41 ms | 89 ms  | 134 ms | ✅     |
```

A regression in p99 will fail the job and block merge. See [performance.md](performance.md) for target values and tuning advice.

### Running Locally

```bash
pytest tests/benchmark_suite.py -v
```

---

## Security Workflow

**File:** `.github/workflows/security.yml`  
**Triggers:** Push, pull requests, weekly schedule (every Monday)

Three independent security scans run in parallel:

### 1. Bandit — SAST

Scans Python source for common security issues (hardcoded credentials, use of `eval`, insecure deserialization, etc.).

```bash
# Local equivalent
pip install bandit
bandit -r . -ll  # medium severity and above
```

### 2. pip-audit — Dependency Vulnerabilities

Checks all installed packages against the OSV and PyPI advisory databases.

```bash
# Local equivalent
pip install pip-audit
pip-audit
```

### 3. Trivy — Container Image Scan

Builds the Docker image and scans it for CRITICAL and HIGH CVEs in OS packages and Python dependencies.

```bash
# Local equivalent
docker build -t hancock:local .
trivy image --severity CRITICAL,HIGH hancock:local
```

### Remediation

- **Bandit findings:** Review the flagged line and either fix the code or add a `# nosec` comment with a justification.
- **pip-audit findings:** Update the affected package in `requirements.txt` to a patched version.
- **Trivy findings:** Update the base image or the vulnerable OS/Python package.

The weekly schedule ensures dependency vulnerabilities are caught even when no code is pushed.

---

## Release Workflow

**File:** `.github/workflows/release.yml`  
**Triggers:** Tagged pushes matching `v*.*.*` (e.g., `v0.6.0`)

### Steps

1. **Build Docker image** — built from the root `Dockerfile`
2. **Push to GHCR** — pushes to `ghcr.io/cyberviser/hancock` with three tags:
   - Full semver: `v0.6.0`
   - Minor: `v0.6`
   - `latest`
3. **Extract changelog** — pulls the relevant section from `CHANGELOG.md`
4. **Create GitHub Release** — attaches the changelog section as release notes

### Creating a Release

```bash
# Tag and push — this triggers the workflow automatically
git tag v0.6.0
git push origin v0.6.0
```

The image will be available at `ghcr.io/cyberviser/hancock:v0.6.0` a few minutes after the tag is pushed.

### Versioning Convention

Hancock follows [Semantic Versioning](https://semver.org/):

- **Patch** (`v0.5.1`): Bug fixes, dependency updates
- **Minor** (`v0.6.0`): New features, new agent modes, backwards-compatible changes
- **Major** (`v1.0.0`): Breaking API changes

---

## Supporting Workflows

### Docs Deploy (`deploy.yml`)

Deploys the `docs/` directory to Netlify whenever files under `docs/` are pushed to `main`. Requires `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` secrets. Posts a preview URL as a PR comment.

### Python Package (`python-package.yml`)

A secondary lint + test run that also runs `flake8` with `--exit-zero` (reports style warnings without failing) alongside the stricter check in `test.yml`.

### Fine-Tune (`finetune.yml`)

Manual workflow for fine-tuning Hancock on Modal GPUs (T4, A10G, A100). Dispatched via the GitHub Actions UI with optional `--dry-run` and `--push-hub` flags. Requires `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` secrets.

### CodeQL (`codeql.yml`)

GitHub's CodeQL engine performs deep static analysis on pushes, PRs, and a schedule. Results appear in the **Security → Code scanning** tab. High and critical alerts should be resolved before merge.

---

## Required Secrets

Configure these in **Settings → Secrets and variables → Actions**:

| Secret | Required by | Purpose |
|---|---|---|
| `NETLIFY_AUTH_TOKEN` | `deploy.yml` | Netlify deployment |
| `NETLIFY_SITE_ID` | `deploy.yml` | Target Netlify site |
| `MODAL_TOKEN_ID` | `finetune.yml` | Modal GPU compute |
| `MODAL_TOKEN_SECRET` | `finetune.yml` | Modal GPU compute |
| `GHCR_TOKEN` | `release.yml` | Push to GitHub Container Registry |

The `GITHUB_TOKEN` (automatically provided by Actions) is used by the release and CodeQL workflows.

---

## Local Equivalents

Run these locally to replicate what CI does before opening a PR:

```bash
# 1. Lint (fail-fast, matches test.yml)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# 2. Full test suite
pytest tests/ -v

# 3. Benchmark
pytest tests/benchmark_suite.py -v

# 4. SAST
bandit -r . -ll

# 5. Dependency audit
pip-audit

# 6. Container scan
docker build -t hancock:local .
trivy image --severity CRITICAL,HIGH hancock:local

# 7. Pre-flight checks
python deploy/startup_checks.py
```
