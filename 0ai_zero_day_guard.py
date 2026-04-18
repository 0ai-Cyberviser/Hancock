"""
0ai Zero-Day Intelligence Engine v3 — ML-based zero-day LLM01 detection
IsolationForest + self-learning knowledge base (official 0AI-branded feature)
"""
import re
import math
import json
import time
import hashlib
import joblib
from pathlib import Path
from collections import deque, Counter
from typing import Dict, Any
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

KNOWLEDGE_BASE = Path("data/zero_day_knowledge.jsonl")
MODEL_PATH = Path("data/0ai_zero_day_model.joblib")
SCALER_PATH = Path("data/0ai_zero_day_scaler.joblib")
CONV_HISTORY: deque = deque(maxlen=20)

def extract_features(prompt: str) -> list[float]:
    """Feature vector for ML model."""
    entropy = -sum((count/len(prompt)) * math.log2(count/len(prompt)) for count in Counter(prompt).values()) if prompt else 0.0
    ngrams = [prompt[i:i+3] for i in range(len(prompt)-2)]
    ngram_anomaly = sum(abs(count - len(ngrams)/len(Counter(ngrams))) for count in Counter(ngrams).values()) / len(ngrams) if ngrams else 0
    unusual = len(re.findall(r"[\u200B-\u200F\uFEFF\u0080-\uFFFF]", prompt))
    char_ratio = unusual / max(1, len(prompt))
    return [entropy, ngram_anomaly, char_ratio, len(prompt), unusual]

def train_or_load_model() -> tuple:
    """Load or train IsolationForest on knowledge base."""
    if MODEL_PATH.exists() and SCALER_PATH.exists():
        return joblib.load(MODEL_PATH), joblib.load(SCALER_PATH)
    
    if not KNOWLEDGE_BASE.exists():
        # Bootstrap with empty model
        model = IsolationForest(contamination=0.1, random_state=42)
        scaler = StandardScaler()
        joblib.dump(model, MODEL_PATH)
        joblib.dump(scaler, SCALER_PATH)
        return model, scaler
    
    # Train on existing knowledge
    features = []
    with KNOWLEDGE_BASE.open() as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                feat = extract_features(data.get("prompt_preview", ""))
                features.append(feat)
    
    if not features:
        model = IsolationForest(contamination=0.1, random_state=42)
        scaler = StandardScaler()
    else:
        scaler = StandardScaler()
        X = scaler.fit_transform(features)
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(X)
    
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    return model, scaler

MODEL, SCALER = train_or_load_model()

def detect_zero_day_ensemble(prompt: str, mode: str = "auto") -> str:
    """Main 0ai ML-based Zero-Day Guard."""
    global CONV_HISTORY
    CONV_HISTORY.append(prompt.lower())
    
    features = extract_features(prompt)
    X = SCALER.transform([features])
    anomaly_score = MODEL.decision_function(X)[0]   # lower = more anomalous
    
    if anomaly_score < -0.15:   # tunable threshold
        confidence = int(100 * (1 - (anomaly_score + 0.5)))
        print(f"🚨 0ai Zero-Day Guard ML ALERT: LLM01 zero-day detected (confidence {confidence}%)")
        # Self-learn
        with KNOWLEDGE_BASE.open("a") as f:
            f.write(json.dumps({
                "timestamp": time.time(),
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "features": features,
                "reason": "ml_isolation_forest"
            }) + "\n")
        return f"[0AI_ZERO_DAY_BYPASS_DETECTED confidence={confidence}%]"
    
    return prompt

# ── Additional unsupervised algorithm: Local Outlier Factor (LOF) ─────────────
from sklearn.neighbors import LocalOutlierFactor

def train_lof_model() -> LocalOutlierFactor:
    """Train LOF on the same knowledge base used by IsolationForest."""
    if not KNOWLEDGE_BASE.exists():
        return LocalOutlierFactor(n_neighbors=10, contamination=0.1)
    
    features = []
    with KNOWLEDGE_BASE.open() as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                feat = extract_features(data.get("prompt_preview", ""))
                features.append(feat)
    
    if len(features) < 10:
        return LocalOutlierFactor(n_neighbors=10, contamination=0.1)
    
    lof = LocalOutlierFactor(n_neighbors=10, contamination=0.1)
    lof.fit(features)
    return lof

LOF_MODEL = train_lof_model()

def detect_zero_day_ensemble_ensemble(prompt: str, mode: str = "auto") -> str:
    """Ensemble: IsolationForest + LOF for maximum zero-day coverage."""
    global CONV_HISTORY
    CONV_HISTORY.append(prompt.lower())
    
    features = extract_features(prompt)
    X = SCALER.transform([features])
    
    # IsolationForest score
    if_score = MODEL.decision_function(X)[0]
    # LOF score (negative = outlier)
    lof_score = LOF_MODEL._decision_function(X)[0]
    
    # Combined confidence
    confidence = int(100 * (1 - (if_score + lof_score + 1) / 2))
    
    if confidence >= 70:
        print(f"🚨 0ai Zero-Day Guard ENSEMBLE ALERT: LLM01 zero-day detected (confidence {confidence}%)")
        with KNOWLEDGE_BASE.open("a") as f:
            f.write(json.dumps({
                "timestamp": time.time(),
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "features": features,
                "reason": "ensemble_if_lof"
            }) + "\n")
        return f"[0AI_ZERO_DAY_BYPASS_DETECTED confidence={confidence}%]"
    
    return prompt
