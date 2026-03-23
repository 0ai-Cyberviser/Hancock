# Hancock Performance Guide

Benchmarking results, tuning recommendations, and scaling guidance.

---

## Running Benchmarks

### Quick benchmark (mocked backend)

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run benchmark suite (50 requests per endpoint)
python tests/benchmark_suite.py --n 50

# Run via pytest
pytest tests/benchmark_suite.py tests/test_performance.py -v
```

Results are saved to `benchmarks/results/bench_<timestamp>.json`.

### Load testing with Locust

```bash
pip install locust

# Interactive UI
locust -f tests/load_test_locust.py --host http://localhost:5000

# Headless — 100 users, 10/s spawn rate, 60 second run
locust -f tests/load_test_locust.py --headless \
  --host http://localhost:5000 \
  --users 100 --spawn-rate 10 --run-time 60s \
  --html locust-report.html
```

---

## Performance Baselines (mocked backend)

These numbers represent performance with the mock backend (no real LLM calls).
With a real Ollama/NIM backend, latency scales primarily with model inference time.

| Endpoint | p50 (ms) | p95 (ms) | p99 (ms) | Throughput (req/s) |
|---|---|---|---|---|
| `GET /health` | < 1 | < 5 | < 10 | > 1000 |
| `GET /metrics` | < 1 | < 5 | < 10 | > 1000 |
| `POST /v1/chat` | < 5 | < 20 | < 50 | > 200 |
| `POST /v1/triage` | < 5 | < 20 | < 50 | > 200 |
| `POST /v1/sigma` | < 5 | < 20 | < 50 | > 200 |

> **Note:** With a real LLM backend, latency is dominated by model inference:
> - Ollama (CPU): 2–15s per response
> - Ollama (GPU): 0.5–3s per response
> - NVIDIA NIM: 0.5–2s per response
> - OpenAI: 1–5s per response

---

## Performance Tuning

### 1. Use a production WSGI server

Replace Flask's development server with Gunicorn:

```bash
pip install gunicorn
gunicorn "hancock_agent:build_app(make_ollama_client(), 'llama3.1:8b')" \
  --workers 4 \
  --threads 2 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -
```

### 2. Increase rate limit for high-traffic deployments

```env
HANCOCK_RATE_LIMIT=300   # requests per minute per IP
```

### 3. Enable Ollama GPU acceleration

```bash
# Install CUDA-enabled Ollama
# Pull a GPU-optimised model
ollama pull llama3.1:8b
ollama run llama3.1:8b  # verify GPU is used
```

### 4. Tune model parameters

Lower `max_tokens` for faster responses on simple queries:

```python
# In hancock_agent.py, adjust per endpoint:
max_tokens=512   # triage (short responses)
max_tokens=2048  # code/sigma (longer responses)
```

### 5. Async webhook notifications

Webhook Slack/Teams notifications are already sent synchronously (5s timeout).
For high-throughput deployments, use the async pattern:

```python
import threading

def send_notification_async(source, severity, alert, triage):
    t = threading.Thread(
        target=_send_notification,
        args=(source, severity, alert, triage),
        daemon=True,
    )
    t.start()
```

---

## Scaling Recommendations

### Horizontal scaling (Kubernetes HPA)

```yaml
# deploy/kubernetes/hancock-deployment.yaml — already configured
minReplicas: 2
maxReplicas: 10
targetCPUUtilizationPercentage: 70
```

### Resource sizing

| Traffic Level | CPU Request | Memory | Replicas |
|---|---|---|---|
| Dev/Test | 100m | 128Mi | 1 |
| Production (low) | 250m | 256Mi | 2 |
| Production (medium) | 500m | 512Mi | 3–5 |
| Production (high) | 1000m | 1Gi | 5–10 |

### Caching strategies

For frequently-repeated questions, consider:

1. **Redis response cache** — cache model responses by (endpoint, hash(prompt))
2. **CDN caching** — cache `/health` and `/v1/agents` at edge
3. **Model warm-up** — pre-load models at startup to reduce cold-start latency

---

## Monitoring Performance in Production

Query Prometheus for live SLO status:

```promql
# Current p99 latency
histogram_quantile(0.99, sum(rate(hancock_request_latency_seconds_bucket[5m])) by (le))

# Requests per second
rate(hancock_requests_total[1m])

# Error rate
rate(hancock_errors_by_endpoint_total[5m]) / rate(hancock_requests_total[5m])
```

See [Monitoring Guide](monitoring.md) for full dashboard setup.
