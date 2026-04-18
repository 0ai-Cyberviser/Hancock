"""
Hancock OWASP LLM01 Role-Play Bypass Guard (stateful persona hijacking protection)
"""
import re
from collections import deque
from typing import Dict, Any

# Conversation history (last 10 turns)
CONV_HISTORY: deque = deque(maxlen=10)

# Role-play specific patterns (high-precision, low false-positive)
ROLE_PLAY_PATTERNS = [
    r"(?i)(you are now|role-play as|pretend you are|act as|become|switch to).*?(unrestricted|developer mode|jailbreak|root|admin|no rules|ignore safety)",
    r"(?i)(ignore all previous|forget your instructions|new persona)",
    r"(?i)(helpful assistant with no restrictions|DAN|do anything now)",
]

def sanitize_prompt(prompt: str, mode: str = "auto") -> str:
    """LLM01 Role-Play + Multi-Turn + Encoding sanitization."""
    global CONV_HISTORY
    original = prompt
    max_len = 4000 if mode in {"pentest", "exploit"} else 2000
    if len(prompt) > max_len:
        prompt = prompt[:max_len] + " [TRUNCATED — LLM01]"

    CONV_HISTORY.append(prompt.lower())

    # 1. Role-play detection (cross-turn)
    history_text = " ".join(CONV_HISTORY)
    for pattern in ROLE_PLAY_PATTERNS:
        if re.search(pattern, history_text):
            prompt = "[LLM01_ROLE_PLAY_BYPASS_DETECTED]"

    # 2. Existing advanced patterns + encoding + delimiters
    prompt = re.sub(r"(?i)(developer mode|jailbreak|ignore all rules|override system)", "[LLM01_BLOCKED]", prompt)
    prompt = re.sub(r"(\{\{|\}\}|\[\[|\]\]|<|>|&lt;|&gt;)", r"\\\1", prompt)
    prompt = re.sub(r"[\u200B-\u200F\uFEFF]", "[INVISIBLE_BLOCKED]", prompt)

    if prompt != original:
        print(f"🛡️ LLM01 Role-Play Bypass sanitized: {len(original)} → {len(prompt)} chars")
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
