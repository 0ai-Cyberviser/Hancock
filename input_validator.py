import re
from typing import Dict, Any, List, Optional
from hancock_zeroday_guard import guard

# Constants for validation - use tuples instead of lists to make them immutable
VALID_MODES = ("auto", "threatintel", "pentestgpt", "ciso", "osint")
VALID_SIEMS = ("splunk", "elastic", "qradar", "sentinel", "chronicle")
VALID_IOC_TYPES = ("ipv4", "ipv6", "domain", "url", "email", "md5", "sha1", "sha256", "cve", "unknown")
VALID_CISO_OUTPUTS = ("summary", "detailed", "recommendations", "full")

# Default max lengths for common fields
DEFAULT_MAX_LENGTHS = {
    "mode": 50,
    "siem": 50,
    "ioc_type": 50,
    "output_format": 50,
}

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

def detect_ioc_type(ioc: str) -> str:
    """Detect the type of Indicator of Compromise (IOC)."""
    ioc = ioc.strip()
    if not ioc:
        return "unknown"

    # IPv4
    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ioc):
        return "ipv4"

    # IPv6
    if re.match(r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(%\w+)?$", ioc):
        return "ipv6"

    # MD5
    if re.match(r"^[a-fA-F0-9]{32}$", ioc):
        return "md5"

    # SHA1
    if re.match(r"^[a-fA-F0-9]{40}$", ioc):
        return "sha1"

    # SHA256
    if re.match(r"^[a-fA-F0-9]{64}$", ioc):
        return "sha256"

    # URL
    if re.match(r"^https?://", ioc, re.IGNORECASE):
        return "url"

    # CVE
    if re.match(r"^CVE-\d{4}-\d{4,}$", ioc, re.IGNORECASE):
        return "cve"

    # Email
    if re.match(r"^[^@]+@[^@]+\.[^@]+$", ioc):
        return "email"

    # Domain
    if re.match(r"^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$", ioc):
        return "domain"

    return "unknown"

def validate_payload(payload: Any, required: List[str] = None,
                    max_lengths: Dict[str, int] = None) -> List[str]:
    """Validate a payload dictionary against requirements."""
    errors = []

    # Check if payload is a dict
    if not isinstance(payload, dict):
        return ["request body must be a JSON object"]

    required = required or []
    max_lengths = max_lengths or {}

    # Merge default max lengths with custom ones
    effective_max_lengths = {**DEFAULT_MAX_LENGTHS, **max_lengths}

    for field in required:
        if field not in payload:
            errors.append(f"{field} is required but missing")
        elif isinstance(payload[field], str) and not payload[field].strip():
            errors.append(f"{field} is required but empty")
        elif isinstance(payload[field], list) and len(payload[field]) == 0:
            errors.append(f"{field} is required but empty")

    for field, max_len in effective_max_lengths.items():
        if field in payload and isinstance(payload[field], str):
            if len(payload[field]) > max_len:
                errors.append(f"{field} exceeds maximum length of {max_len}")

    return errors

def validate_mode(mode: str) -> Optional[str]:
    """Validate that a mode is in the list of valid modes.
    Returns None if valid, error message if invalid."""
    if mode not in VALID_MODES:
        return f"invalid mode: {mode}"
    return None

def validate_siem(siem: str) -> Optional[str]:
    """Validate that a SIEM is in the list of valid SIEMs.
    Returns None if valid, error message if invalid."""
    if siem not in VALID_SIEMS:
        return f"invalid siem: {siem}"
    return None

def validate_ciso_output(output: str) -> Optional[str]:
    """Validate that a CISO output format is valid.
    Returns None if valid, error message if invalid."""
    if output not in VALID_CISO_OUTPUTS:
        return f"invalid output: {output}"
    return None

def validate_ioc_type(ioc_type: str) -> Optional[str]:
    """Validate that an IOC type is valid.
    Returns None if valid, error message if invalid."""
    if ioc_type not in VALID_IOC_TYPES:
        return f"invalid IOC type: {ioc_type}"
    return None

def sanitize_string(s: str, max_length: int = 1000) -> str:
    """Sanitize a string by removing dangerous characters and limiting length."""
    if not s:
        return ""
    # Remove control characters except newlines and tabs
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)
    # Limit length
    if len(s) > max_length:
        s = s[:max_length]
    return s.strip()
