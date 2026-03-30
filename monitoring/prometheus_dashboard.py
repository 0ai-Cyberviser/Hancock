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
            "rate(hancock_requests_total[2m])",
            legend="total",
        )],
        grid_pos={"x": 0, "y": 0, "w": 12, "h": 8},
        unit="reqps",
        description="Incoming request rate (all endpoints).",
    ))

    panels.append(timeseries_panel(
        panel_id=2,
        title="Error Rate (%)",
        targets=[_target(
            'rate(hancock_errors_total[2m]) '
            '/ (rate(hancock_requests_total[2m]) > 0) * 100',
            legend="error %",
        )],
        grid_pos={"x": 12, "y": 0, "w": 12, "h": 8},
        unit="percent",
        description="Percentage of errors over total requests.",
    ))

    # Row 2 – per-endpoint and per-mode breakdown
    panels.append(timeseries_panel(
        panel_id=3,
        title="Requests by Endpoint",
        targets=[_target(
            "hancock_requests_by_endpoint",
            legend="{{endpoint}}",
        )],
        grid_pos={"x": 0, "y": 8, "w": 12, "h": 8},
        unit="short",
        description="Cumulative request count per endpoint.",
    ))

    panels.append(timeseries_panel(
        panel_id=4,
        title="Requests by Mode",
        targets=[_target(
            "hancock_requests_by_mode",
            legend="{{mode}}",
        )],
        grid_pos={"x": 12, "y": 8, "w": 12, "h": 8},
        unit="short",
        description="Cumulative request count per specialist mode.",
    ))

    # Row 3 – memory (requires metrics_exporter gauge) and totals
    panels.append(timeseries_panel(
        panel_id=5,
        title="Memory Usage",
        targets=[_target(
            "hancock_memory_usage_bytes",
            legend="RSS",
        )],
        grid_pos={"x": 0, "y": 16, "w": 12, "h": 8},
        unit="bytes",
        description=(
            "Resident set size of the Hancock process. "
            "Available when metrics_exporter is wired into the agent."
        ),
    ))

    panels.append(timeseries_panel(
        panel_id=6,
        title="Active Connections",
        targets=[_target(
            "hancock_active_connections",
            legend="connections",
        )],
        grid_pos={"x": 12, "y": 16, "w": 12, "h": 8},
        unit="short",
        description=(
            "Current number of open HTTP connections. "
            "Available when metrics_exporter is wired into the agent."
        ),
    ))

    # Row 4 – stat panels
    panels.append(stat_panel(
        panel_id=7,
        title="Total Requests",
        targets=[_target(
            "hancock_requests_total",
            legend="total",
        )],
        grid_pos={"x": 0, "y": 24, "w": 6, "h": 4},
        unit="short",
    ))

    panels.append(stat_panel(
        panel_id=8,
        title="Total Errors",
        targets=[_target(
            "hancock_errors_total",
            legend="errors",
        )],
        grid_pos={"x": 6, "y": 24, "w": 6, "h": 4},
        unit="short",
    ))

    panels.append(stat_panel(
        panel_id=9,
        title="Current Memory (RSS)",
        targets=[_target(
            "hancock_memory_usage_bytes",
            legend="RSS",
        )],
        grid_pos={"x": 12, "y": 24, "w": 6, "h": 4},
        unit="bytes",
    ))

    panels.append(stat_panel(
        panel_id=10,
        title="Active Connections",
        targets=[_target(
            "hancock_active_connections",
            legend="connections",
        )],
        grid_pos={"x": 18, "y": 24, "w": 6, "h": 4},
        unit="short",
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
