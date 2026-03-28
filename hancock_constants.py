"""Shared constants for Hancock modules.

Centralizes configuration values, limits, and defaults that are referenced
across hancock_agent, orchestration_controller, input_validator, and tests.
"""

from __future__ import annotations

# ── OpenAI dependency guard ───────────────────────────────────────────────────

OPENAI_IMPORT_ERROR_MSG = "OpenAI client not installed. Run: pip install openai"


def require_openai(openai_cls):
    """Raise ImportError when the OpenAI dependency is missing."""
    if openai_cls is None:
        raise ImportError(OPENAI_IMPORT_ERROR_MSG)


# ── Version ───────────────────────────────────────────────────────────────────

VERSION = "0.6.0"

# ── API defaults ──────────────────────────────────────────────────────────────

DEFAULT_PORT = 5000
DEFAULT_RATE_LIMIT = 60          # requests per window
RATE_LIMIT_WINDOW_SECONDS = 60   # seconds
MAX_RATE_LIMIT_ENTRIES = 10_000  # max tracked IPs before eviction

# ── LLM defaults per mode ────────────────────────────────────────────────────

# Temperature and max_tokens are tuned per use-case:
#   - Lower temperature for deterministic output (code, rules, triage)
#   - Higher temperature for creative/conversational responses

MODE_DEFAULTS: dict[str, dict] = {
    "auto":    {"temperature": 0.7, "max_tokens": 1024, "top_p": 0.95},
    "pentest": {"temperature": 0.7, "max_tokens": 1024, "top_p": 0.95},
    "soc":     {"temperature": 0.4, "max_tokens": 1200, "top_p": 0.95},
    "code":    {"temperature": 0.2, "max_tokens": 2048, "top_p": 0.70},
    "ciso":    {"temperature": 0.3, "max_tokens": 2048, "top_p": 0.95},
    "sigma":   {"temperature": 0.2, "max_tokens": 2048, "top_p": 0.70},
    "yara":    {"temperature": 0.2, "max_tokens": 2048, "top_p": 0.70},
    "ioc":     {"temperature": 0.3, "max_tokens": 1000, "top_p": 0.90},
    "osint":   {"temperature": 0.3, "max_tokens": 1200, "top_p": 0.90},
}

# ── Supported modes ──────────────────────────────────────────────────────────

ALL_MODES = tuple(MODE_DEFAULTS.keys())

# ── HTTP response headers ────────────────────────────────────────────────────

HEADER_RATE_LIMIT = "X-RateLimit-Limit"
HEADER_RATE_REMAINING = "X-RateLimit-Remaining"
HEADER_RATE_WINDOW = "X-RateLimit-Window"
HEADER_REQUEST_ID = "X-Request-ID"

# ── Webhook ───────────────────────────────────────────────────────────────────

WEBHOOK_SIGNATURE_HEADER = "X-Hancock-Signature"
WEBHOOK_SIGNATURE_PREFIX = "sha256="
