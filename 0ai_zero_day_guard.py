"""
0ai Zero-Day Guard — Official 0AI-branded module for LLM01 zero-day prompt injection
Detects unknown/emerging bypass techniques using anomaly scoring (entropy + char distribution).
"""
import re
import math
from collections import deque
from typing import Dict, Any

CONV_HISTORY: deque = deque(maxlen=10)

def shannon_entropy(text: str) -> float:
    """Shannon entropy — high values indicate encoded/random payloads."""
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
    """Composite zero-day anomaly score (0ai Zero-Day Guard core)."""
    entropy = shannon_entropy(prompt)
    entropy_score = max(0, (entropy - 3.8) / 2.0)
    unusual_chars = len(re.findall(r"[\u200B-\u200F\uFEFF\u0080-\uFFFF]", prompt))
    char_score = unusual_chars / max(1, len(prompt))
    return (entropy_score + char_score * 5) / 2

def detect_zero_day(prompt: str, mode: str = "auto") -> str:
    """Main 0ai Zero-Day Guard entry point — called on every prompt."""
    global CONV_HISTORY
    CONV_HISTORY.append(prompt.lower())
    score = anomaly_score(prompt)
    if score > 0.7:
        print(f"🚨 0ai Zero-Day Guard: LLM01 zero-day bypass detected (score: {score:.2f})")
        return "[0AI_ZERO_DAY_BYPASS_DETECTED]"
    return prompt
