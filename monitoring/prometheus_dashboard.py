"""
Generate a Grafana dashboard JSON for Hancock Prometheus metrics.

Run directly to (re)generate monitoring/grafana_dashboard.json:

    python monitoring/prometheus_dashboard.py
"""

import json
import os

DATASOURCE = "Prometheus"
DASHBOARD_TITLE = "Hancock — Security AI Agent"
DASHBOARD_UID = "hancock-overview-v1"
REFRESH = "30s"
TAGS = ["hancock", "security", "ai"]


# ---------------------------------------------------------------------------
# Panel builder helpers
# ---------------------------------------------------------------------------

def _panel_base(panel_id, title, panel_type, grid_pos):
    return {
        "id": panel_id,
        "title": title,
        "type": panel_type,
        "gridPos": grid_pos,
        "datasource": DATASOURCE,
    }


def timeseries_panel(panel_id, title, targets, grid_pos, unit="short",
                     description=""):
    panel = _panel_base(panel_id, title, "timeseries", grid_pos)
    panel["description"] = description
    panel["fieldConfig"] = {
        "defaults": {
            "unit": unit,
            "custom": {"lineWidth": 2, "fillOpacity": 10},
        },
        "overrides": [],
    }
    panel["options"] = {"tooltip": {"mode": "multi"}, "legend": {"displayMode": "list"}}
    panel["targets"] = targets
    return panel


def stat_panel(panel_id, title, targets, grid_pos, unit="short",
               description=""):
    panel = _panel_base(panel_id, title, "stat", grid_pos)
    panel["description"] = description
    panel["fieldConfig"] = {
        "defaults": {"unit": unit},
        "overrides": [],
    }
    panel["options"] = {
        "reduceOptions": {"calcs": ["lastNotNull"]},
        "colorMode": "background",
        "graphMode": "area",
        "textMode": "auto",
    }
    panel["targets"] = targets
    return panel


def _target(expr, legend="{{endpoint}}"):
    return {
        "expr": expr,
        "legendFormat": legend,
        "refId": "A",
        "datasource": DATASOURCE,
    }


# ---------------------------------------------------------------------------
# Dashboard assembly
# ---------------------------------------------------------------------------

