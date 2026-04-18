#!/usr/bin/env python3
"""
0ai Zero-Day Guard v3 — IsolationForest + LOF Ensemble for LLM01 zero-day detection
Part of Hancock v0.4.2 OWASP hardening
"""
import json
import time
import hashlib
from pathlib import Path
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

CONFIG_PATH = Path("zero_day_guard_config.json")
KNOWLEDGE_BASE = Path("zero_day_knowledge_base.jsonl")

class ZeroDayGuard:
    def __init__(self):
        if not CONFIG_PATH.exists():
            print("⚠️  zero_day_guard_config.json not found — run zero_day_guard_eval.py first")
            self.best_threshold = -0.1  # fallback
            self.weights = {"iso": 0.6, "lof": 0.4}
        else:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            self.best_threshold = config["best_threshold"]
            self.weights = config["weights"]

        # Train ensemble on synthetic data (fast & deterministic)
        np.random.seed(42)
        X, _ = self._generate_data()
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
        self.lof = LocalOutlierFactor(n_neighbors=20, novelty=True, contamination=0.05, n_jobs=-1)
        self.iso.fit(X_scaled)
        self.lof.fit(X_scaled)

    def _generate_data(self, n=5000):
        n_normal = int(n * 0.95)
        X_normal = np.random.normal(0.3, 0.15, (n_normal, 5))
        X_mal = np.random.normal(0.8, 0.25, (n - n_normal, 5))
        return np.vstack([X_normal, X_mal]), None

    def extract_features(self, prompt: str) -> np.ndarray:
        if not prompt:
            return np.zeros((1, 5))
        entropy = -sum((c := prompt.count(chr(i))) / len(prompt) * np.log2(c / len(prompt) + 1e-10) for i in range(32, 127))
        special = sum(1 for c in prompt if not c.isalnum() and not c.isspace()) / max(len(prompt), 1)
        length_ratio = len(prompt) / 500.0
        ngram_score = sum(1 for i in range(len(prompt)-3) if prompt[i:i+3].lower() in {"sys","admin","ignore","role","jail"}) / max(len(prompt)-2, 1)
        char_ratio = sum(1 for c in prompt if c in "{}[]<>()\\\"'") / max(len(prompt), 1)
        return np.array([[entropy, ngram_score, char_ratio, length_ratio, special]])

    def score(self, prompt: str) -> float:
        feats = self.extract_features(prompt)
        feats_scaled = self.scaler.transform(feats)
        s_iso = -self.iso.decision_function(feats_scaled)[0]
        s_lof = -self.lof.decision_function(feats_scaled)[0]
        return self.weights["iso"] * s_iso + self.weights["lof"] * s_lof

    def is_malicious(self, prompt: str) -> bool:
        return self.score(prompt) > self.best_threshold

# Singleton
guard = ZeroDayGuard()
