#!/usr/bin/env python3
"""
deploy/graceful_shutdown.py — SIGTERM/SIGINT handler for the Hancock agent.

Registers signal handlers so that in-flight requests complete and resources
(DB connections, open files, thread pools) are cleaned up before the process
exits.  Designed to be imported early in hancock_agent.py or run as a wrapper.

Usage (standalone wrapper):
    python deploy/graceful_shutdown.py python hancock_agent.py --server

Usage (import):
    from deploy.graceful_shutdown import register_handlers
    register_handlers(on_shutdown=my_cleanup_fn)
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from typing import Callable, Optional


logger = logging.getLogger(__name__)

_shutdown_event = threading.Event()
_shutdown_timeout: int = int(os.environ.get("SHUTDOWN_TIMEOUT", "30"))


def _build_handler(
    on_shutdown: Optional[Callable[[], None]],
    timeout: int,
) -> Callable[[int, object], None]:
    def _handler(signum: int, frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — initiating graceful shutdown (timeout=%ds)", sig_name, timeout)
        print(f"\n[shutdown] Received {sig_name} — shutting down gracefully …", flush=True)

        _shutdown_event.set()

        if on_shutdown is not None:
            try:
                on_shutdown()
            except Exception as exc:  # noqa: BLE001
                logger.error("Error in shutdown callback: %s", exc)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if _is_idle():
                break
            time.sleep(0.5)
        else:
            logger.warning("Graceful shutdown timed out after %ds — forcing exit", timeout)
            print(f"[shutdown] Timeout after {timeout}s — forcing exit.", flush=True)

        logger.info("Shutdown complete.")
        print("[shutdown] Done.", flush=True)
        sys.exit(0)

    return _handler


def _is_idle() -> bool:
    """Hook: return True when the server has drained in-flight requests."""
    return True


def register_handlers(
    on_shutdown: Optional[Callable[[], None]] = None,
    timeout: int = _shutdown_timeout,
) -> threading.Event:
    """Register SIGTERM and SIGINT handlers.

    Args:
        on_shutdown: Optional callable invoked once the shutdown signal is
                     received (e.g. to flush buffers or close DB connections).
        timeout:     Seconds to wait for the server to drain before forcing
                     an exit.

    Returns:
        A threading.Event that is set when shutdown has been requested.
        Useful for long-running background threads to detect shutdown.
    """
    handler = _build_handler(on_shutdown, timeout)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    logger.debug("Graceful shutdown handlers registered (timeout=%ds)", timeout)
    return _shutdown_event


def shutdown_requested() -> bool:
    """Return True if a shutdown signal has been received."""
    return _shutdown_event.is_set()


def _run_child(argv: list[str]) -> None:
    """Wrap a child process and forward signals for container deployments."""
    proc = subprocess.Popen(argv)  # noqa: S603

    def _forward(signum: int, frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Forwarding %s to child PID %d", sig_name, proc.pid)
        proc.send_signal(signum)

    signal.signal(signal.SIGTERM, _forward)
    signal.signal(signal.SIGINT, _forward)

    try:
        sys.exit(proc.wait())
    except KeyboardInterrupt:
        proc.terminate()
        sys.exit(proc.wait())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: graceful_shutdown.py <command> [args …]", file=sys.stderr)
        sys.exit(1)

    _run_child(sys.argv[1:])
