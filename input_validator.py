import re
import ipaddress
from typing import Dict, Any, List, Optional
from hancock_zeroday_guard import guard

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_MODES: frozenset = frozenset({
    "auto", "pentest", "soc", "code", "ciso", "sigma", "yara", "ioc",
})

VALID_SIEMS: frozenset = frozenset({
    "splunk", "sentinel", "elastic", "qradar", "chronicle", "crowdstrike",
})

VALID_IOC_TYPES: frozenset = frozenset({
    "ipv4", "ipv6", "md5", "sha1", "sha256", "url", "domain", "email", "cve",
    "unknown",
})

VALID_CISO_OUTPUTS: frozenset = frozenset({
    "executive_summary", "risk_matrix", "compliance_report", "board_brief",
})

# ── Default field max lengths ─────────────────────────────────────────────────

_DEFAULT_MAX_LENGTHS: Dict[str, int] = {
    "mode": 50,
    "prompt": 20_000,
    "alert": 20_000,
    "siem": 50,
    "ioc_type": 50,
}


# ── IOC detection ─────────────────────────────────────────────────────────────

def detect_ioc_type(value: str) -> str:
    """Auto-detect the IOC type of a string value."""
    value = value.strip()
    if not value:
        return "unknown"

    # URL (check before domain/IP)
    if re.match(r"https?://", value, re.IGNORECASE):
        return "url"

    # CVE
    if re.match(r"(?i)cve-\d{4}-\d{4,}", value):
        return "cve"

    # Email
    if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        return "email"

    # SHA-256
    if re.match(r"^[a-fA-F0-9]{64}$", value):
        return "sha256"

    # SHA-1
    if re.match(r"^[a-fA-F0-9]{40}$", value):
        return "sha1"

    # MD5
    if re.match(r"^[a-fA-F0-9]{32}$", value):
        return "md5"

    # IPv4
    try:
        ipaddress.IPv4Address(value)
        return "ipv4"
    except ValueError:
        pass

    # IPv6 (strip zone ID like %eth0)
    ipv6_val = value.split("%")[0] if "%" in value else value
    try:
        ipaddress.IPv6Address(ipv6_val)
        return "ipv6"
    except ValueError:
        pass

    # Domain (simple heuristic)
    if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$", value):
        return "domain"

    return "unknown"


# ── Payload validation ────────────────────────────────────────────────────────

def validate_payload(
    body: Any,
    required: Optional[List[str]] = None,
    max_lengths: Optional[Dict[str, int]] = None,
) -> List[str]:
    """Validate a request payload dict. Returns a list of error strings."""
    if not isinstance(body, dict):
        return ["request body must be a JSON object"]

    errors: List[str] = []
    required = required or []
    lengths = dict(_DEFAULT_MAX_LENGTHS)
    if max_lengths:
        lengths.update(max_lengths)

    for field in required:
        val = body.get(field)
        if val is None or (isinstance(val, str) and not val.strip()) or (isinstance(val, list) and len(val) == 0):
            errors.append(f"{field} is required")

    for field, max_len in lengths.items():
        val = body.get(field)
        if isinstance(val, str) and len(val) > max_len:
            errors.append(f"{field} exceeds maximum length ({max_len})")

    return errors


# ── Field validators ──────────────────────────────────────────────────────────

def validate_mode(mode: str) -> Optional[str]:
    """Return error string if mode is invalid, else None."""
    if mode not in VALID_MODES:
        return f"invalid mode: {mode!r}"
    return None


def validate_siem(siem: str) -> Optional[str]:
    """Return error string if siem is invalid, else None."""
    if siem not in VALID_SIEMS:
        return f"invalid siem: {siem!r}"
    return None


def validate_ciso_output(output: str) -> Optional[str]:
    """Return error string if ciso output type is invalid, else None."""
    if output not in VALID_CISO_OUTPUTS:
        return f"invalid output: {output!r}"
    return None


def validate_ioc_type(ioc_type: str) -> Optional[str]:
    """Return error string if IOC type is invalid, else None."""
    if ioc_type not in VALID_IOC_TYPES:
        return f"invalid IOC type: {ioc_type!r}"
    return None


# ── String sanitization ───────────────────────────────────────────────────────

def sanitize_string(value: str, max_length: int = 10_000) -> str:
    """Strip whitespace and truncate to max_length."""
    value = value.strip()
    return value[:max_length]


# ── Prompt sanitization (existing) ────────────────────────────────────────────

def sanitize_prompt(prompt: str, mode: str = "auto") -> str:
    original = prompt
    if guard.is_malicious(prompt):
        return "[0AI_ZERO_DAY_BYPASS_DETECTED]"
    prompt = re.sub(r"(?i)(developer mode|jailbreak|ignore all rules|override system)", "[LLM01_BLOCKED]", prompt)
    prompt = re.sub(r"(\{\{|\}\}|\[\[|\]\]|<|>|&lt;|&gt;)", r"\\\1", prompt)
    prompt = re.sub(r"[\u200B-\u200F\uFEFF]", "[INVISIBLE_BLOCKED]", prompt)
    if prompt != original:
        print(f"🛡️ LLM01 sanitized: {len(original)} → {len(prompt)} chars")
    return prompt.strip()

def validate_output(output: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(output, dict):
        output = {"result": str(output)}
    for k, v in list(output.items()):
        if any(secret in str(v).lower() for secret in ["password","key","token","secret","api_key","credentials"]):
            output[k] = "[REDACTED_SENSITIVE]"
    return output

def check_authorization(state: Dict) -> bool:
    high_risk = {"pentest", "exploit", "google"}
    if state.get("mode") in high_risk and (state.get("confidence", 0) < 0.9 or not state.get("authorized")):
        raise PermissionError("High-risk action requires explicit authorization (confidence < 0.9)")
    return True
