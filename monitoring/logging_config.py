"""
Hancock structured logging configuration.

Sets up JSON-formatted logging using ``python-json-logger`` with
request-ID correlation via ``contextvars``.  Falls back to plain
text logging when ``python-json-logger`` is not installed.
"""
from __future__ import annotations

import logging
import logging.config
import os
from contextvars import ContextVar
from typing import Any

# Context variable that holds the current request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# ── Try to import pythonjsonlogger ────────────────────────────────────────────
try:
    from pythonjsonlogger import jsonlogger as _jsonlogger  # type: ignore
    _JSON_LOGGER_AVAILABLE = True
except ImportError:
    _JSON_LOGGER_AVAILABLE = False


class _RequestIdFilter(logging.Filter):
    """Inject the current request ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        record.request_id = request_id_var.get("")  # type: ignore[attr-defined]
        return True


class _JsonFormatter(_jsonlogger.JsonFormatter if _JSON_LOGGER_AVAILABLE else logging.Formatter):  # type: ignore[misc]
    """Custom JSON formatter that includes the request ID field."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)  # type: ignore[arg-type]
        log_record["request_id"] = getattr(record, "request_id", "")
        log_record["logger"] = record.name
        log_record["level"] = record.levelname


def configure_logging(
    level: str | None = None,
    json_output: bool | None = None,
) -> None:
    """
    Configure the root logger for Hancock.

    Parameters
    ----------
    level:
        Log level string (e.g. ``"INFO"``).  Falls back to the
        ``HANCOCK_LOG_LEVEL`` environment variable, then ``"INFO"``.
    json_output:
        Force JSON output (``True``) or plain text (``False``).
        Falls back to ``HANCOCK_LOG_JSON`` env var, then auto-detects
        based on whether ``python-json-logger`` is installed.
    """
    resolved_level = (
        level
        or os.getenv("HANCOCK_LOG_LEVEL", "INFO")
    ).upper()

    if json_output is None:
        json_env = os.getenv("HANCOCK_LOG_JSON", "").lower()
        json_output = json_env in ("1", "true", "yes") if json_env else _JSON_LOGGER_AVAILABLE

    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())

    if json_output and _JSON_LOGGER_AVAILABLE:
        formatter: logging.Formatter = _JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(resolved_level)
    # Remove pre-existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger(__name__).info(
        "Logging configured: level=%s json=%s", resolved_level, json_output
    )
