"""
Input validation utilities and LLM guardrails for Hancock.

This module keeps the older REST/API validation surface intact while also
exposing the newer prompt-sanitization and output-redaction helpers used by
the agent runtime.
"""

from __future__ import annotations

import ipaddress
import math
import re
from collections import deque, Counter
from typing import Any


CONV_HISTORY: deque[str] = deque(maxlen=10)

_MD5_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DOMAIN_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
)
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)

# Pre-compile secret marker patterns for efficient reuse across multiple passes
_SECRET_KEYS_RE = re.compile(r"(password|token|secret|api_key|credentials)")
_SECRET_VALUES_RE = re.compile(r"(password=|token=|secret=|api_key=|credentials=)")

VALID_IOC_TYPES = frozenset(
    {
        "auto",
        "ipv4",
        "ipv6",
        "domain",
        "url",
        "md5",
        "sha1",
        "sha256",
        "email",
        "cve",
    }
)

VALID_MODES = frozenset(
    {
        "pentest",
        "soc",
        "auto",
        "code",
        "ciso",
        "sigma",
        "yara",
        "ioc",
        "osint",
    }
)

VALID_SIEMS = frozenset({"splunk", "elastic", "sentinel", "qradar", "chronicle"})

VALID_CISO_OUTPUTS = frozenset({"advice", "report", "gap-analysis", "board-summary"})

DEFAULT_MAX_LENGTHS: dict[str, int] = {
    "message": 10_000,
    "question": 10_000,
    "alert": 20_000,
    "target": 5_000,
    "incident": 5_000,
    "task": 10_000,
    "description": 10_000,
    "indicator": 1_000,
    "context": 5_000,
    "language": 50,
    "mode": 20,
    "siem": 30,
    "output": 30,
    "logsource": 200,
    "technique": 50,
    "file_type": 100,
    "hash": 128,
    "source": 200,
    "severity": 20,
}


def shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy to detect highly random/encoded payloads."""
    if not text:
        return 0.0

    # Use Counter for O(1) frequency tracking instead of manual dict.get() calls
    freq = Counter(text)
    text_len = len(text)
    entropy = 0.0
    for count in freq.values():
        probability = count / text_len
        entropy -= probability * math.log2(probability)
    return entropy


def anomaly_score(prompt: str) -> float:
    """Composite anomaly score based on entropy and unusual character density."""
    entropy = shannon_entropy(prompt)
    entropy_score = max(0.0, (entropy - 3.5) / 2.0)
    unusual_chars = len(re.findall(r"[\u200B-\u200F\uFEFF\u0080-\uFFFF]", prompt))
    char_score = unusual_chars / max(1, len(prompt))
    return (entropy_score + char_score * 5) / 2


def detect_ioc_type(indicator: str) -> str:
    """Auto-detect the IOC type from the indicator value."""
    indicator = indicator.strip()
    if not indicator:
        return "unknown"

    try:
        addr = ipaddress.ip_address(indicator)
        return "ipv4" if addr.version == 4 else "ipv6"
    except ValueError:
        pass

    if _SHA256_RE.match(indicator):
        return "sha256"
    if _SHA1_RE.match(indicator):
        return "sha1"
    if _MD5_RE.match(indicator):
        return "md5"
    if _URL_RE.match(indicator):
        return "url"
    if _CVE_RE.match(indicator):
        return "cve"
    if _EMAIL_RE.match(indicator):
        return "email"
    if _DOMAIN_RE.match(indicator):
        return "domain"
    return "unknown"


def validate_payload(
    data: dict[str, Any] | Any,
    required: list[str] | None = None,
    max_lengths: dict[str, int] | None = None,
) -> list[str]:
    """Validate a JSON request payload and return human-readable errors."""
    if not isinstance(data, dict):
        return ["request body must be a JSON object"]

    errors: list[str] = []

    for field in required or []:
        value = data.get(field, "")
        if isinstance(value, str) and not value.strip():
            errors.append(f"{field} is required")
        elif isinstance(value, list) and not value:
            errors.append(f"{field} is required")

    lengths = {**DEFAULT_MAX_LENGTHS, **(max_lengths or {})}
    for field, max_len in lengths.items():
        value = data.get(field)
        if isinstance(value, str) and len(value) > max_len:
            errors.append(f"{field} exceeds maximum length ({len(value)} > {max_len})")

    return errors


def validate_mode(mode: str) -> str | None:
    """Return an error message if *mode* is not supported."""
    if mode not in VALID_MODES:
        return f"invalid mode '{mode}'; valid: {sorted(VALID_MODES)}"
    return None


def validate_siem(siem: str) -> str | None:
    """Return an error message if *siem* is not supported."""
    if siem.lower() not in VALID_SIEMS:
        return f"invalid siem '{siem}'; valid: {sorted(VALID_SIEMS)}"
    return None


def validate_ciso_output(output_type: str) -> str | None:
    """Return an error message if *output_type* is not supported."""
    if output_type not in VALID_CISO_OUTPUTS:
        return f"invalid output '{output_type}'; valid: {sorted(VALID_CISO_OUTPUTS)}"
    return None


def validate_ioc_type(ioc_type: str) -> str | None:
    """Return an error message if *ioc_type* is not supported."""
    if ioc_type not in VALID_IOC_TYPES:
        return f"invalid IOC type '{ioc_type}'; valid: {sorted(VALID_IOC_TYPES)}"
    return None


def sanitize_string(value: str, max_length: int = 10_000) -> str:
    """Strip whitespace and cap strings at *max_length* characters."""
    return value.strip()[:max_length]


def sanitize_prompt(prompt: str, mode: str = "auto") -> str:
    """Apply prompt length bounds and a lightweight anomaly check."""
    original = prompt
    max_len = 4000 if mode in {"pentest", "exploit"} else 2000
    if len(prompt) > max_len:
        prompt = prompt[:max_len] + " [TRUNCATED - LLM01]"

    CONV_HISTORY.append(prompt.lower())

    if anomaly_score(prompt) > 0.65:
        return "[LLM01_ZERO_DAY_BYPASS_DETECTED]"

    if prompt != original:
        return prompt.strip()
    return prompt.strip()


def validate_output(output: dict[str, Any] | Any) -> dict[str, Any]:
    """Redact obvious secrets from tool output before returning it."""

    def _redact(key_name: str, value: Any) -> Any:
        lower_key = key_name.lower()
        # Use pre-compiled regex for efficient pattern matching (compiled once at module level)
        if _SECRET_KEYS_RE.search(lower_key):
            return "[REDACTED_SENSITIVE]"

        if isinstance(value, dict):
            return {key: _redact(str(key), nested) for key, nested in value.items()}

        if isinstance(value, list):
            return [_redact(key_name, item) for item in value]

        if isinstance(value, str):
            lower_value = value.lower()
            # Use pre-compiled regex for efficient pattern matching (compiled once at module level)
            if _SECRET_VALUES_RE.search(lower_value):
                return "[REDACTED_SENSITIVE]"
        return value

    if not isinstance(output, dict):
        return {"result": _redact("result", str(output))}

    return {key: _redact(str(key), value) for key, value in output.items()}


def check_authorization(state: dict[str, Any]) -> bool:
    """Enforce a simple authorization gate for higher-risk execution modes."""
    high_risk = {"pentest", "exploit", "google"}
    if state.get("mode") in high_risk and (
        state.get("confidence", 0) < 0.9 or not state.get("authorized")
    ):
        raise PermissionError("High-risk action requires explicit authorization (confidence < 0.9)")
    return True
