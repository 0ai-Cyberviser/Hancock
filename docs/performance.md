# Performance Tuning Guide

This guide explains how to optimise Hancock for throughput and latency,
and how to interpret benchmark results.

---

## Running benchmarks

### Quick benchmark

```bash
python tests/benchmark_suite.py
```

Sample output:

```
[benchmark] GET /health (50 iterations)
  min=0.3ms  p50=0.5ms  p95=1.1ms  p99=2.3ms  max=4.7ms

[benchmark] POST /v1/chat (20 iterations)
  min=18ms  p50=24ms  p95=47ms  p99=89ms  max=102ms
```

### Pytest benchmarks

```bash
pytest tests/benchmark_suite.py -v
pytest tests/test_performance.py -v
```

---

## Interpreting results

| Percentile | Meaning |
|-----------|---------|
| p50 (median) | Typical user experience |
| p95 | 95% of requests are faster than this |
| p99 | Tail latency — worst-case for most users |
| max | Outlier; influenced by GC pauses / cold starts |

Focus on **p95 and p99** for SLO definitions.

### Recommended SLOs

| Endpoint | p95 target | p99 target |
|----------|-----------|-----------|
| `/health` | < 50 ms | < 200 ms |
| `/v1/chat` | < 3 s | < 8 s |
| `/v1/triage` | < 3 s | < 8 s |
| `/v1/code` | < 5 s | < 15 s |

---

## Tuning knobs

### Model selection

Smaller models have lower latency at the cost of quality:

| Model | Typical p50 | Use case |
|-------|------------|---------|
| `llama3.1:8b` | ~0.5 s | Development, testing |
| `llama3.1:70b` | ~3–5 s | Production pentest |
| `qwen2.5-coder:7b` | ~0.8 s | Code generation |

### Concurrency

- Default Flask dev server: single-threaded → poor concurrent throughput
- Use a production WSGI server:

```bash
pip install gunicorn
gunicorn hancock_agent:app -w 4 -b 0.0.0.0:5000
```

### Rate limiting

Adjust `HANCOCK_RATE_LIMIT` (requests/minute per IP):

```bash
export HANCOCK_RATE_LIMIT=120   # default: 60
```

### Connection pooling (OpenAI)

The OpenAI client reuses connections automatically.  For high-throughput
deployments, increase the connection pool:

```python
from openai import OpenAI
import httpx

client = OpenAI(
    http_client=httpx.Client(
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )
)
```

### Ollama GPU acceleration

Ensure Ollama is running with GPU support for 5–10× faster inference:

```bash
docker run --gpus all -p 11434:11434 ollama/ollama
ollama pull llama3.1:8b
```

---

## Load testing

Use Locust for sustained load tests:

```bash
pip install locust
locust -f tests/load_test_locust.py \
  --host http://localhost:5000 \
  --users 20 \
  --spawn-rate 2 \
  --run-time 60s \
  --headless
```

Key metrics to watch during load tests:
- **RPS** — requests per second achieved
- **Failure rate** — should stay below 1%
- **p95 latency** — compare against your SLO
- **CPU / memory** on the Hancock host

---

## CI performance regression detection

The `benchmark.yml` workflow runs benchmarks on every PR and posts
results as a comment.  Review the comment to catch regressions before
they reach production.

To add a new benchmark:

1. Add a test class to `tests/benchmark_suite.py`
2. Call `_run_benchmark(fn, iterations, label)`
3. Assert `stats["p99"] < your_budget`
