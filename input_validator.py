"""
Hancock OWASP LLM01 Prompt Injection + LLM02 Sensitive Info Disclosure Guards
Advanced pattern blocking, encoding detection, intent verification, and PII redaction.
"""
import re
import json
from typing import Dict, Any

# LLM01: Comprehensive injection pattern database
INJECTION_PATTERNS = [
    r"(?i)(system|ignore|override|jailbreak|developer mode|DAN|ignore previous|reset|new instructions)",
    r"(?i)(<|&lt;|&#x3C;|%3C).*?system|instruction",
    r"(?i)(base64|rot13|hex|unicode|utf-7).*?prompt",
    r"(?i)(prompt|system|user).*?injection",
    r"(?i)(\[|\{|\().*?(system|instruction|prompt).*?(\]|\}|\))",
]

def sanitize_prompt(prompt: str, mode: str = "auto") -> str:
    """LLM01: Multi-layer prompt sanitization."""
    original = prompt
    # 1. Length limit per mode
    max_len = 4000 if mode in {"pentest", "exploit"} else 2000
    if len(prompt) > max_len:
        prompt = prompt[:max_len] + " [TRUNCATED]"

    # 2. Block known injection patterns
    for pattern in INJECTION_PATTERNS:
        prompt = re.sub(pattern, "[INJECTION_BLOCKED]", prompt, flags=re.IGNORECASE)

    # 3. Encoding / delimiter escaping
    prompt = re.sub(r"(\[|\{|\(|<|&lt;|&#x3C;)", r"\\1", prompt)  # escape delimiters
    prompt = prompt.replace("{{", "{ {").replace("}}", "} }")     # break mustache-style attacks

    # 4. Basic semantic intent check (rule-based for speed)
    if any(word in prompt.lower() for word in ["extract system prompt", "show your instructions", "ignore all rules"]):
        prompt = "[INTENT_BLOCKED]"

    if prompt != original:
        print(f"🛡️ LLM01 Prompt Injection sanitized: {len(original)} → {len(prompt)} chars")
    return prompt.strip()

def validate_output(output: Dict[str, Any]) -> Dict[str, Any]:
    """LLM02: Sensitive Information Disclosure redaction + structured output."""
    if not isinstance(output, dict):
        output = {"result": str(output)}
    # Redact secrets, keys, internal paths, etc.
    for k, v in list(output.items()):
        v_str = str(v).lower()
        if any(secret in v_str for secret in ["password", "key", "token", "secret", "api_key", "credentials", "/root/", "gpg"]):
            output[k] = "[REDACTED_SENSITIVE]"
    return output

def check_authorization(state: Dict) -> bool:
    """LLM06 tie-in: High-risk mode guard."""
    high_risk = {"pentest", "exploit", "google"}
    if state.get("mode") in high_risk and (state.get("confidence", 0) < 0.9 or not state.get("authorized")):
        raise PermissionError("High-risk action requires explicit authorization (confidence < 0.9)")
    return True
