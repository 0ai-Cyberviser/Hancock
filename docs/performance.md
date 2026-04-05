# Performance Guide

This guide covers Hancock's latency targets, benchmark suite, and load testing tooling.

---

## Table of Contents

- [Latency Targets](#latency-targets)
- [Benchmark Suite](#benchmark-suite)
- [Load Testing with Locust](#load-testing-with-locust)
- [Performance Tests](#performance-tests)
- [Tuning Recommendations](#tuning-recommendations)

---

## Latency Targets

These are the target latencies for Hancock endpoints under normal load. They are enforced in CI via the benchmark suite.

| Endpoint | p50 | p95 | p99 |
|---|---|---|---|
| `GET /health` | < 10 ms | < 25 ms | < 50 ms |
| `GET /models` | < 20 ms | < 50 ms | < 100 ms |
| `GET /mode` | < 20 ms | < 50 ms | < 100 ms |
| `POST /chat` (LLM mocked) | < 50 ms | < 150 ms | < 500 ms |

The **p99 threshold of 500 ms** is the hard CI gate. Any PR that breaches it will fail the benchmark job.

---

## Benchmark Suite

`tests/benchmark_suite.py` is a pytest-based micro-benchmark that runs locally or in CI.

### Running Locally

```bash
# Run with default settings (50 iterations, 5-iteration warmup)
pytest tests/benchmark_suite.py -v

# Run a specific endpoint benchmark
pytest tests/benchmark_suite.py -v -k "health"

# Output a summary table
pytest tests/benchmark_suite.py -v --tb=short
```

### How It Works

1. **Warm-up:** 5 requests are sent to each endpoint to prime connection pools and JIT paths.
2. **Measurement:** 50 timed requests are sent sequentially.
3. **Statistics:** p50, p95, and p99 are computed from the 50 samples.
4. **Assertion:** The test fails if p99 exceeds the threshold (500 ms for non-LLM endpoints).

### CI Integration

The benchmark runs on every pull request via `.github/workflows/benchmark.yml`. It posts a summary table to the PR as a comment:

```
| Endpoint       | p50    | p95    | p99    | Status |
|----------------|--------|--------|--------|--------|
| GET /health    | 3 ms   | 6 ms   | 9 ms   | ✅     |
| GET /models    | 8 ms   | 14 ms  | 22 ms  | ✅     |
| POST /chat     | 41 ms  | 89 ms  | 134 ms | ✅     |
```

---

## Load Testing with Locust

`tests/load_test_locust.py` provides Locust user profiles for sustained load testing.

### User Profiles

| Class | Behaviour | Use Case |
|---|---|---|
| `HealthOnlyUser` | Polls `GET /health` | Smoke test — verifies availability under load |
| `ReadOnlyUser` | Mix of `GET /health`, `/models`, `/mode` | Read-only load without LLM calls |

### Running Locust

#### Headless (CLI)

```bash
# Install Locust
pip install locust

# Smoke test — 10 users, 1 minute
locust -f tests/load_test_locust.py \
  --host=http://localhost:5000 \
  --users 10 \
  --spawn-rate 2 \
  --run-time 60s \
  --headless \
  --class-picker HealthOnlyUser

# Sustained read load — 50 users, 5 minutes
locust -f tests/load_test_locust.py \
  --host=http://localhost:5000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --headless \
  --class-picker ReadOnlyUser
```

#### Web UI

```bash
locust -f tests/load_test_locust.py --host=http://localhost:5000
# Open http://localhost:8089
```

### Interpreting Results

Key metrics to watch during a load test:

| Metric | Acceptable | Investigate |
|---|---|---|
| Failure rate | < 0.1% | > 1% |
| Median response time | < 100 ms | > 500 ms |
| p99 response time | < 500 ms | > 2 s |
| Requests/s at target load | Stable | Declining |

Monitor process resource usage in Grafana during load tests (e.g., via `hancock_memory_usage_bytes` and `hancock_active_connections` if `metrics_exporter` middleware is wired into the agent).

### Running Against a Deployed Instance

```bash
locust -f tests/load_test_locust.py \
  --host=https://your-hancock-instance.example.com \
  --users 20 \
  --spawn-rate 2 \
  --run-time 2m \
  --headless
```

If API authentication is enabled, set `HANCOCK_API_KEY` in the environment — the Locust profiles read it automatically.

---

## Performance Tests

`tests/test_performance.py` is a lighter pytest suite that runs on every push alongside the unit tests.

It asserts:

- `GET /health` responds within 100 ms (per request)
- `GET /models` responds within 200 ms
- Memory usage stays within an acceptable baseline + delta threshold

These tests use the Flask test client (no real network), so they measure application logic overhead, not network latency.

```bash
pytest tests/test_performance.py -v
```

---

## Tuning Recommendations

### LLM Backend

- **Ollama (local):** Use a GPU-enabled host for the best model throughput. The `llama3.1:8b` model runs comfortably on a 16 GB VRAM GPU.
- **NVIDIA NIM:** NIM endpoints are rate-limited. Use the `NVIDIA_API_KEY` with sufficient quota for your expected request rate.

### Flask / WSGI

The default `hancock_agent.py --server` uses Flask's development server. For production, run behind a WSGI server:

```bash
# Gunicorn example
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "hancock_agent:create_app()"
```

Use `4 × CPU_cores` workers as a starting point and tune based on Prometheus metrics.

### Kubernetes HPA

`deploy/k8s/hpa.yaml` scales pods when CPU exceeds 70% or memory exceeds 80%. Adjust thresholds and `maxReplicas` based on your observed p99 latency at various replica counts.

### Health Check TTL

`monitoring/health_check.py` caches deep health check results for 30 s to avoid hammering the Ollama endpoint on every Kubernetes liveness probe tick. Increase this if Ollama probes are contributing to model latency.
