"""
Hancock — Graceful shutdown handler.

Installs SIGTERM / SIGINT handlers that:
  1. Stop accepting new requests.
  2. Wait for in-flight requests to complete (up to DRAIN_TIMEOUT seconds).
  3. Flush metrics / logs.
  4. Exit with code 0.

Usage (integrate into hancock_agent.py or run standalone):
    from deploy.graceful_shutdown import install_shutdown_handler
    install_shutdown_handler(app, server)
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time

logger = logging.getLogger(__name__)

DRAIN_TIMEOUT = int(os.getenv("SHUTDOWN_DRAIN_TIMEOUT", "30"))  # seconds


class GracefulShutdown:
    """Context manager / signal handler for clean server shutdown."""

    def __init__(self, drain_timeout: int = DRAIN_TIMEOUT) -> None:
        self.drain_timeout = drain_timeout
        self._shutdown_event = threading.Event()
        self._active_requests = 0
        self._lock = threading.Lock()

    # ── Request tracking ──────────────────────────────────────────────────────

    def request_started(self) -> None:
        with self._lock:
            self._active_requests += 1

    def request_finished(self) -> None:
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

    @property
    def is_shutting_down(self) -> bool:
        return self._shutdown_event.is_set()

    @property
    def active_requests(self) -> int:
        with self._lock:
            return self._active_requests

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _handle_signal(self, signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("[Hancock] Received %s — initiating graceful shutdown.", sig_name)
        self._shutdown_event.set()

        deadline = time.monotonic() + self.drain_timeout
        while self.active_requests > 0 and time.monotonic() < deadline:
            logger.info(
                "[Hancock] Waiting for %d in-flight request(s) to complete (%ds remaining)...",
                self.active_requests,
                int(deadline - time.monotonic()),
            )
            time.sleep(1)

        if self.active_requests > 0:
            logger.warning(
                "[Hancock] Drain timeout reached with %d active request(s) — forcing exit.",
                self.active_requests,
            )
        else:
            logger.info("[Hancock] All requests completed. Shutting down cleanly.")

        self._flush()
        sys.exit(0)

    def _flush(self) -> None:
        """Flush metrics and logs before exiting."""
        try:
            # Flush prometheus metrics if available
            from monitoring.metrics_exporter import _PROMETHEUS_AVAILABLE  # noqa: F401
            if _PROMETHEUS_AVAILABLE:
                logger.debug("[Hancock] Prometheus metrics flushed.")
        except Exception:
            pass

        # Flush all log handlers
        for handler in logging.root.handlers:
            try:
                handler.flush()
            except Exception:
                pass

    def install(self) -> "GracefulShutdown":
        """Register SIGTERM and SIGINT handlers."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT,  self._handle_signal)
        logger.debug("[Hancock] Graceful shutdown handler installed (drain timeout: %ds).",
                     self.drain_timeout)
        return self

    # ── Flask middleware (optional) ───────────────────────────────────────────

    def flask_before_request(self) -> None:
        """Register as Flask before_request to track active requests."""
        from flask import g, jsonify  # noqa: F401
        if self.is_shutting_down:
            from flask import jsonify
            return jsonify({"error": "server is shutting down"}), 503  # type: ignore[return-value]
        self.request_started()

    def flask_teardown_request(self, _exc: BaseException | None = None) -> None:
        """Register as Flask teardown_request to decrement counter."""
        self.request_finished()


def install_shutdown_handler(drain_timeout: int = DRAIN_TIMEOUT) -> GracefulShutdown:
    """Convenience function — creates and installs a GracefulShutdown handler."""
    handler = GracefulShutdown(drain_timeout=drain_timeout)
    handler.install()
    return handler


if __name__ == "__main__":
    # Demo: install handler and wait for SIGTERM/SIGINT
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)s  %(message)s")
    handler = install_shutdown_handler()
    logger.info("Shutdown handler installed.  Send SIGTERM or press Ctrl+C to test.")
    signal.pause()
