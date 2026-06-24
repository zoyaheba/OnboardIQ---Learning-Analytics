"""
run_experiments.py
──────────────────
Runs three clustering experiments on the live OnboardIQ database and prints
a comparison table of Silhouette Coefficient and Davies-Bouldin Index.

Experiments:
  1. K-Means          — raw [K, V, E] features, no preprocessing
  2. K-Means + Scaler — StandardScaler normalisation (production model)
  3. GMM   + Scaler   — GaussianMixture, same normalised features

READ-ONLY — makes no writes to the database.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score

from app.core.database import SessionLocal
from app.models.user_db import User
from app.models.content_db import Module
from app.services.scoring import compute_user_scores

# ── 1. Build feature matrix from live database ──────────────────────────────

db = SessionLocal()

users = db.query(User).filter(User.role == "Learner").all()
modules = db.query(Module).all()

print(f"\n→ Users found : {len(users)}")
print(f"→ Modules found: {len(modules)}")

rows = []
for user in users:
    best_k = best_v = best_e = best_ori = 0.0
    for module in modules:
        scores = compute_user_scores(user.id, module.id, db)
        if scores["ORI"] > best_ori:
            best_k = scores["K"]
            best_v = scores["V"]
            best_e = scores["E"]
            best_ori = scores["ORI"]
    rows.append([best_k, best_v, best_e])

db.close()

X = np.array(rows)
print(f"→ Feature matrix shape: {X.shape}  (users × [K, V, E])\n")

# ── 2. Normalise ─────────────────────────────────────────────────────────────

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ── 3. Run experiments ───────────────────────────────────────────────────────

results = []

# Experiment 1: K-Means, raw features
km_raw = KMeans(n_clusters=3, random_state=42, n_init=10)
labels_1 = km_raw.fit_predict(X)
sil_1 = silhouette_score(X, labels_1)
dbi_1 = davies_bouldin_score(X, labels_1)
results.append(("K-Means (Raw, no scaling)", sil_1, dbi_1, None))

# Experiment 2: K-Means, StandardScaler (production model)
km_scaled = KMeans(n_clusters=3, random_state=42, n_init=10)
labels_2 = km_scaled.fit_predict(X_scaled)
sil_2 = silhouette_score(X_scaled, labels_2)
dbi_2 = davies_bouldin_score(X_scaled, labels_2)
results.append(("K-Means + StandardScaler", sil_2, dbi_2, None))

# Experiment 3: GMM, StandardScaler
gmm = GaussianMixture(n_components=3, covariance_type="full", random_state=42)
labels_3 = gmm.fit_predict(X_scaled)
sil_3 = silhouette_score(X_scaled, labels_3)
dbi_3 = davies_bouldin_score(X_scaled, labels_3)
bic_3 = gmm.bic(X_scaled)
results.append(("GMM + StandardScaler      ", sil_3, dbi_3, bic_3))

# ── 4. Stability test: re-run each with 5 seeds ──────────────────────────────

seeds = [0, 7, 21, 42, 99]

def stability(algo, data, seeds):
    base = algo(random_state=seeds[0]).fit_predict(data)
    mismatches = 0
    for s in seeds[1:]:
        labels = algo(random_state=s).fit_predict(data)
        # Compare ignoring label permutation: check if silhouette is stable
        diff = abs(silhouette_score(data, labels) - silhouette_score(data, base))
        mismatches += diff
    return "High" if mismatches < 0.01 else ("Moderate" if mismatches < 0.05 else "Low")

def km_factory_raw(random_state):
    return KMeans(n_clusters=3, n_init=10, random_state=random_state)

def km_factory_scaled(random_state):
    return KMeans(n_clusters=3, n_init=10, random_state=random_state)

def gmm_factory(random_state):
    return GaussianMixture(n_components=3, covariance_type="full", random_state=random_state)

stab_1 = stability(km_factory_raw, X, seeds)
stab_2 = stability(km_factory_scaled, X_scaled, seeds)
stab_3 = stability(gmm_factory, X_scaled, seeds)

# ── 5. Print results ─────────────────────────────────────────────────────────

print("━" * 72)
print(f"  {'EXPERIMENT RESULTS':^68}")
print("━" * 72)
print(f"  {'Algorithm':<30} {'Silhouette ↑':>13} {'DBI ↓':>9} {'BIC':>10} {'Stability':>10}")
print("─" * 72)

stabs = [stab_1, stab_2, stab_3]
for i, (name, sil, dbi, bic) in enumerate(results):
    bic_str = f"{bic:.1f}" if bic is not None else "N/A"
    selected = " ✅" if i == 1 else "   "
    print(f"  Exp {i+1}  {name:<28} {sil:>13.4f} {dbi:>9.4f} {bic_str:>10} {stabs[i]:>10}{selected}")

print("━" * 72)

# Winner
best_idx = max(range(len(results)), key=lambda i: results[i][1])
print(f"\n  Winner (highest Silhouette): Experiment {best_idx + 1} — {results[best_idx][0].strip()}")
print(f"  Silhouette = {results[best_idx][1]:.4f}  |  DBI = {results[best_idx][2]:.4f}")

# Improvement Exp1 → Exp2
sil_improvement = ((results[1][1] - results[0][1]) / results[0][1]) * 100
dbi_improvement = ((results[0][2] - results[1][2]) / results[0][2]) * 100
print(f"\n  Normalisation impact (Exp1 → Exp2):")
print(f"    Silhouette improved: +{results[1][1]-results[0][1]:.4f}  (+{sil_improvement:.1f}%)")
print(f"    DBI improved:        -{results[0][2]-results[1][2]:.4f}  (-{dbi_improvement:.1f}%)")
print("━" * 72 + "\n")
