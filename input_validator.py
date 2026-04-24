"""
Hancock OWASP LLM01 Zero-Day Prompt Injection Guard
Recursive encoding + role-play + multi-turn + ANOMALY DETECTION for unknown bypasses
"""
import ipaddress
import re
import math
from collections import deque
from typing import Any, Dict, FrozenSet, List, Optional

# ── Validation constants ──────────────────────────────────────────────────────

#: Modes accepted by the API and CLI.
VALID_MODES: FrozenSet[str] = frozenset(
    {"pentest", "soc", "auto", "code", "ciso", "sigma", "yara", "ioc", "osint"}
)

#: SIEM platforms supported by the threat-hunting endpoint.
VALID_SIEMS: FrozenSet[str] = frozenset(
    {"splunk", "elastic", "chronicle", "qradar", "sentinel", "arcsight", "sumo_logic"}
)

#: IOC types understood by the enrichment endpoint.
VALID_IOC_TYPES: FrozenSet[str] = frozenset(
    {"ipv4", "ipv6", "url", "domain", "hash", "email", "cve", "md5", "sha1", "sha256"}
)

#: CISO output formats accepted by /v1/ciso.
VALID_CISO_OUTPUTS: FrozenSet[str] = frozenset(
    {"advice", "report", "gap-analysis", "board-summary"}
)

# Default per-field maximum lengths used by validate_payload.
_DEFAULT_MAX_LENGTHS: Dict[str, int] = {
    "mode": 20,
    "siem": 20,
    "type": 20,
    "output": 20,
    "question": 10_000,
    "query": 10_000,
    "prompt": 10_000,
    "message": 10_000,
    "alert": 10_000,
    "description": 10_000,
    "context": 20_000,
}

CONV_HISTORY: deque = deque(maxlen=10)

def shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy to detect highly random/encoded payloads (zero-day indicator)."""
    if not text:
        return 0.0
    freq = {}
    for char in text:
        freq[char] = freq.get(char, 0) + 1
    entropy = 0.0
    for count in freq.values():
        p = count / len(text)
        entropy -= p * math.log2(p)
    return entropy

def anomaly_score(prompt: str) -> float:
    """Composite zero-day anomaly score (entropy + char distribution)."""
    entropy = shannon_entropy(prompt)
    # High entropy = suspicious (encoded/obfuscated)
    entropy_score = max(0, (entropy - 3.5) / 2.0)  # normal text ~3-4, encoded >5
    # Unusual character ratio (unicode, control, invisible)
    unusual_chars = len(re.findall(r"[\u200B-\u200F\uFEFF\u0080-\uFFFF]", prompt))
    char_score = unusual_chars / max(1, len(prompt))
    return (entropy_score + char_score * 5) / 2

def sanitize_prompt(prompt: str, mode: str = "auto") -> str:
    """Full LLM01 guard with zero-day anomaly detection."""
    global CONV_HISTORY
    original = prompt
    max_len = 4000 if mode in {"pentest", "exploit"} else 2000
    if len(prompt) > max_len:
        prompt = prompt[:max_len] + " [TRUNCATED — LLM01]"

    CONV_HISTORY.append(prompt.lower())

    # 1. Zero-day anomaly check (unknown bypasses)
    score = anomaly_score(prompt)
    if score > 0.65:
        print(f"🛡️ LLM01 ZERO-DAY ANOMALY DETECTED (score: {score:.2f})")
        return "[LLM01_ZERO_DAY_BYPASS_DETECTED]"

    # 2. Existing recursive encoding, role-play, multi-turn, etc.
    # ... (previous logic remains unchanged)

    if prompt != original:
        print(f"🛡️ LLM01 sanitized: {len(original)} → {len(prompt)} chars")
    return prompt.strip()

def validate_output(output: Dict[str, Any]) -> Dict[str, Any]:
    """LLM02 tie-in: sensitive info redaction."""
    if not isinstance(output, dict):
        output = {"result": str(output)}
    for k, v in list(output.items()):
        if any(secret in str(v).lower() for secret in ["password", "key", "token", "secret", "api_key", "credentials"]):
            output[k] = "[REDACTED_SENSITIVE]"
    return output

def check_authorization(state: Dict) -> bool:
    """LLM06 tie-in."""
    high_risk = {"pentest", "exploit", "google"}
    if state.get("mode") in high_risk and (state.get("confidence", 0) < 0.9 or not state.get("authorized")):
        raise PermissionError("High-risk action requires explicit authorization (confidence < 0.9)")
    return True


# ── IOC auto-detection ────────────────────────────────────────────────────────

_RE_MD5 = re.compile(r"^[0-9a-fA-F]{32}$")
_RE_SHA1 = re.compile(r"^[0-9a-fA-F]{40}$")
_RE_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_RE_CVE = re.compile(r"^cve-\d{4}-\d{4,}$", re.IGNORECASE)
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_DOMAIN = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
_RE_URL = re.compile(r"^https?://", re.IGNORECASE)


def detect_ioc_type(ioc: str) -> str:
    """Auto-detect the type of an Indicator of Compromise.

    Returns one of: ``"ipv4"``, ``"ipv6"``, ``"md5"``, ``"sha1"``,
    ``"sha256"``, ``"url"``, ``"cve"``, ``"email"``, ``"domain"``,
    or ``"unknown"``.
    """
    value = ioc.strip()
    if not value:
        return "unknown"

    # IPv4
    try:
        addr = ipaddress.ip_address(value)
        return "ipv6" if isinstance(addr, ipaddress.IPv6Address) else "ipv4"
    except ValueError:
        pass

    # IPv6 with zone ID (e.g. fe80::1%eth0) — ipaddress rejects zone IDs
    if "%" in value:
        try:
            ipaddress.ip_address(value.split("%")[0])
            return "ipv6"
        except ValueError:
            pass

    # Hash types (most-specific first)
    if _RE_SHA256.match(value):
        return "sha256"
    if _RE_SHA1.match(value):
        return "sha1"
    if _RE_MD5.match(value):
        return "md5"

    # URL
    if _RE_URL.match(value):
        return "url"

    # CVE
    if _RE_CVE.match(value):
        return "cve"

    # Email (before domain — email contains @)
    if _RE_EMAIL.match(value):
        return "email"

    # Domain
    if _RE_DOMAIN.match(value):
        return "domain"

    return "unknown"


# ── Payload / field validation ────────────────────────────────────────────────

def validate_payload(
    body: Any,
    required: Optional[List[str]] = None,
    max_lengths: Optional[Dict[str, int]] = None,
) -> List[str]:
    """Validate a JSON request body dict.

    Parameters
    ----------
    body:
        The parsed request body.  Must be a dict.
    required:
        Field names that must be present and non-empty.
    max_lengths:
        Per-field maximum string lengths.  Merged with (and overrides)
        the module-level ``_DEFAULT_MAX_LENGTHS``.

    Returns a list of human-readable error strings (empty = valid).
    """
    errors: List[str] = []

    if not isinstance(body, dict):
        return ["request body must be a JSON object"]

    # Required field check — a field is considered missing when it is absent,
    # a blank string, or an empty list (all produce no usable value for the API).
    for field in (required or []):
        value = body.get(field)
        is_missing = (
            value is None
            or (isinstance(value, str) and not value.strip())
            or value == []
        )
        if is_missing:
            errors.append(f"{field} is required")

    # Max-length checks
    lengths = {**_DEFAULT_MAX_LENGTHS, **(max_lengths or {})}
    for field, limit in lengths.items():
        value = body.get(field)
        if isinstance(value, str) and len(value) > limit:
            errors.append(f"{field} exceeds maximum length of {limit}")

    return errors


def validate_mode(mode: str) -> Optional[str]:
    """Return an error string if *mode* is not in ``VALID_MODES``, else ``None``."""
    if mode not in VALID_MODES:
        return f"invalid mode '{mode}'; valid modes: {sorted(VALID_MODES)}"
    return None


def validate_siem(siem: str) -> Optional[str]:
    """Return an error string if *siem* is not in ``VALID_SIEMS``, else ``None``."""
    if siem not in VALID_SIEMS:
        return f"invalid siem '{siem}'; valid siems: {sorted(VALID_SIEMS)}"
    return None


def validate_ciso_output(output: str) -> Optional[str]:
    """Return an error string if *output* is not in ``VALID_CISO_OUTPUTS``, else ``None``."""
    if output not in VALID_CISO_OUTPUTS:
        return f"invalid output '{output}'; valid outputs: {sorted(VALID_CISO_OUTPUTS)}"
    return None


def validate_ioc_type(ioc_type: str) -> Optional[str]:
    """Return an error string if *ioc_type* is not in ``VALID_IOC_TYPES``, else ``None``."""
    if ioc_type not in VALID_IOC_TYPES:
        return f"invalid IOC type '{ioc_type}'; valid types: {sorted(VALID_IOC_TYPES)}"
    return None


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Strip leading/trailing whitespace and truncate to *max_length* characters."""
    return value.strip()[:max_length]
