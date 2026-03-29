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
    """Return the full Grafana dashboard JSON definition.

    Queries reference only the metrics currently emitted by the
    ``hancock_agent.py`` ``/metrics`` endpoint:

    * ``hancock_requests_total``
    * ``hancock_errors_total``
    * ``hancock_requests_by_endpoint``
    * ``hancock_requests_by_mode``
    """
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
                "100 * rate(hancock_errors_total[1m])"
                " / rate(hancock_requests_total[1m])",
                {"x": 8, "y": 0, "w": 8, "h": 8},
                legend_format="error %", unit="percent",
            ),
            _panel(
                3, "Requests by endpoint", "timeseries",
                "increase(hancock_requests_by_endpoint[1h])",
                {"x": 16, "y": 0, "w": 8, "h": 8},
                legend_format="{{endpoint}}", unit="short",
            ),
            # ── Row 2: Business metrics ───────────────────────────────────────
            _panel(
                4, "Requests by mode", "piechart",
                "increase(hancock_requests_by_mode[1h])",
                {"x": 0, "y": 8, "w": 12, "h": 8},
                legend_format="{{mode}}",
            ),
            _panel(
                5, "Total errors", "stat",
                "hancock_errors_total",
                {"x": 12, "y": 8, "w": 12, "h": 8},
                legend_format="errors", unit="short",
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
