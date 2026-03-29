"""
Hancock — Structured logging configuration.

Provides JSON-formatted logging with request ID correlation and
optional file output for production deployments.

Usage:
    from monitoring.logging_config import configure_logging
    configure_logging()
"""
from __future__ import annotations

import contextvars
import logging
import logging.handlers
import os
import sys
import uuid
from typing import Any

# Optional: python-json-logger for structured output
try:
    from pythonjsonlogger import jsonlogger  # type: ignore
    _JSON_AVAILABLE = True
except ImportError:
    _JSON_AVAILABLE = False

# Thread-safe / async-safe request ID storage
_current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "hancock_request_id", default=""
)


class RequestIdFilter(logging.Filter):
    """Inject a per-request correlation ID into every log record.

    Uses ``contextvars.ContextVar`` so each thread / async task gets its
    own request ID without cross-contamination.
    """

    @staticmethod
    def set_request_id(request_id: str) -> None:
        _current_request_id.set(request_id)

    @staticmethod
    def new_request_id() -> str:
        rid = str(uuid.uuid4())[:8]
        _current_request_id.set(rid)
        return rid

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = _current_request_id.get() or "-"
        return True


def configure_logging(
    level: str | None = None,
    log_format: str | None = None,
    log_to_file: bool | None = None,
    log_file_path: str | None = None,
) -> logging.Logger:
    """Configure root logger for Hancock.

    All parameters fall back to environment variables when not provided.

    Args:
        level:         Log level string (DEBUG/INFO/WARNING/ERROR/CRITICAL).
        log_format:    "json" for structured output, "text" for human-readable.
        log_to_file:   Whether to also write logs to a file.
        log_file_path: Path for the log file.

    Returns:
        The configured root logger.
    """
    level       = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format  = log_format or os.getenv("LOG_FORMAT", "text").lower()
    log_to_file = log_to_file if log_to_file is not None else (
        os.getenv("LOG_TO_FILE", "false").lower() == "true"
    )
    log_file_path = log_file_path or os.getenv("LOG_FILE_PATH", "/var/log/hancock.log")

    numeric_level = getattr(logging, level, logging.INFO)
    root_logger   = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    request_filter = RequestIdFilter()

    if log_format == "json" and _JSON_AVAILABLE:
        formatter: logging.Formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(request_id)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  [%(request_id)s]  %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_filter)
    root_logger.addHandler(console_handler)

    # Optional file handler with rotation
    if log_to_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(request_filter)
            root_logger.addHandler(file_handler)
        except OSError as exc:
            root_logger.warning("Could not open log file %s: %s", log_file_path, exc)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (call configure_logging first)."""
    return logging.getLogger(name)
