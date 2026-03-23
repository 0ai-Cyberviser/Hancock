"""
Prometheus metrics exporter for the Hancock security AI agent.

Exports histograms, counters, and gauges for request tracking, model
performance, rate-limiting, memory usage, and active connections.
Gracefully degrades to no-op stubs when prometheus_client is not installed.
"""

import contextlib
import time

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PROMETHEUS_AVAILABLE = False


# ---------------------------------------------------------------------------
# No-op fallback classes
# ---------------------------------------------------------------------------

class _NoOpHistogram:
    """No-op histogram stub used when prometheus_client is unavailable."""

    class _Timer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def observe(self, amount):
        pass

    def labels(self, **kwargs):
        return self

    def time(self):
        return self._Timer()


class _NoOpCounter:
    """No-op counter stub used when prometheus_client is unavailable."""

    def inc(self, amount=1):
        pass

    def labels(self, **kwargs):
        return self


class _NoOpGauge:
    """No-op gauge stub used when prometheus_client is unavailable."""

    def set(self, value):
        pass

    def inc(self, amount=1):
        pass

    def dec(self, amount=1):
        pass

    def labels(self, **kwargs):
        return self

    def set_function(self, fn):
        pass


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

if _PROMETHEUS_AVAILABLE:
    REQUEST_DURATION = Histogram(
        "hancock_request_duration_seconds",
        "End-to-end HTTP request duration in seconds",
        ["endpoint", "method", "status_code"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    REQUESTS_TOTAL = Counter(
        "hancock_requests_total",
        "Total HTTP requests handled",
        ["endpoint", "status"],
    )

    MODEL_RESPONSE_TIME = Histogram(
        "hancock_model_response_time_seconds",
        "Time spent waiting for model inference",
        ["model", "operation"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    )

    RATE_LIMIT_EXCEEDED = Counter(
        "hancock_rate_limit_exceeded_total",
        "Number of requests rejected due to rate limiting",
        ["endpoint", "client_id"],
    )

    MEMORY_USAGE = Gauge(
        "hancock_memory_usage_bytes",
        "Current process resident memory in bytes",
    )

    ACTIVE_CONNECTIONS = Gauge(
        "hancock_active_connections",
        "Number of currently active HTTP connections",
    )
else:  # pragma: no cover
    REQUEST_DURATION = _NoOpHistogram()
    REQUESTS_TOTAL = _NoOpCounter()
    MODEL_RESPONSE_TIME = _NoOpHistogram()
    RATE_LIMIT_EXCEEDED = _NoOpCounter()
    MEMORY_USAGE = _NoOpGauge()
    ACTIVE_CONNECTIONS = _NoOpGauge()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def track_request(endpoint, method="GET", status_code="200"):
    """Context manager that records request duration and increments counter."""
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        REQUEST_DURATION.labels(
            endpoint=endpoint,
            method=method,
            status_code=str(status_code),
        ).observe(elapsed)
        REQUESTS_TOTAL.labels(endpoint=endpoint, status=str(status_code)).inc()


@contextlib.contextmanager
def track_model_call(model="hancock", operation="infer"):
    """Context manager that records model inference latency."""
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        MODEL_RESPONSE_TIME.labels(model=model, operation=operation).observe(elapsed)


def record_rate_limit(endpoint="unknown", client_id="unknown"):
    """Increment the rate-limit-exceeded counter."""
    RATE_LIMIT_EXCEEDED.labels(endpoint=endpoint, client_id=client_id).inc()


def update_memory_usage():
    """Refresh the memory gauge from /proc/self/status (Linux) or psutil."""
    try:
        import resource
        usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        MEMORY_USAGE.set(usage_kb * 1024)
        return
    except Exception:
        pass
    try:
        import psutil
        proc = psutil.Process()
        MEMORY_USAGE.set(proc.memory_info().rss)
    except Exception:
        pass


def start_metrics_server(port=9090):
    """Start the Prometheus HTTP metrics server on *port*."""
    if not _PROMETHEUS_AVAILABLE:
        return
    start_http_server(port)
