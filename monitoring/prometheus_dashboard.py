"""
Hancock — Prometheus metrics dashboard definitions.

Registers all Hancock metrics with a shared CollectorRegistry and
exposes helper functions used by the Flask app.  Also generates the
Grafana dashboard JSON programmatically for easy version-controlling.

Usage (standalone — generates grafana_dashboard.json):
    python monitoring/prometheus_dashboard.py
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

# ── Re-export metrics from the exporter so importers need only one import ─────
from monitoring.metrics_exporter import (  # noqa: F401
    REQUEST_LATENCY,
    ACTIVE_REQUESTS,
    ERRORS_BY_ENDPOINT,
    MODEL_AVAILABILITY,
    TOKENS_USED,
    RATE_LIMIT_UTILIZATION,
    PENTEST_REQUESTS,
    SOC_REQUESTS,
    CISO_REQUESTS,
    record_request,
    estimate_tokens,
    start_metrics_server,
)


# ── Grafana dashboard JSON builder ────────────────────────────────────────────

def _panel(
    panel_id: int,
    title: str,
    panel_type: str,
    expr: str,
    grid_pos: dict[str, int],
    legend_format: str = "{{endpoint}}",
    unit: str = "short",
) -> dict[str, Any]:
    return {
        "id": panel_id,
        "title": title,
        "type": panel_type,
        "gridPos": grid_pos,
        "targets": [{"expr": expr, "legendFormat": legend_format, "refId": "A"}],
        "fieldConfig": {"defaults": {"unit": unit}},
        "options": {"tooltip": {"mode": "multi"}},
    }


def build_grafana_dashboard() -> dict[str, Any]:
    """Return the full Grafana dashboard JSON definition."""
    return {
        "__inputs": [],
        "__requires": [
            {"type": "grafana", "id": "grafana", "name": "Grafana", "version": "10.0.0"},
            {"type": "datasource", "id": "prometheus", "name": "Prometheus", "version": "1.0.0"},
        ],
        "annotations": {"list": []},
        "description": "Hancock AI Security Agent — Real-time operational dashboard",
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "panels": [
            # ── Row 1: Request overview ───────────────────────────────────────
            _panel(
                1, "Requests / second", "timeseries",
                "rate(hancock_requests_total[1m])",
                {"x": 0, "y": 0, "w": 8, "h": 8},
                legend_format="req/s", unit="reqps",
            ),
            _panel(
                2, "Error rate (%)", "timeseries",
                "100 * rate(hancock_errors_by_endpoint_total[1m]) / ignoring(endpoint, status_code)"
                " rate(hancock_requests_total[1m])",
                {"x": 8, "y": 0, "w": 8, "h": 8},
                legend_format="{{endpoint}}", unit="percent",
            ),
            _panel(
                3, "Active requests", "stat",
                "sum(hancock_active_requests)",
                {"x": 16, "y": 0, "w": 8, "h": 8},
                legend_format="active", unit="short",
            ),
            # ── Row 2: Latency ────────────────────────────────────────────────
            _panel(
                4, "Request latency p50 (s)", "timeseries",
                "histogram_quantile(0.50, sum(rate(hancock_request_latency_seconds_bucket[5m])) by (le, endpoint))",
                {"x": 0, "y": 8, "w": 8, "h": 8},
                legend_format="{{endpoint}} p50", unit="s",
            ),
            _panel(
                5, "Request latency p95 (s)", "timeseries",
                "histogram_quantile(0.95, sum(rate(hancock_request_latency_seconds_bucket[5m])) by (le, endpoint))",
                {"x": 8, "y": 8, "w": 8, "h": 8},
                legend_format="{{endpoint}} p95", unit="s",
            ),
            _panel(
                6, "Request latency p99 (s)", "timeseries",
                "histogram_quantile(0.99, sum(rate(hancock_request_latency_seconds_bucket[5m])) by (le, endpoint))",
                {"x": 16, "y": 8, "w": 8, "h": 8},
                legend_format="{{endpoint}} p99", unit="s",
            ),
            # ── Row 3: Model & tokens ─────────────────────────────────────────
            _panel(
                7, "Estimated tokens / min", "timeseries",
                "rate(hancock_tokens_used_estimated_total[1m]) * 60",
                {"x": 0, "y": 16, "w": 12, "h": 8},
                legend_format="{{model}}", unit="short",
            ),
            _panel(
                8, "Model availability", "stat",
                "hancock_model_availability",
                {"x": 12, "y": 16, "w": 12, "h": 8},
                legend_format="{{backend}} {{model}}", unit="short",
            ),
            # ── Row 4: Business metrics ───────────────────────────────────────
            _panel(
                9, "Requests by mode", "piechart",
                "increase(hancock_requests_by_mode[1h])",
                {"x": 0, "y": 24, "w": 12, "h": 8},
                legend_format="{{mode}}",
            ),
            _panel(
                10, "Rate limit utilisation", "timeseries",
                "hancock_rate_limit_utilization",
                {"x": 12, "y": 24, "w": 12, "h": 8},
                legend_format="{{ip}}", unit="percentunit",
            ),
        ],
        "refresh": "10s",
        "schemaVersion": 38,
        "tags": ["hancock", "cyberviser", "security"],
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Hancock — AI Security Agent",
        "uid": "hancock-v1",
        "version": 1,
    }


if __name__ == "__main__":
    dashboard = build_grafana_dashboard()
    out_path  = Path(__file__).parent / "grafana_dashboard.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(dashboard, fh, indent=2)
    print(f"Dashboard written to {out_path}")
