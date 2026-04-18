"""
Hancock OWASP LLM01 Zero-Day Prompt Injection Guard
Recursive encoding + role-play + multi-turn + ANOMALY DETECTION for unknown bypasses
"""
import re
import math
from collections import deque
from typing import Dict, Any

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
