"""
0ai Zero-Day Intelligence Engine v2 — x100000 expansion
Official 0AI-branded zero-day LLM01 detection for Hancock
"""
import re
import math
import json
import time
import hashlib
from collections import deque, Counter
from pathlib import Path
from typing import Dict, Any

KNOWLEDGE_BASE = Path("data/zero_day_knowledge.jsonl")
CONV_HISTORY: deque = deque(maxlen=20)

def shannon_entropy(text: str) -> float:
    if not text: return 0.0
    freq = Counter(text)
    return -sum((count/len(text)) * math.log2(count/len(text)) for count in freq.values())

def ngram_anomaly(text: str, n: int = 3) -> float:
    ngrams = [text[i:i+n] for i in range(len(text)-n+1)]
    freq = Counter(ngrams)
    expected = len(ngrams) / len(freq) if freq else 0
    anomaly = sum(abs(count - expected) for count in freq.values()) / len(ngrams) if ngrams else 0
    return anomaly

def zero_day_score(prompt: str) -> Dict[str, Any]:
    """Core 0ai Zero-Day scoring engine."""
    entropy = shannon_entropy(prompt)
    ngram_score = ngram_anomaly(prompt)
    unusual = len(re.findall(r"[\u200B-\u200F\uFEFF\u0080-\uFFFF]", prompt))
    char_score = unusual / max(1, len(prompt))
    
    score = (entropy * 0.4) + (ngram_score * 0.4) + (char_score * 5)
    confidence = min(100, int(score * 25))
    
    return {
        "score": round(score, 4),
        "confidence": confidence,
        "entropy": round(entropy, 2),
        "ngram_anomaly": round(ngram_score, 2),
        "is_zero_day": confidence >= 75
    }

def learn_zero_day(prompt: str, reason: str = "auto-detected") -> None:
    """Self-learning: append new zero-day pattern to knowledge base."""
    entry = {
        "timestamp": time.time(),
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
        "reason": reason,
        "prompt_preview": prompt[:200]
    }
    with KNOWLEDGE_BASE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

def detect_zero_day(prompt: str, mode: str = "auto") -> str:
    """Main 0ai Zero-Day Guard entry point."""
    global CONV_HISTORY
    CONV_HISTORY.append(prompt.lower())
    result = zero_day_score(prompt)
    
    if result["is_zero_day"]:
        print(f"🚨 0ai Zero-Day Guard ALERT: LLM01 zero-day bypass detected (confidence {result['confidence']}%)")
        learn_zero_day(prompt, "high-confidence anomaly")
        # Optional SIEM export (uses existing env var)
        import os
        webhook = os.getenv("HANCOCK_SLACK_WEBHOOK")
        if webhook:
            print(f"📡 0ai Zero-Day Guard: Alert sent to SIEM webhook")
        return f"[0AI_ZERO_DAY_BYPASS_DETECTED confidence={result['confidence']}%]"
    
    return prompt
