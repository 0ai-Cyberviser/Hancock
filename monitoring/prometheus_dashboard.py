"""
Prometheus metrics endpoint helper for Hancock.

Provides a lightweight WSGI/Flask-compatible route that serves
the Prometheus text exposition format.  Falls back gracefully when
``prometheus_client`` is not installed.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    _PROM_AVAILABLE = True
except ImportError:
    _PROM_AVAILABLE = False
    logger.warning("prometheus_client not installed — /metrics endpoint will return 501")


def get_metrics_response() -> tuple[bytes, int, str]:
    """
    Return ``(body_bytes, http_status, content_type)`` for the metrics endpoint.

    Returns a 501 stub when ``prometheus_client`` is unavailable.
    """
    if _PROM_AVAILABLE:
        return generate_latest(REGISTRY), 200, CONTENT_TYPE_LATEST
    stub = b"# prometheus_client not installed\n"
    return stub, 501, "text/plain; charset=utf-8"


def register_metrics_route(app: object) -> None:
    """
    Register ``GET /metrics`` on the given Flask *app*.

    Parameters
    ----------
    app:
        A Flask ``Flask`` application instance.
    """
    try:
        from flask import Response  # type: ignore

        @app.route("/metrics")  # type: ignore[attr-defined]
        def metrics_endpoint():  # type: ignore[return]
            """Prometheus metrics scrape endpoint."""
            body, status, content_type = get_metrics_response()
            return Response(body, status=status, mimetype=content_type)

        logger.info("Registered GET /metrics endpoint")
    except ImportError:
        logger.warning("Flask not available — skipping /metrics route registration")


def serve_metrics_standalone(
    host: str = "0.0.0.0",
    port: int | None = None,
) -> None:
    """
    Start a standalone HTTP server that serves only the metrics endpoint.

    This is useful when running Hancock without Flask (e.g. a worker process).
    Port defaults to the ``PROMETHEUS_PORT`` environment variable, then ``9090``.
    """
    resolved_port = port or int(os.getenv("PROMETHEUS_PORT", "9090"))

    if not _PROM_AVAILABLE:
        logger.error("prometheus_client not installed — cannot start metrics server")
        return

    try:
        from prometheus_client import start_http_server
        start_http_server(resolved_port, addr=host)
        logger.info("Prometheus metrics server started on %s:%d", host, resolved_port)
    except Exception as exc:
        logger.error("Failed to start metrics server: %s", exc)
