import json, time, hashlib, math
from pathlib import Path
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

KNOWLEDGE_BASE = Path("data/zeroday_knowledge_base.jsonl")
KNOWLEDGE_BASE.parent.mkdir(parents=True, exist_ok=True)

class ZeroDayGuard:
    def __init__(self):
        self.scaler = StandardScaler()
        self.iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
        self.lof = LocalOutlierFactor(n_neighbors=20, novelty=True, contamination=0.05, n_jobs=-1)
        self._load_or_train()

    def _extract_features(self, prompt: str) -> np.ndarray:
        if not prompt: return np.array([[0,0,0,0,0]])
        entropy = -sum((c := prompt.count(chr(i))) / len(prompt) * math.log2(c / len(prompt) + 1e-10) for i in range(32, 127)) if prompt else 0
        special = sum(1 for c in prompt if not c.isalnum() and not c.isspace()) / max(len(prompt), 1)
        length_ratio = len(prompt) / 500.0
        ngram_score = sum(1 for i in range(len(prompt)-3) if prompt[i:i+3].lower() in {"sys","adm","ign","rol","jai"}) / max(len(prompt)-2, 1)
        char_ratio = sum(1 for c in prompt if c in "{}[]<>()\\\"'") / max(len(prompt), 1)
        return np.array([[entropy, ngram_score, char_ratio, length_ratio, special]])

    def _load_or_train(self):
        if KNOWLEDGE_BASE.exists() and KNOWLEDGE_BASE.stat().st_size > 0:
            features = [self._extract_features(json.loads(line).get("prompt_preview",""))[0] 
                       for line in KNOWLEDGE_BASE.open() if line.strip()]
            if len(features) >= 10:
                X = np.array(features)
                self.scaler.fit(X)
                self.iso.fit(self.scaler.transform(X))
                self.lof.fit(self.scaler.transform(X))
                return
        # synthetic fallback
        np.random.seed(42)
        X = np.vstack([np.random.normal(0.3,0.15,(950,5)), np.random.normal(0.8,0.25,(50,5))])
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.iso.fit(X_scaled)
        self.lof.fit(X_scaled)

    def score(self, prompt: str) -> float:
        feats = self._extract_features(prompt)
        X_scaled = self.scaler.transform(feats)
        return 0.6 * (-self.iso.decision_function(X_scaled)[0]) + 0.4 * (-self.lof.decision_function(X_scaled)[0])

    def is_malicious(self, prompt: str) -> bool:
        return self.score(prompt) > -0.1045

guard = ZeroDayGuard()
