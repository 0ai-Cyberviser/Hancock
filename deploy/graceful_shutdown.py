"""
Hancock graceful shutdown handler.

Registers SIGTERM and SIGINT handlers that:
1. Stop accepting new requests (sets a global shutdown flag)
2. Wait for in-flight requests to drain (up to a configurable timeout)
3. Close any open connections / cleanup resources
4. Exit cleanly

Usage (integrate into hancock_agent.py or your WSGI server)::

    from deploy.graceful_shutdown import install_handlers, shutdown_event

    install_handlers()

    # In your request handlers, check:
    if shutdown_event.is_set():
        return 503, "Service shutting down"
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time

logger = logging.getLogger(__name__)

# Global event that is set when a shutdown signal is received.
# Request handlers should check this to reject new work during draining.
shutdown_event = threading.Event()

# Default drain timeout in seconds (override via HANCOCK_DRAIN_TIMEOUT env var)
_DEFAULT_DRAIN_TIMEOUT = 30

_cleanup_callbacks: list = []
_installed = False


def register_cleanup(callback) -> None:
    """
    Register a zero-argument callable to be invoked during shutdown.

    Registered callbacks are called in LIFO order (last registered, first called).
    """
    _cleanup_callbacks.append(callback)


def _run_cleanup() -> None:
    """Execute all registered cleanup callbacks in LIFO order."""
    for cb in reversed(_cleanup_callbacks):
        try:
            cb()
        except Exception as exc:
            logger.error("Cleanup callback %r raised: %s", cb, exc)


def _signal_handler(signum: int, frame) -> None:
    sig_name = signal.Signals(signum).name
    logger.info("Received %s — initiating graceful shutdown", sig_name)

    # Signal new requests should be rejected
    shutdown_event.set()

    drain_timeout = int(os.getenv("HANCOCK_DRAIN_TIMEOUT", str(_DEFAULT_DRAIN_TIMEOUT)))
    logger.info("Draining in-flight requests (timeout=%ds)…", drain_timeout)

    # Give the server time to finish in-flight work
    time.sleep(min(drain_timeout, _DEFAULT_DRAIN_TIMEOUT))

    logger.info("Drain complete — running cleanup callbacks")
    _run_cleanup()

    logger.info("Shutdown complete — exiting")
    sys.exit(0)


def install_handlers(drain_timeout: int | None = None) -> None:
    """
    Install SIGTERM and SIGINT handlers for graceful shutdown.

    Safe to call multiple times — handlers are only installed once.

    Parameters
    ----------
    drain_timeout:
        Seconds to wait for in-flight requests to complete.
        Defaults to ``HANCOCK_DRAIN_TIMEOUT`` env var, then 30 s.
    """
    global _installed
    if _installed:
        return

    if drain_timeout is not None:
        os.environ.setdefault("HANCOCK_DRAIN_TIMEOUT", str(drain_timeout))

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    _installed = True
    logger.info(
        "Graceful shutdown handlers installed (drain timeout=%ss)",
        os.getenv("HANCOCK_DRAIN_TIMEOUT", str(_DEFAULT_DRAIN_TIMEOUT)),
    )


def is_shutting_down() -> bool:
    """Return True if a shutdown signal has been received."""
    return shutdown_event.is_set()
