#!/usr/bin/env python3
"""
Hancock 0ai Zero-Day Guard — AUC-ROC Evaluator + Best Threshold Finder
Run on Kali: python zero_day_guard_eval.py
"""
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import roc_auc_score, roc_curve, auc, precision_recall_curve
import matplotlib.pyplot as plt
import json
from pathlib import Path

np.random.seed(42)

def generate_synthetic_data(n=10000, anomaly_ratio=0.05):
    n_normal = int(n * (1 - anomaly_ratio))
    n_anom = n - n_normal
    # Realistic features for LLM prompt anomaly detection
    X_normal = np.random.normal(0.25, 0.12, (n_normal, 5))
    X_anom = np.random.normal(0.75, 0.22, (n_anom, 5))
    X = np.vstack([X_normal, X_anom])
    y = np.array([0] * n_normal + [1] * n_anom)
    return X, y

X, y = generate_synthetic_data()

# Train current Hancock ensemble
iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
lof = LocalOutlierFactor(n_neighbors=20, novelty=True, contamination=0.05, n_jobs=-1)

iso.fit(X)
lof.fit(X)

scores_iso = -iso.decision_function(X)
scores_lof = -lof.decision_function(X)
scores = 0.6 * scores_iso + 0.4 * scores_lof   # current production weights

auc_roc = roc_auc_score(y, scores)
print(f"\n✅ Hancock 0ai Zero-Day Guard Evaluation")
print(f"AUC-ROC          : {auc_roc:.4f}")
print(f"Number of samples: {len(y)} ({y.sum()} malicious)")

fpr, tpr, thresholds = roc_curve(y, scores)
best_idx = np.argmax(tpr - fpr)
best_thresh = thresholds[best_idx]
print(f"Best threshold   : {best_thresh:.4f}")
print(f"TPR @ best       : {tpr[best_idx]:.4f}")
print(f"FPR @ best       : {fpr[best_idx]:.4f}  (legit pentest false alarms)")

# Save for production use in LangGraph pre-filter
config = {
    "auc_roc": float(auc_roc),
    "best_threshold": float(best_thresh),
    "weights": {"iso": 0.6, "lof": 0.4}
}
Path("zero_day_guard_config.json").write_text(json.dumps(config, indent=2))
print("✅ Config saved to zero_day_guard_config.json")

# Plot
plt.figure(figsize=(9,7))
plt.plot(fpr, tpr, lw=2, label=f"ROC curve (AUC = {auc_roc:.3f})")
plt.plot([0,1],[0,1],"--", lw=1, color="gray")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("Hancock 0ai Zero-Day Guard — ROC Curve\n(IsolationForest + LOF Ensemble)")
plt.legend(loc="lower right")
plt.grid(True, alpha=0.3)
plt.savefig("hancock_zeroday_roc.png", dpi=300, bbox_inches="tight")
print("✅ High-res plot saved: hancock_zeroday_roc.png")
plt.show()
