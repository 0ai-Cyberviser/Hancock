# Monitoring Guide

Hancock ships with a full observability stack: structured logging, Prometheus metrics, Grafana dashboards, and alerting rules.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prometheus Metrics](#prometheus-metrics)
- [Grafana Dashboards](#grafana-dashboards)
- [Alerting Rules](#alerting-rules)
- [Health Checks](#health-checks)
- [Structured Logging](#structured-logging)
- [Local Stack Setup](#local-stack-setup)

---

## Architecture Overview

```
Hancock (port 5000)
  └── /metrics  ──────────►  Prometheus (port 9090)
                                   └──────────►  Grafana (port 3000)
                                   └──────────►  Alertmanager
```

All monitoring code lives in `monitoring/`:

| File | Purpose |
|---|---|
| `monitoring/metrics_exporter.py` | Prometheus metric definitions and helpers |
| `monitoring/health_check.py` | Deep health checks with 30 s TTL caching |
| `monitoring/logging_config.py` | Structured JSON logging with request-ID correlation |
| `monitoring/prometheus_dashboard.py` | Programmatic Grafana dashboard generator |
| `monitoring/alerting_rules.yaml` | Prometheus alerting rule groups |
| `monitoring/grafana_dashboard.json` | Pre-built Grafana dashboard (generated) |

---

## Prometheus Metrics

Metrics are exposed at `GET /metrics` and collected by `monitoring/metrics_exporter.py`.

### Available Metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `hancock_request_duration_seconds` | Histogram | `method`, `endpoint`, `status` | HTTP request latency |
| `hancock_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests |
| `hancock_model_response_time_seconds` | Histogram | `model`, `mode` | LLM model response time |
| `hancock_rate_limit_exceeded_total` | Counter | `endpoint` | Rate limit violations |
| `hancock_memory_usage_bytes` | Gauge | — | Process memory usage |
| `hancock_active_connections` | Gauge | — | Current active connections |

### Scrape Configuration

Add Hancock to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'hancock'
    static_configs:
      - targets: ['hancock:5000']
    scrape_interval: 15s
    metrics_path: /metrics
```

The Kubernetes `service.yaml` includes Prometheus annotations so the Prometheus Kubernetes SD will auto-discover Hancock pods:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "5000"
  prometheus.io/path: "/metrics"
```

### Using the Metrics Helpers

```python
from monitoring.metrics_exporter import track_request, track_model_response

# Track an HTTP request (context manager)
with track_request(method="POST", endpoint="/chat"):
    ...

# Track a model response
with track_model_response(model="llama3.1:8b", mode="pentest"):
    response = llm.chat(...)
```

---

## Grafana Dashboards

The pre-built dashboard is at `monitoring/grafana_dashboard.json`. Import it directly into Grafana:

1. Open Grafana → **Dashboards** → **Import**
2. Upload `monitoring/grafana_dashboard.json`
3. Select your Prometheus data source
4. Click **Import**

### Regenerating the Dashboard

The dashboard is generated from `monitoring/prometheus_dashboard.py`:

```bash
python monitoring/prometheus_dashboard.py
# Outputs monitoring/grafana_dashboard.json
```

### Dashboard Panels

The dashboard contains 11 panels:

| Panel | Visualization | Query |
|---|---|---|
| Request Rate | Time series | `rate(hancock_requests_total[5m])` |
| Error Rate % | Time series | `rate(...status=~"5.."[5m]) / rate(...[5m]) * 100` |
| Latency p50 | Time series | `histogram_quantile(0.50, ...)` |
| Latency p95 | Time series | `histogram_quantile(0.95, ...)` |
| Latency p99 | Time series | `histogram_quantile(0.99, ...)` |
| Model Response Time | Time series | `histogram_quantile(0.99, hancock_model_response_time_seconds_bucket)` |
| Rate Limit Exceeded | Time series | `rate(hancock_rate_limit_exceeded_total[5m])` |
| Memory Usage | Time series | `hancock_memory_usage_bytes` |
| Active Connections | Time series | `hancock_active_connections` |
| Total Requests (stat) | Stat | `sum(hancock_requests_total)` |
| Avg Response Time (stat) | Stat | `avg(hancock_request_duration_seconds_sum / ...count)` |

Dashboard refresh interval is 30 s.

---

## Alerting Rules

Alert rules are defined in `monitoring/alerting_rules.yaml` and organised into four groups.

### Loading the Rules

```yaml
# prometheus.yml
rule_files:
  - /etc/prometheus/alerting_rules.yaml
```

### Rule Groups

#### `hancock.requests` — HTTP Traffic

| Alert | Condition | Severity | Description |
|---|---|---|---|
| `HancockHighErrorRate` | 5xx error rate > 5% over 5 min | critical | Too many server errors |
| `HancockHighP99Latency` | p99 latency > 5 s over 10 min | warning | Slow responses |

#### `hancock.model` — LLM Backend

| Alert | Condition | Severity | Description |
|---|---|---|---|
| `HancockModelUnavailable` | No model responses for 5 min | critical | LLM backend down |
| `HancockHighModelP99` | Model p99 response > 30 s over 10 min | warning | Slow model inference |

#### `hancock.rate_limits` — Abuse Detection

| Alert | Condition | Severity | Description |
|---|---|---|---|
| `HancockRateLimitSpike` | Rate limit exceeded > 1 req/s over 5 min | warning | Possible abuse or misconfigured client |

#### `hancock.memory` — Resource Usage

| Alert | Condition | Severity | Description |
|---|---|---|---|
| `HancockMemoryGrowth` | Memory growing > 50 MiB/min over 5 min | warning | Possible memory leak |
| `HancockHighMemoryUsage` | Absolute memory > 1 GiB | critical | Memory ceiling breached |

### Alertmanager Integration

Configure Alertmanager receivers to route alerts to Slack, PagerDuty, or email. Example routing:

```yaml
route:
  receiver: 'slack-critical'
  group_by: ['alertname', 'severity']
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack-warnings'
```

---

## Health Checks

`monitoring/health_check.py` provides deep health checks with 30 s TTL caching on the `GET /health` endpoint.

### Checked Components

| Component | Check | Thresholds |
|---|---|---|
| Ollama | HTTP reachability + model list | — |
| NVIDIA NIM | API reachability | — |
| Memory | Available system memory | Warn < 512 MiB |
| Disk | Available disk space | Warn < 1 GiB |
| Prometheus | Metrics endpoint reachability | — |

### Response Format

```json
{
  "status": "ok",
  "checks": {
    "ollama": { "status": "ok", "latency_ms": 12 },
    "memory": { "status": "ok", "detail": "available_mb=4096" },
    "disk":   { "status": "ok", "detail": "available_gb=42" }
  }
}
```

Statuses: `ok` | `degraded` | `error`

HTTP status codes: `200` (ok/degraded), `503` (error).

---

## Structured Logging

`monitoring/logging_config.py` emits structured JSON logs with automatic request-ID injection.

### Log Format

```json
{
  "timestamp": "2024-01-15T10:23:45.123Z",
  "level": "INFO",
  "request_id": "req-a1b2c3d4",
  "message": "POST /chat 200 142ms",
  "method": "POST",
  "path": "/chat",
  "status": 200,
  "duration_ms": 142
}
```

### Configuration

```python
from monitoring.logging_config import configure_logging

configure_logging(app, log_level="INFO")
```

The `request_id` is generated per request and injected into every log line via `RequestIdFilter`. Noisy third-party libraries (`urllib3`, `werkzeug`, `httpx`) are silenced by default.

### Log Level

Set via the `LOG_LEVEL` environment variable (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default: `INFO`.

---

## Local Stack Setup

The full observability stack (Hancock + Prometheus + Grafana) is defined in `deploy/docker-compose.yml`:

```bash
cd deploy
docker compose up -d

# Access
# Hancock:    http://localhost:5000
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000  (admin / admin)
```

Import `monitoring/grafana_dashboard.json` into Grafana on first run to get the pre-built dashboard.
