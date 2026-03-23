# Monitoring & Alerting Guide

Hancock ships with a full observability stack: Prometheus metrics,
Grafana dashboards, and alerting rules.

---

## Architecture overview

```
Hancock Agent ──► Prometheus ──► Grafana
     │                │
     │                └──► AlertManager ──► Slack / PagerDuty
     │
     └──► JSON logs (stdout) ──► log aggregation (ELK / Loki)
```

---

## Prometheus metrics

All metrics are served at `GET /metrics` (requires `prometheus_client`).

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `hancock_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `hancock_request_latency_seconds` | Histogram | method, endpoint, status_code | Request latency |
| `hancock_active_requests` | Gauge | endpoint | In-flight requests |
| `hancock_model_inference_seconds` | Histogram | model, mode | LLM inference time |
| `hancock_errors_total` | Counter | error_type, endpoint | Error count by type |
| `hancock_rate_limit_hits_total` | Counter | endpoint | Rate-limit rejections |

### Instrumenting your code

```python
from monitoring.metrics_exporter import record_request, record_inference

# In a Flask before/after_request hook:
record_request("POST", "/v1/chat", 200, elapsed_seconds)
record_inference("llama3.1:8b", "pentest", inference_seconds)
```

### Installing prometheus_client

```bash
pip install prometheus-client
```

Without it, all metrics calls are silent no-ops (safe for development).

---

## Grafana dashboard

The dashboard JSON is at `monitoring/grafana_dashboard.json`.

### Import manually

1. Open Grafana → **Dashboards** → **Import**
2. Upload `monitoring/grafana_dashboard.json`
3. Select your Prometheus data source

### Auto-provision (Docker Compose)

The `deploy/docker-compose.yml` mounts the dashboard automatically.
After `docker compose up`, open **http://localhost:3000**.

### Dashboard panels

| Panel | Description |
|-------|-------------|
| Request Rate | req/s by endpoint |
| Request Latency Percentiles | p50/p95/p99 by endpoint |
| Error Rate | errors/s by type |
| Model Inference Latency | p50/p95/p99 by model |
| Active Requests | Current in-flight count |
| Rate Limit Hits | Rate-limit rejections/s |

---

## Alerting rules

Rules are defined in `monitoring/alerting_rules.yaml`.

| Alert | Severity | Trigger |
|-------|----------|---------|
| `HancockDown` | critical | Agent unreachable > 1 min |
| `HancockModelUnavailable` | critical | Model errors for > 2 min |
| `HancockHighP99Latency` | warning | p99 latency > 5 s for 5 min |
| `HancockHighInferenceLatency` | warning | p95 inference > 30 s for 5 min |
| `HancockHighErrorRate` | warning | Error rate > 5% for 5 min |
| `HancockRateLimitExhaustion` | warning | > 10 rate-limit hits/s for 2 min |
| `HancockHighMemoryUsage` | warning | Host memory > 80% for 5 min |
| `HancockDiskSpaceLow` | warning | Disk usage > 85% for 10 min |

### Load rules into Prometheus

Add to `prometheus.yml`:

```yaml
rule_files:
  - /etc/prometheus/alerting_rules.yaml
```

---

## Structured logging

Hancock emits JSON-structured logs when `python-json-logger` is installed.

### Configure

```python
from monitoring.logging_config import configure_logging

configure_logging(level="INFO", json_output=True)
```

Or via environment variables:

```bash
export HANCOCK_LOG_LEVEL=INFO
export HANCOCK_LOG_JSON=true
```

### Request ID correlation

Each request is assigned a UUID stored in the `request_id` context variable.
All log records during a request include the `request_id` field, enabling
full request tracing across log lines.

---

## Health checks

`monitoring/health_check.py` provides deep dependency checks:

```python
from monitoring.health_check import HealthChecker

checker = HealthChecker(ttl=30)   # cache results for 30 s
status = checker.check_all()
print(status)
# {'status': 'healthy', 'checks': {'disk': {...}, 'memory': {...}, 'ollama': {...}}}
```

Results are cached per check type with a configurable TTL to avoid
hammering backends on every `/health` poll.
