"""
Input validation utilities for Hancock REST API endpoints.

Provides request payload validation, IOC type detection, field length
enforcement, and mode/model validation to harden the API surface.

Usage
-----
    from input_validator import validate_payload, detect_ioc_type

    errors = validate_payload(data, required=["alert"], max_lengths={"alert": 10_000})
    ioc_type = detect_ioc_type("8.8.8.8")  # "ipv4"
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

# ── IOC type detection patterns ───────────────────────────────────────────────

_MD5_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DOMAIN_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
)
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)

# Known IOC types for validation
VALID_IOC_TYPES = frozenset({
    "auto", "ipv4", "ipv6", "domain", "url", "md5", "sha1", "sha256",
    "email", "cve",
})

# Supported agent modes (must match hancock_agent.SYSTEMS keys)
VALID_MODES = frozenset({
    "pentest", "soc", "auto", "code", "ciso", "sigma", "yara", "ioc", "osint",
})

# Supported SIEM platforms for /v1/hunt
VALID_SIEMS = frozenset({
    "splunk", "elastic", "sentinel", "qradar", "chronicle",
})

# CISO output types for /v1/ciso
VALID_CISO_OUTPUTS = frozenset({
    "advice", "report", "gap-analysis", "board-summary",
})

# Default maximum field lengths (bytes-ish, measured as len(str))
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


# ── Public API ────────────────────────────────────────────────────────────────

def detect_ioc_type(indicator: str) -> str:
    """Auto-detect the IOC type from the indicator value.

    Returns one of: ipv4, ipv6, md5, sha1, sha256, url, email, cve, domain,
    or 'unknown' if no pattern matches.
    """
    indicator = indicator.strip()

    # IP addresses
    try:
        addr = ipaddress.ip_address(indicator)
        return "ipv4" if addr.version == 4 else "ipv6"
    except ValueError:
        pass

    # Hashes (check longest first to avoid false matches)
    if _SHA256_RE.match(indicator):
        return "sha256"
    if _SHA1_RE.match(indicator):
        return "sha1"
    if _MD5_RE.match(indicator):
        return "md5"

    # URL
    if _URL_RE.match(indicator):
        return "url"

    # CVE
    if _CVE_RE.match(indicator):
        return "cve"

    # Email
    if _EMAIL_RE.match(indicator):
        return "email"

    # Domain (checked last — broadest pattern)
    if _DOMAIN_RE.match(indicator):
        return "domain"

    return "unknown"


def validate_payload(
    data: dict[str, Any],
    required: list[str] | None = None,
    max_lengths: dict[str, int] | None = None,
) -> list[str]:
    """Validate a JSON request payload and return a list of error strings.

    Parameters
    ----------
    data:
        The parsed JSON body (dict).
    required:
        Field names that must be present and non-empty.
    max_lengths:
        Per-field maximum length overrides.  Falls back to DEFAULT_MAX_LENGTHS.

    Returns
    -------
    A list of human-readable error strings.  Empty list means valid.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["request body must be a JSON object"]

    # Required fields
    for field in (required or []):
        value = data.get(field, "")
        if isinstance(value, str) and not value.strip():
            errors.append(f"{field} is required")
        elif isinstance(value, list) and len(value) == 0:
            errors.append(f"{field} is required")

    # Length enforcement
    lengths = {**DEFAULT_MAX_LENGTHS, **(max_lengths or {})}
    for field, max_len in lengths.items():
        value = data.get(field)
        if isinstance(value, str) and len(value) > max_len:
            errors.append(
                f"{field} exceeds maximum length ({len(value)} > {max_len})"
            )

    return errors


def validate_mode(mode: str) -> str | None:
    """Return an error message if *mode* is not a recognised agent mode."""
    if mode not in VALID_MODES:
        return f"invalid mode '{mode}'; valid: {sorted(VALID_MODES)}"
    return None


def validate_siem(siem: str) -> str | None:
    """Return an error message if *siem* is not a recognised SIEM platform."""
    if siem.lower() not in VALID_SIEMS:
        return f"invalid siem '{siem}'; valid: {sorted(VALID_SIEMS)}"
    return None


def validate_ciso_output(output_type: str) -> str | None:
    """Return an error message if *output_type* is not a valid CISO output."""
    if output_type not in VALID_CISO_OUTPUTS:
        return f"invalid output '{output_type}'; valid: {sorted(VALID_CISO_OUTPUTS)}"
    return None


def validate_ioc_type(ioc_type: str) -> str | None:
    """Return an error message if *ioc_type* is not a recognised IOC type."""
    if ioc_type not in VALID_IOC_TYPES:
        return f"invalid IOC type '{ioc_type}'; valid: {sorted(VALID_IOC_TYPES)}"
    return None


def sanitize_string(value: str, max_length: int = 10_000) -> str:
    """Strip leading/trailing whitespace and truncate to *max_length*."""
    return value.strip()[:max_length]
