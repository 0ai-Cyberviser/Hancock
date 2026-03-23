"""
Hancock metrics exporter — Prometheus instrumentation.

Exposes histograms, gauges, and counters for key Hancock signals.
Falls back to no-op stubs when ``prometheus_client`` is not installed
so the agent can run without the monitoring stack in development.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Try to import prometheus_client; fall back to no-ops ──────────────────────

try:
    from prometheus_client import Counter, Gauge, Histogram, REGISTRY  # noqa: F401

    _PROM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PROM_AVAILABLE = False
    logger.warning(
        "prometheus_client not installed — metrics will be no-ops. "
        "Install with: pip install prometheus-client"
    )

# ── Metric definitions ─────────────────────────────────────────────────────────

if _PROM_AVAILABLE:
    REQUEST_LATENCY = Histogram(
        "hancock_request_latency_seconds",
        "End-to-end HTTP request latency in seconds",
        ["method", "endpoint", "status_code"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    ACTIVE_REQUESTS = Gauge(
        "hancock_active_requests",
        "Number of HTTP requests currently being processed",
        ["endpoint"],
    )

    MODEL_INFERENCE_TIME = Histogram(
        "hancock_model_inference_seconds",
        "Model inference latency in seconds",
        ["model", "mode"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    )

    ERROR_COUNTER = Counter(
        "hancock_errors_total",
        "Total number of errors by type",
        ["error_type", "endpoint"],
    )

    RATE_LIMIT_COUNTER = Counter(
        "hancock_rate_limit_hits_total",
        "Total number of rate-limit rejections",
        ["endpoint"],
    )

    REQUEST_COUNTER = Counter(
        "hancock_requests_total",
        "Total HTTP requests processed",
        ["method", "endpoint", "status_code"],
    )
else:
    # ── No-op stubs ───────────────────────────────────────────────────────────
    class _NoOpContextManager:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class _NoOpHistogram:
        def labels(self, **kwargs):
            return self

        def observe(self, value):
            pass

        def time(self):
            return _NoOpContextManager()

    class _NoOpGauge:
        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            pass

        def dec(self, amount=1):
            pass

        def set(self, value):
            pass

    class _NoOpCounter:
        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            pass

    REQUEST_LATENCY = _NoOpHistogram()
    ACTIVE_REQUESTS = _NoOpGauge()
    MODEL_INFERENCE_TIME = _NoOpHistogram()
    ERROR_COUNTER = _NoOpCounter()
    RATE_LIMIT_COUNTER = _NoOpCounter()
    REQUEST_COUNTER = _NoOpCounter()


# ── Public helper functions ────────────────────────────────────────────────────

def record_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Record an HTTP request's outcome and latency."""
    labels = {"method": method, "endpoint": endpoint, "status_code": str(status_code)}
    REQUEST_LATENCY.labels(**labels).observe(duration)
    REQUEST_COUNTER.labels(**labels).inc()


def record_inference(model: str, mode: str, duration: float) -> None:
    """Record a model inference call's latency."""
    MODEL_INFERENCE_TIME.labels(model=model, mode=mode).observe(duration)


def increment_error(error_type: str, endpoint: str = "unknown") -> None:
    """Increment the error counter for the given error type."""
    ERROR_COUNTER.labels(error_type=error_type, endpoint=endpoint).inc()


def increment_rate_limit(endpoint: str) -> None:
    """Increment the rate-limit counter for the given endpoint."""
    RATE_LIMIT_COUNTER.labels(endpoint=endpoint).inc()


def set_active_requests(endpoint: str, count: int) -> None:
    """Set the active-request gauge for a given endpoint."""
    ACTIVE_REQUESTS.labels(endpoint=endpoint).set(count)
