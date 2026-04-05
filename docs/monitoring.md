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

The `/metrics` endpoint exposes four core counters:

| Metric | Type | Labels | Description |
|---|---|---|---|
| `hancock_requests_total` | Counter | — | Total HTTP requests |
| `hancock_errors_total` | Counter | — | Total 4xx/5xx errors |
| `hancock_requests_by_endpoint` | Counter | `endpoint` | Requests per endpoint |
| `hancock_requests_by_mode` | Counter | `mode` | Requests per specialist mode |

`monitoring/metrics_exporter.py` defines additional metrics (histograms, gauges) that become available when wired into the agent via middleware:

| Metric | Type | Labels | Description |
|---|---|---|---|
| `hancock_request_duration_seconds` | Histogram | `method`, `endpoint`, `status_code` | HTTP request latency |
| `hancock_model_response_time_seconds` | Histogram | `model`, `operation` | LLM model response time |
| `hancock_rate_limit_exceeded_total` | Counter | `endpoint`, `client_id` | Rate limit violations |
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
from monitoring.metrics_exporter import track_request, track_model_call

# Track an HTTP request (context manager)
with track_request(endpoint="/chat", method="POST"):
    ...

# Track a model response
with track_model_call(model="llama3.1:8b", operation="pentest"):
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

The dashboard contains 10 panels:

| Panel | Visualization | Query |
|---|---|---|
| Request Rate | Time series | `rate(hancock_requests_total[2m])` |
| Error Rate % | Time series | `rate(hancock_errors_total[2m]) / rate(hancock_requests_total[2m]) * 100` |
| Requests by Endpoint | Time series | `hancock_requests_by_endpoint` |
| Requests by Mode | Time series | `hancock_requests_by_mode` |
| Memory Usage | Time series | `hancock_memory_usage_bytes` |
| Active Connections | Time series | `hancock_active_connections` |
| Total Requests (stat) | Stat | `hancock_requests_total` |
| Total Errors (stat) | Stat | `hancock_errors_total` |
| Current Memory (stat) | Stat | `hancock_memory_usage_bytes` |
| Active Connections (stat) | Stat | `hancock_active_connections` |

Dashboard refresh interval is 30 s.

---

## Alerting Rules

Alert rules are defined in `monitoring/alerting_rules.yaml` and organised into three groups.

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
| `HancockHighErrorRate` | Error rate > 5% over 5 min | warning | Too many errors |

#### `hancock.availability` — Service Health

| Alert | Condition | Severity | Description |
|---|---|---|---|
| `HancockNoTraffic` | No requests for 5 min | critical | Service may be down |

#### `hancock.memory` — Resource Usage

| Alert | Condition | Severity | Description |
|---|---|---|---|
| `HancockMemoryGrowth` | Memory growing > 50 MiB/min over 10 min | warning | Possible memory leak |
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
