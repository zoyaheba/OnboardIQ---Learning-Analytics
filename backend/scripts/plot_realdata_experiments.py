"""
plot_realdata_experiments.py
─────────────────────────────
Runs three clustering experiments directly on the 30 real OULAD-mapped
learners currently seeded in the OnboardIQ database, and saves an
individual experiment breakdown chart.

Experiments:
  Exp 1: K-Means (Raw)               — no normalisation
  Exp 2: K-Means + StandardScaler    — production model
  Exp 3: GMM + StandardScaler        — alternative algorithm

Output:
  OnboardIQ_RealData_Experiment_Individual.png  (saved to project root)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score

from app.core.database import SessionLocal
from app.models.user_db import User
from app.services.scoring import compute_user_scores
from app.models.content_db import Module

# ── 1. Load real KVE vectors from the database ────────────────────────────────

print("Loading real learner KVE vectors from OnboardIQ DB…")

db = SessionLocal()
users = db.query(User).filter(User.role == "Learner").all()
modules = db.query(Module).all()

rows = []
for user in users:
    all_k, all_v, all_e = [], [], []
    total_attempts = 0
    for mod in modules:
        scores = compute_user_scores(user.id, mod.id, db)
        total_attempts += scores["attempts"]
        if scores["attempts"] == 0 and scores["ORI"] == 0.0:
            continue
        all_k.append(scores["K"])
        all_v.append(scores["V"])
        all_e.append(scores["E"])

    if total_attempts == 0:
        continue

    avg_k = sum(all_k) / len(all_k)
    avg_v = sum(all_v) / len(all_v)
    avg_e = sum(all_e) / len(all_e)
    rows.append({"name": user.name, "K": avg_k, "V": avg_v, "E": avg_e})

db.close()

print(f"Users with activity: {len(rows)}")
X_raw = np.array([[r["K"], r["V"], r["E"]] for r in rows])

scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)

# ── 2. Run three experiments ──────────────────────────────────────────────────

SEED = 42
print("\nRunning experiments on real OnboardIQ cohort…")

km1    = KMeans(n_clusters=3, random_state=SEED, n_init=10)
labs1  = km1.fit_predict(X_raw)
sil1   = silhouette_score(X_raw,    labs1)
dbi1   = davies_bouldin_score(X_raw,    labs1)

km2    = KMeans(n_clusters=3, random_state=SEED, n_init=10)
labs2  = km2.fit_predict(X_scaled)
sil2   = silhouette_score(X_scaled, labs2)
dbi2   = davies_bouldin_score(X_scaled, labs2)

gmm    = GaussianMixture(n_components=3, covariance_type="full", random_state=SEED)
labs3  = gmm.fit_predict(X_scaled)
sil3   = silhouette_score(X_scaled, labs3)
dbi3   = davies_bouldin_score(X_scaled, labs3)
bic3   = gmm.bic(X_scaled)

seeds = [0, 7, 21, 42, 99]

def _stab(algo_fn, data):
    base = silhouette_score(data, algo_fn(seeds[0]).fit_predict(data))
    diffs = sum(
        abs(silhouette_score(data, algo_fn(s).fit_predict(data)) - base)
        for s in seeds[1:]
    )
    return "High" if diffs < 0.01 else ("Moderate" if diffs < 0.05 else "Low")

stab1 = _stab(lambda s: KMeans(n_clusters=3, n_init=10, random_state=s), X_raw)
stab2 = _stab(lambda s: KMeans(n_clusters=3, n_init=10, random_state=s), X_scaled)
stab3 = _stab(lambda s: GaussianMixture(n_components=3, covariance_type="full", random_state=s), X_scaled)

print(f"\n  Exp 1  K-Means (Raw)         Sil={sil1:.4f}  DBI={dbi1:.4f}  Stability={stab1}")
print(f"  Exp 2  K-Means + Scaler [✓]  Sil={sil2:.4f}  DBI={dbi2:.4f}  Stability={stab2}")
print(f"  Exp 3  GMM + Scaler          Sil={sil3:.4f}  DBI={dbi3:.4f}  BIC={bic3:.1f}  Stability={stab3}")

# ── 3. Plot ───────────────────────────────────────────────────────────────────

TITLE_COLOR = "#f1f5f9"
LABEL_COLOR = "#94a3b8"
GRID_COLOR  = "#1e293b"
BENCH_COLOR = "#fbbf24"
stab_colors = {"High": "#22c55e", "Moderate": "#f59e0b", "Low": "#ef4444"}

exp_names  = [
    f"Exp 1: K-Means (Raw)  |  {len(rows)} Real OnboardIQ Learners",
    f"Exp 2: K-Means + StandardScaler  [SELECTED]  |  {len(rows)} Real OnboardIQ Learners",
    f"Exp 3: GMM + StandardScaler  |  {len(rows)} Real OnboardIQ Learners",
]
exp_colors  = ["#64748b", "#3b82f6", "#f97316"]
metrics     = ["DBI ↓", "Silhouette ↑"]
values      = [[dbi1, sil1], [dbi2, sil2], [dbi3, sil3]]
stabilities = [stab1, stab2, stab3]
selected    = [False, True, False]

fig, axes = plt.subplots(3, 1, figsize=(12, 15))
fig.patch.set_facecolor("#0f172a")
fig.suptitle(
    f"OnboardIQ — Real Cohort Algorithm Experiment Breakdown\n"
    f"({len(rows)} real learners · OULAD-mapped profiles · Production model: K-Means + StandardScaler)",
    color=TITLE_COLOR, fontsize=12, fontweight="bold", y=1.02
)

for i, (ax, exp_name, exp_color, vals, stab, sel) in enumerate(
    zip(axes, exp_names, exp_colors, values, stabilities, selected)
):
    ax.set_facecolor("#111827")
    bars = ax.barh(metrics, vals, color=exp_color, height=0.4, zorder=3, edgecolor="#1e293b")
    ax.set_xlim(0, 0.95)
    ax.set_title(exp_name, color=TITLE_COLOR, fontsize=10, fontweight="bold", loc="left", pad=8)
    ax.tick_params(colors=LABEL_COLOR, labelsize=10)
    ax.spines["bottom"].set_color("#334155")
    ax.spines["left"].set_color("#334155")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    ax.axvline(0.40, color="#94a3b8", linewidth=1.2, linestyle=":", zorder=4, label="0.40 threshold")
    ax.axvline(0.60, color=BENCH_COLOR, linewidth=1.5, linestyle="--", zorder=4, label="0.60 strong threshold")

    for bar, val in zip(bars, vals):
        ax.text(
            val + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.4f}", va="center", color=TITLE_COLOR, fontsize=11, fontweight="bold"
        )

    # Silhouette quality annotation on the Silhouette bar (index 1)
    sil_val = vals[1]
    qual = "Strong" if sil_val >= 0.60 else ("Moderate" if sil_val >= 0.40 else "Weak")
    qual_color = "#22c55e" if sil_val >= 0.60 else ("#f59e0b" if sil_val >= 0.40 else "#ef4444")
    ax.text(
        sil_val + 0.015,
        bars[1].get_y() + bars[1].get_height() / 2 - 0.05,
        f"{qual} separation",
        va="center", ha="left", color=qual_color, fontsize=8, fontweight="bold"
    )

    if sel:
        for bar in bars:
            bar.set_edgecolor("#60a5fa")
            bar.set_linewidth(2)

    sc = stab_colors[stab]
    badge = f"Stability: {stab}"
    if sel:
        badge += "  |  SELECTED"
    ax.text(
        0.99, 0.08, badge, transform=ax.transAxes, ha="right", va="bottom",
        color=sc if not sel else "#60a5fa",
        fontsize=9, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#1e293b",
                  edgecolor=sc if not sel else "#60a5fa", linewidth=1.5)
    )

    ax.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155",
              labelcolor=BENCH_COLOR, loc="upper right")

plt.tight_layout(pad=2.2)

fig.text(
    0.5, -0.01,
    f"Exp 3 (GMM) result compared to Exp 2 (K-Means + Scaler): "
    f"Sil {'=' if abs(sil3 - sil2) < 0.0001 else '≠'} {sil3:.4f} vs {sil2:.4f}  ·  "
    f"Production model: K-Means + StandardScaler (Exp 2) — deterministic, interpretable, validated.",
    ha="center", va="top", color="#64748b", fontsize=8
)

out_dir  = os.path.join(os.path.dirname(__file__), "..", "..")
out_path = os.path.join(out_dir, "OnboardIQ_RealData_Experiment_Individual.png")
plt.savefig(out_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"\n✅ Saved: {os.path.abspath(out_path)}")
print("Done.")
