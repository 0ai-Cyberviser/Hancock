"""
Structured JSON logging with request-ID correlation for Hancock.

Usage
-----
    from monitoring.logging_config import configure_logging, get_logger

    configure_logging(level="INFO")
    logger = get_logger(__name__)
    logger.info("started", extra={"request_id": "abc-123", "user": "alice"})

The ``RequestIdFilter`` can be attached to Flask via ``before_request`` /
``teardown_request`` hooks so every log line emitted during a request
automatically carries the request-ID without explicit passing.
"""

import datetime
import json
import logging
import time
import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


# ---------------------------------------------------------------------------
# Request-ID helpers
# ---------------------------------------------------------------------------

def get_request_id():
    """Return the current context-local request-ID, or a new UUID."""
    return _request_id_var.get() or str(uuid.uuid4())


def set_request_id(request_id=None):
    """Set the context-local request-ID (generate one if omitted)."""
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def clear_request_id():
    """Clear the context-local request-ID at end of request."""
    _request_id_var.set(None)


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

    def format(self, record):
        ts = datetime.datetime.fromtimestamp(
            record.created, tz=datetime.timezone.utc
        )
        payload = {
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{ts.microsecond // 1000:03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", get_request_id()),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Merge any extra fields that aren't part of the standard LogRecord
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Filter — injects request_id into every record
# ---------------------------------------------------------------------------

class RequestIdFilter(logging.Filter):
    """Inject the current request-ID into every log record."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure_logging(level="INFO", service_name="hancock"):
    """
    Configure root logger with structured JSON output.

    Parameters
    ----------
    level:        Logging level string ("DEBUG", "INFO", "WARNING", "ERROR").
    service_name: Appears in the ``service`` field of every log record.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "werkzeug", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger = logging.getLogger(service_name)
    logger.info("Logging configured", extra={
        "service": service_name, "log_level": level
    })
    return logger


def get_logger(name=None):
    """Return a logger for *name* with the RequestIdFilter attached."""
    logger = logging.getLogger(name)
    if not any(isinstance(f, RequestIdFilter) for f in logger.filters):
        logger.addFilter(RequestIdFilter())
    return logger


# ---------------------------------------------------------------------------
# Optional Flask integration
# ---------------------------------------------------------------------------

def init_flask_logging(app):
    """
    Attach request-ID lifecycle hooks to a Flask *app*.

    Reads ``X-Request-ID`` from incoming headers, or generates a new UUID.
    The same ID is echoed back in the response as ``X-Request-ID``.
    """
    try:
        from flask import g, request
    except ImportError:
        return

    @app.before_request
    def _on_request_start():
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = set_request_id(rid)
        g.request_start_perf = time.perf_counter()

        payload = request.get_json(silent=True) if request.is_json else {}
        mode = payload.get("mode", "n/a") if isinstance(payload, dict) else "n/a"
        g.request_mode = mode
        logging.getLogger("hancock.request").info(
            "request_started",
            extra={
                "event": "request_started",
                "method": request.method,
                "endpoint": request.path,
                "mode": mode,
                "request_id": g.request_id,
            },
        )

    @app.after_request
    def _after_request(response):
        rid = getattr(g, "request_id", get_request_id())
        started = getattr(g, "request_start_perf", None)
        latency_ms = round((time.perf_counter() - started) * 1000, 2) if started else None
        mode = getattr(g, "request_mode", "n/a")
        response.headers["X-Request-ID"] = rid

        logging.getLogger("hancock.request").info(
            "request_completed",
            extra={
                "event": "request_completed",
                "method": request.method,
                "endpoint": request.path,
                "mode": mode,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "request_id": rid,
            },
        )
        return response

    @app.teardown_request
    def _on_request_teardown(_exc):
        clear_request_id()