def build_dashboard():
    panels = []

    # Row 1 – request throughput & error rate
    panels.append(timeseries_panel(
        panel_id=1,
        title="Request Rate (req/s)",
        targets=[_target(
            "sum(rate(hancock_requests_total[2m])) by (endpoint)",
            legend="{{endpoint}}",
        )],
        grid_pos={"x": 0, "y": 0, "w": 12, "h": 8},
        unit="reqps",
        description="Incoming request rate per endpoint.",
    ))

    panels.append(timeseries_panel(
        panel_id=2,
        title="Error Rate (%)",
        targets=[_target(
            'sum(rate(hancock_requests_total{status=~"5.."}[2m])) '
            '/ sum(rate(hancock_requests_total[2m])) * 100',
            legend="error %",
        )],
        grid_pos={"x": 12, "y": 0, "w": 12, "h": 8},
        unit="percent",
        description="Percentage of 5xx responses over total requests.",
    ))

    # Row 2 – latency
    panels.append(timeseries_panel(
        panel_id=3,
        title="Request Duration p50 / p95 / p99",
        targets=[
            {
                "expr": (
                    "histogram_quantile(0.50, "
                    "sum(rate(hancock_request_duration_seconds_bucket[2m])) "
                    "by (le))"
                ),
                "legendFormat": "p50",
                "refId": "A",
                "datasource": DATASOURCE,
            },
            {
                "expr": (
                    "histogram_quantile(0.95, "
                    "sum(rate(hancock_request_duration_seconds_bucket[2m])) "
                    "by (le))"
                ),
                "legendFormat": "p95",
                "refId": "B",
                "datasource": DATASOURCE,
            },
            {
                "expr": (
                    "histogram_quantile(0.99, "
                    "sum(rate(hancock_request_duration_seconds_bucket[2m])) "
                    "by (le))"
                ),
                "legendFormat": "p99",
                "refId": "C",
                "datasource": DATASOURCE,
            },
        ],
        grid_pos={"x": 0, "y": 8, "w": 12, "h": 8},
        unit="s",
        description="Request latency percentiles.",
    ))

    panels.append(timeseries_panel(
        panel_id=4,
        title="Model Response Time p50 / p99",
        targets=[
            {
                "expr": (
                    "histogram_quantile(0.50, "
                    "sum(rate(hancock_model_response_time_seconds_bucket[2m])) "
                    "by (le, model))"
                ),
                "legendFormat": "{{model}} p50",
                "refId": "A",
                "datasource": DATASOURCE,
            },
            {
                "expr": (
                    "histogram_quantile(0.99, "
                    "sum(rate(hancock_model_response_time_seconds_bucket[2m])) "
                    "by (le, model))"
                ),
                "legendFormat": "{{model}} p99",
                "refId": "B",
                "datasource": DATASOURCE,
            },
        ],
        grid_pos={"x": 12, "y": 8, "w": 12, "h": 8},
        unit="s",
        description="Model inference latency percentiles.",
    ))

    # Row 3 – rate limiting, memory, connections
    panels.append(timeseries_panel(
        panel_id=5,
        title="Rate Limit Exceeded (events/s)",
        targets=[_target(
            "sum(rate(hancock_rate_limit_exceeded_total[2m])) by (endpoint)",
            legend="{{endpoint}}",
        )],
        grid_pos={"x": 0, "y": 16, "w": 8, "h": 8},
        unit="short",
        description="Rate at which requests are rejected by the rate limiter.",
    ))

    panels.append(timeseries_panel(
        panel_id=6,
        title="Memory Usage",
        targets=[_target(
            "hancock_memory_usage_bytes",
            legend="RSS",
        )],
        grid_pos={"x": 8, "y": 16, "w": 8, "h": 8},
        unit="bytes",
        description="Resident set size of the Hancock process.",
    ))

    panels.append(timeseries_panel(
        panel_id=7,
        title="Active Connections",
        targets=[_target(
            "hancock_active_connections",
            legend="connections",
        )],
        grid_pos={"x": 16, "y": 16, "w": 8, "h": 8},
        unit="short",
        description="Current number of open HTTP connections.",
    ))

    # Row 4 – stat panels
    panels.append(stat_panel(
        panel_id=8,
        title="Total Requests",
        targets=[_target(
            "sum(hancock_requests_total)",
            legend="total",
        )],
        grid_pos={"x": 0, "y": 24, "w": 6, "h": 4},
        unit="short",
    ))

    panels.append(stat_panel(
        panel_id=9,
        title="Total Rate-Limit Events",
        targets=[_target(
            "sum(hancock_rate_limit_exceeded_total)",
            legend="total",
        )],
        grid_pos={"x": 6, "y": 24, "w": 6, "h": 4},
        unit="short",
    ))

    panels.append(stat_panel(
        panel_id=10,
        title="p99 Request Duration",
        targets=[_target(
            "histogram_quantile(0.99, "
            "sum(rate(hancock_request_duration_seconds_bucket[5m])) by (le))",
            legend="p99",
        )],
        grid_pos={"x": 12, "y": 24, "w": 6, "h": 4},
        unit="s",
    ))

    panels.append(stat_panel(
        panel_id=11,
        title="Current Memory (RSS)",
        targets=[_target(
            "hancock_memory_usage_bytes",
            legend="RSS",
        )],
        grid_pos={"x": 18, "y": 24, "w": 6, "h": 4},
        unit="bytes",
    ))

    dashboard = {
        "__inputs": [
            {
                "name": "DS_PROMETHEUS",
                "label": "Prometheus",
                "description": "",
                "type": "datasource",
                "pluginId": "prometheus",
                "pluginName": "Prometheus",
            }
        ],
        "__requires": [
            {"type": "grafana", "id": "grafana", "name": "Grafana",
             "version": "10.0.0"},
            {"type": "datasource", "id": "prometheus", "name": "Prometheus",
             "version": "1.0.0"},
        ],
        "id": None,
        "uid": DASHBOARD_UID,
        "title": DASHBOARD_TITLE,
        "tags": TAGS,
        "timezone": "browser",
        "schemaVersion": 38,
        "version": 1,
        "refresh": REFRESH,
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {},
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "panels": panels,
        "templating": {"list": []},
        "annotations": {"list": []},
        "links": [],
    }
    return dashboard


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def generate(output_path=None):
    """Generate dashboard JSON and write to *output_path*."""
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(__file__), "grafana_dashboard.json"
        )
    dashboard = build_dashboard()
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(dashboard, fh, indent=2)
        fh.write("\n")
    return output_path


if __name__ == "__main__":
    path = generate()
    print(f"Dashboard written to {path}")
