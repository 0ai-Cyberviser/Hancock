"""
Hancock — Prometheus metrics exporter.

Provides Prometheus-compatible metric objects that can be imported by any
Hancock module.  Uses the official prometheus_client library when available,
with a lightweight pure-Python fallback so the agent always starts even if
prometheus_client is not installed.

Usage:
    from monitoring.metrics_exporter import (
        REQUEST_LATENCY, ACTIVE_REQUESTS, ERRORS_BY_ENDPOINT,
        MODEL_AVAILABILITY, TOKENS_USED, RATE_LIMIT_UTILIZATION,
        record_request, start_metrics_server,
    )
"""
from __future__ import annotations

import os
import time
from typing import Any

# ── Prometheus client (optional) ──────────────────────────────────────────────
try:
    from prometheus_client import (  # type: ignore
        Counter, Gauge, Histogram, CollectorRegistry, start_http_server,
        REGISTRY,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

# ── Metric definitions ────────────────────────────────────────────────────────

if _PROMETHEUS_AVAILABLE:
    REQUEST_LATENCY = Histogram(
        "hancock_request_latency_seconds",
        "Request latency in seconds",
        ["endpoint", "mode", "status"],
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    ACTIVE_REQUESTS = Gauge(
        "hancock_active_requests",
        "Number of requests currently being processed",
        ["endpoint"],
    )

    ERRORS_BY_ENDPOINT = Counter(
        "hancock_errors_by_endpoint_total",
        "Total errors grouped by endpoint and HTTP status code",
        ["endpoint", "status_code"],
    )

    MODEL_AVAILABILITY = Gauge(
        "hancock_model_availability",
        "1 if the model backend is reachable, 0 otherwise",
        ["backend", "model"],
    )

    TOKENS_USED = Counter(
        "hancock_tokens_used_estimated_total",
        "Estimated tokens consumed (input + output)",
        ["model", "endpoint"],
    )

    RATE_LIMIT_UTILIZATION = Gauge(
        "hancock_rate_limit_utilization",
        "Current rate-limit slot utilisation (0.0 – 1.0) per source IP",
        ["ip"],
    )

    PENTEST_REQUESTS = Counter(
        "hancock_pentest_requests_total",
        "Total pentest-mode requests",
    )

    SOC_REQUESTS = Counter(
        "hancock_soc_requests_total",
        "Total SOC-mode requests",
    )

    CISO_REQUESTS = Counter(
        "hancock_ciso_requests_total",
        "Total CISO-mode requests",
    )

else:
    # ── No-op stubs so imports never fail ─────────────────────────────────────
    class _NoopMetric:
        def labels(self, **_: Any) -> "_NoopMetric":
            return self
        def observe(self, _: float) -> None: ...
        def inc(self, _: float = 1) -> None: ...
        def dec(self, _: float = 1) -> None: ...
        def set(self, _: float) -> None: ...

    _noop = _NoopMetric()
    REQUEST_LATENCY        = _noop  # type: ignore[assignment]
    ACTIVE_REQUESTS        = _noop  # type: ignore[assignment]
    ERRORS_BY_ENDPOINT     = _noop  # type: ignore[assignment]
    MODEL_AVAILABILITY     = _noop  # type: ignore[assignment]
    TOKENS_USED            = _noop  # type: ignore[assignment]
    RATE_LIMIT_UTILIZATION = _noop  # type: ignore[assignment]
    PENTEST_REQUESTS       = _noop  # type: ignore[assignment]
    SOC_REQUESTS           = _noop  # type: ignore[assignment]
    CISO_REQUESTS          = _noop  # type: ignore[assignment]


# ── Helper utilities ──────────────────────────────────────────────────────────

def record_request(endpoint: str, mode: str, status: int, duration_s: float,
                   tokens_estimated: int = 0, model: str = "") -> None:
    """Update all relevant metrics after a request completes."""
    label = str(status)
    REQUEST_LATENCY.labels(endpoint=endpoint, mode=mode, status=label).observe(duration_s)
    if status >= 400:
        ERRORS_BY_ENDPOINT.labels(endpoint=endpoint, status_code=label).inc()
    if tokens_estimated and model:
        TOKENS_USED.labels(model=model, endpoint=endpoint).inc(tokens_estimated)
    if mode == "pentest":
        PENTEST_REQUESTS.inc()
    elif mode == "soc":
        SOC_REQUESTS.inc()
    elif mode == "ciso":
        CISO_REQUESTS.inc()


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token (GPT-style)."""
    return max(1, len(text) // 4)


def start_metrics_server(port: int | None = None) -> None:
    """Start a standalone Prometheus HTTP server on *port* (default: $METRICS_PORT or 8001)."""
    if not _PROMETHEUS_AVAILABLE:
        import logging
        logging.getLogger(__name__).warning(
            "prometheus_client not installed — metrics server not started. "
            "Run: pip install prometheus-client"
        )
        return
    port = port or int(os.getenv("METRICS_PORT", "8001"))
    start_http_server(port)
    import logging
    logging.getLogger(__name__).info("Prometheus metrics server started on port %d", port)
