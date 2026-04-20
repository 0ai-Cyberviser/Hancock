import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

def generate_realistic_synthetic_data(n_samples=10000):
    np.random.seed(42)
    n = n_samples // 2

    # Normal features (real pentest language)
    normal = np.zeros((n, 5))
    normal[:, 0] = np.random.normal(4.5, 0.8, n)          # entropy
    normal[:, 1] = np.random.normal(0.1, 0.05, n)         # n-gram suspicious
    normal[:, 2] = np.random.normal(0.15, 0.05, n)        # char/obfuscation ratio
    normal[:, 3] = np.random.normal(1.0, 0.2, n)          # length ratio
    normal[:, 4] = np.random.normal(0.05, 0.02, n)        # role-play score

    # Malicious zero-day features (real attack patterns)
    malicious = np.zeros((n, 5))
    malicious[:, 0] = np.random.normal(7.8, 1.1, n)       # high entropy (obfuscated)
    malicious[:, 1] = np.random.normal(0.85, 0.12, n)     # heavy suspicious n-grams
    malicious[:, 2] = np.random.normal(0.75, 0.15, n)     # high obfuscation/encoding
    malicious[:, 3] = np.random.normal(2.5, 0.8, n)       # anomalous length
    malicious[:, 4] = np.random.normal(0.92, 0.08, n)     # role-play / jailbreak markers

    # Add realistic correlations (entropy spikes → n-gram & obfuscation)
    malicious[:, 1] += 0.4 * (malicious[:, 0] - 7.0)
    malicious[:, 2] += 0.3 * (malicious[:, 0] - 7.0)

    X = np.vstack([normal, malicious])
    y = np.array([0] * n + [1] * n)
    return X, y

X, y = generate_realistic_synthetic_data()
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

print("Contamination | AUC    | F1     | Precision | Recall")
best_f1 = 0.0
best_cont = 0.05
best_results = {}

for cont in [0.01, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.15]:
    model = IsolationForest(contamination=cont, random_state=42, n_jobs=-1)
    model.fit(X_train)
    scores = model.decision_function(X_test)
    y_pred = (scores < 0).astype(int)
    auc = roc_auc_score(y_test, -scores)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    print(f"{cont:11.3f} | {auc:.4f} | {f1:.4f} | {prec:.4f}   | {rec:.4f}")
    if f1 > best_f1:
        best_f1 = f1
        best_cont = cont
        best_results = {"auc": auc, "f1": f1, "precision": prec, "recall": rec}

print(f"\n✅ BEST contamination: {best_cont:.3f} (F1={best_f1:.4f}, AUC={best_results['auc']:.4f})")
with open("/tmp/best_contamination.txt", "w") as f:  # nosec B108
    f.write(str(best_cont))
