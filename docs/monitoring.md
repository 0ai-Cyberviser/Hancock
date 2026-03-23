# Hancock Monitoring Guide

Setup and usage of Prometheus metrics, Grafana dashboards, and alerting rules.

---

## Table of Contents

1. [Prometheus Setup](#prometheus-setup)
2. [Metrics Reference](#metrics-reference)
3. [Grafana Dashboard](#grafana-dashboard)
4. [Alert Configuration](#alert-configuration)
5. [Custom Metrics](#custom-metrics)
6. [Troubleshooting](#troubleshooting)

---

## Prometheus Setup

### With Docker Compose (recommended)

```bash
cd deploy/docker
docker compose up -d prometheus
```

Prometheus scrapes Hancock metrics at `http://hancock:8001/metrics` every 15 seconds.

### Standalone Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: hancock
    static_configs:
      - targets: ["localhost:8001"]
    metrics_path: /metrics
    scrape_interval: 15s
```

### On Kubernetes

Hancock pods are annotated for auto-discovery:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8001"
  prometheus.io/path: "/metrics"
```

Apply the ServiceMonitor (if using Prometheus Operator):

```bash
kubectl apply -f deploy/kubernetes/prometheus-deployment.yaml
```

---

## Metrics Reference

| Metric | Type | Labels | Description |
|---|---|---|---|
| `hancock_request_latency_seconds` | Histogram | `endpoint`, `mode`, `status` | Request latency (p50/p95/p99 via quantile queries) |
| `hancock_active_requests` | Gauge | `endpoint` | In-flight requests |
| `hancock_errors_by_endpoint_total` | Counter | `endpoint`, `status_code` | Errors per endpoint |
| `hancock_model_availability` | Gauge | `backend`, `model` | 1 = reachable, 0 = down |
| `hancock_tokens_used_estimated_total` | Counter | `model`, `endpoint` | Estimated token usage |
| `hancock_rate_limit_utilization` | Gauge | `ip` | Rate-limit usage (0.0–1.0) |
| `hancock_pentest_requests_total` | Counter | — | Pentest-mode request count |
| `hancock_soc_requests_total` | Counter | — | SOC-mode request count |
| `hancock_ciso_requests_total` | Counter | — | CISO-mode request count |

### Built-in (from Flask `/metrics` endpoint)

The `/metrics` endpoint also exposes basic counters in Prometheus text format:

```
hancock_requests_total <n>
hancock_errors_total <n>
hancock_requests_by_endpoint{endpoint="/v1/chat"} <n>
hancock_requests_by_mode{mode="soc"} <n>
```

---

## Grafana Dashboard

### Import the pre-built dashboard

1. Open Grafana at `http://localhost:3000`
2. Go to **Dashboards → Import**
3. Upload `monitoring/grafana_dashboard.json`
4. Select your Prometheus data source

Or regenerate the JSON:

```bash
python -m monitoring.prometheus_dashboard
# Writes monitoring/grafana_dashboard.json
```

### Dashboard panels

| Panel | Query | Description |
|---|---|---|
| Requests/sec | `rate(hancock_requests_total[1m])` | Real-time throughput |
| Error rate (%) | `rate(errors) / rate(total) * 100` | Error percentage |
| Active requests | `sum(hancock_active_requests)` | Concurrency |
| Latency p50 | `histogram_quantile(0.50, ...)` | Median response time |
| Latency p95 | `histogram_quantile(0.95, ...)` | 95th percentile |
| Latency p99 | `histogram_quantile(0.99, ...)` | 99th percentile |
| Tokens/min | `rate(hancock_tokens_used_estimated_total[1m]) * 60` | Token consumption |
| Model availability | `hancock_model_availability` | Backend status |
| Requests by mode | `increase(hancock_requests_by_mode[1h])` | Mode distribution |
| Rate limit util. | `hancock_rate_limit_utilization` | Per-IP utilisation |

---

## Alert Configuration

Alerting rules are in `monitoring/alerting_rules.yaml`.

### Load into Prometheus

```yaml
# prometheus.yml
rule_files:
  - /etc/prometheus/alerting_rules.yaml
```

### Alert summary

| Alert | Condition | Severity |
|---|---|---|
| `HancockHighErrorRate` | Error rate > 5% for 2m | Warning |
| `HancockCriticalErrorRate` | Error rate > 20% for 1m | Critical |
| `HancockSlowP99` | p99 latency > 5s for 3m | Warning |
| `HancockSlowP50` | p50 latency > 2s for 5m | Warning |
| `HancockModelUnavailable` | Model availability = 0 for 1m | Critical |
| `HancockRateLimitNearExhaustion` | Utilisation > 85% for 1m | Warning |
| `HancockRateLimitExhausted` | Utilisation ≥ 100% for 30s | Critical |
| `HancockMemoryLeak` | RSS grew > 25% in 30m for 10m | Warning |
| `HancockNoTraffic` | Zero requests for 10m | Info |

### Add Alertmanager routing (example)

```yaml
# alertmanager.yml
route:
  group_by: [alertname, service]
  receiver: slack-critical

receivers:
  - name: slack-critical
    slack_configs:
      - api_url: <slack_webhook_url>
        channel: "#security-alerts"
        title: "{{ .GroupLabels.alertname }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}"
```

---

## Custom Metrics

To extend metrics, import from `monitoring/metrics_exporter.py`:

```python
from monitoring.metrics_exporter import record_request, estimate_tokens

# After a model call:
tokens = estimate_tokens(response_text)
record_request(
    endpoint="/v1/chat",
    mode="soc",
    status=200,
    duration_s=1.23,
    tokens_estimated=tokens,
    model="llama3.1:8b",
)
```

---

## Troubleshooting

### Metrics endpoint returns 404

Ensure the server was started with `--server` flag:
```bash
python hancock_agent.py --server
```

### Prometheus can't scrape Hancock

1. Verify `METRICS_PORT` is set and port 8001 is exposed
2. Check firewall/security-group rules allow port 8001
3. Test manually: `curl http://localhost:8001/metrics`

### Grafana shows "No data"

1. Verify Prometheus data source URL is correct
2. Check Prometheus targets: `http://localhost:9090/targets`
3. Ensure scrape interval has elapsed (default 15s)

### Alerts not firing

1. Check `prometheus.yml` includes `rule_files`
2. Verify Alertmanager is configured and running
3. Test with: `curl -X POST http://localhost:9090/-/reload`
