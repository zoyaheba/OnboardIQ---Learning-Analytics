"""
plot_oulad_experiments.py
─────────────────────────
Runs three clustering experiments on real OULAD student data (BBB-2013J)
and saves individual experiment breakdown charts — mirroring the synthetic
experiment chart but using real Open University student data.

Charts produced:
  OnboardIQ_OULAD_Experiment_Individual.png  — 3 full-size horizontal bar charts

Prerequisites:
  OULAD CSVs must be present in backend/scripts/oulad_data/
  Run validate_oulad.py first if they are not downloaded yet.

READ-ONLY — makes no changes to the database or codebase.
"""

import os
import sys
import math

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR   = os.path.join(os.path.dirname(__file__), "oulad_data")
MODULE     = "BBB"
PRESENTATION = "2013J"
N_STUDENTS = 30
SEED       = 42

REQUIRED = ["studentAssessment.csv", "assessments.csv", "studentInfo.csv", "studentVle.csv"]

# ── 1. Check data files ───────────────────────────────────────────────────────

missing = [f for f in REQUIRED if not os.path.exists(os.path.join(DATA_DIR, f))]
if missing:
    print(f"ERROR: Missing OULAD files: {missing}")
    print("Run validate_oulad.py first to download the data.")
    sys.exit(1)

print("Loading OULAD CSVs…")
sa  = pd.read_csv(os.path.join(DATA_DIR, "studentAssessment.csv"))
sv  = pd.read_csv(os.path.join(DATA_DIR, "studentVle.csv"))
ass = pd.read_csv(os.path.join(DATA_DIR, "assessments.csv"))
si  = pd.read_csv(os.path.join(DATA_DIR, "studentInfo.csv"))

# ── 2. Derive K / V / E ───────────────────────────────────────────────────────

mod_students = si[
    (si["code_module"] == MODULE) & (si["code_presentation"] == PRESENTATION)
]["id_student"].unique()

mod_ass = ass[
    (ass["code_module"] == MODULE) & (ass["code_presentation"] == PRESENTATION)
][["id_assessment", "date"]].copy()
mod_ass["date"] = pd.to_numeric(mod_ass["date"], errors="coerce")
mod_ass = mod_ass.dropna(subset=["date"]).rename(columns={"date": "due_date"})

sa_mod = sa[sa["id_assessment"].isin(mod_ass["id_assessment"])].copy()
sa_mod = sa_mod[sa_mod["id_student"].isin(mod_students)].copy()
sa_mod["score"] = pd.to_numeric(sa_mod["score"], errors="coerce").fillna(0)

def _k(grp):
    return (grp["score"].max() / 100.0) * math.exp(-0.1 * (len(grp) - 1))

k_scores = (
    sa_mod.groupby("id_student", group_keys=False)
    .apply(_k)
    .clip(0, 1)
    .rename("K")
)

sa_merged = sa_mod.merge(mod_ass, on="id_assessment", how="left")
sa_merged["date_submitted"] = pd.to_numeric(sa_merged["date_submitted"], errors="coerce")
sa_merged["days_late"] = (sa_merged["date_submitted"] - sa_merged["due_date"]).abs()
v_scores = (
    sa_merged.groupby("id_student")["days_late"]
    .mean()
    .apply(lambda d: 1.0 / (1.0 + d))
    .clip(0, 1)
    .rename("V")
)

sv_mod = sv[
    (sv["code_module"] == MODULE) &
    (sv["code_presentation"] == PRESENTATION) &
    (sv["id_student"].isin(mod_students))
].copy()
total_clicks = sv_mod.groupby("id_student")["sum_click"].sum().rename("total_clicks")
expected = float(total_clicks.median()) or 1.0
e_scores = (total_clicks / expected).clip(0, 1).rename("E")

df = (
    pd.DataFrame({"id_student": mod_students})
    .join(k_scores, on="id_student")
    .join(v_scores, on="id_student")
    .join(e_scores, on="id_student")
    .dropna()
)

print(f"Total students with complete K/V/E: {len(df)}")

sample = df.sample(min(N_STUDENTS, len(df)), random_state=SEED).reset_index(drop=True)
print(f"Sample size used for experiments: {len(sample)}")

X_raw    = sample[["K", "V", "E"]].values
scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X_raw)

# ── 3. Run three experiments ──────────────────────────────────────────────────

print("\nRunning experiments on OULAD data…")

# Exp 1: K-Means raw (no scaling)
km1     = KMeans(n_clusters=3, random_state=SEED, n_init=10)
labs1   = km1.fit_predict(X_raw)
sil1    = silhouette_score(X_raw,    labs1)
dbi1    = davies_bouldin_score(X_raw,    labs1)

# Exp 2: K-Means + StandardScaler (matches production model)
km2     = KMeans(n_clusters=3, random_state=SEED, n_init=10)
labs2   = km2.fit_predict(X_scaled)
sil2    = silhouette_score(X_scaled, labs2)
dbi2    = davies_bouldin_score(X_scaled, labs2)

# Exp 3: GMM + StandardScaler
gmm     = GaussianMixture(n_components=3, covariance_type="full", random_state=SEED)
labs3   = gmm.fit_predict(X_scaled)
sil3    = silhouette_score(X_scaled, labs3)
dbi3    = davies_bouldin_score(X_scaled, labs3)
bic3    = gmm.bic(X_scaled)

# Stability across 5 seeds
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

print(f"\n  Exp 1  K-Means (Raw)          Sil={sil1:.4f}  DBI={dbi1:.4f}  Stability={stab1}")
print(f"  Exp 2  K-Means + Scaler [✓]   Sil={sil2:.4f}  DBI={dbi2:.4f}  Stability={stab2}")
print(f"  Exp 3  GMM + Scaler           Sil={sil3:.4f}  DBI={dbi3:.4f}  BIC={bic3:.1f}  Stability={stab3}")

# ── 4. Plot ───────────────────────────────────────────────────────────────────

TITLE_COLOR = "#f1f5f9"
LABEL_COLOR = "#94a3b8"
GRID_COLOR  = "#1e293b"
BENCH_COLOR = "#fbbf24"
stab_colors = {"High": "#22c55e", "Moderate": "#f59e0b", "Low": "#ef4444"}

exp_names  = [
    "Exp 1: K-Means (Raw)  |  OULAD Real Data",
    "Exp 2: K-Means + StandardScaler  [SELECTED]  |  OULAD Real Data",
    "Exp 3: GMM + StandardScaler  |  OULAD Real Data",
]
exp_colors = ["#64748b", "#3b82f6", "#f97316"]
metrics    = ["DBI ↓", "Silhouette ↑"]
values     = [[dbi1, sil1], [dbi2, sil2], [dbi3, sil3]]
stabilities = [stab1, stab2, stab3]
selected   = [False, True, False]

fig, axes = plt.subplots(3, 1, figsize=(12, 15))
fig.patch.set_facecolor("#0f172a")
fig.suptitle(
    f"OnboardIQ — OULAD Real Data Experiment Breakdown\n"
    f"({len(sample)} real students · Open University BBB-2013J)",
    color=TITLE_COLOR, fontsize=13, fontweight="bold", y=1.01
)

for i, (ax, exp_name, exp_color, vals, stab, sel) in enumerate(
    zip(axes, exp_names, exp_colors, values, stabilities, selected)
):
    ax.set_facecolor("#111827")
    bars = ax.barh(metrics, vals, color=exp_color, height=0.4, zorder=3, edgecolor="#1e293b")
    ax.set_xlim(0, 0.85)
    ax.set_title(exp_name, color=TITLE_COLOR, fontsize=10, fontweight="bold", loc="left", pad=8)
    ax.tick_params(colors=LABEL_COLOR, labelsize=10)
    ax.spines["bottom"].set_color("#334155")
    ax.spines["left"].set_color("#334155")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    # Silhouette 0.40 threshold line (lower bar for real data context)
    ax.axvline(0.40, color="#94a3b8", linewidth=1.2, linestyle=":", zorder=4, label="0.40 min threshold")
    # Silhouette 0.60 strong threshold
    ax.axvline(0.60, color=BENCH_COLOR, linewidth=1.5, linestyle="--", zorder=4, label="0.60 strong threshold")

    # Value labels
    for bar, val in zip(bars, vals):
        ax.text(
            val + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.4f}", va="center", color=TITLE_COLOR, fontsize=11, fontweight="bold"
        )

    # Stability + selection badge
    sc = stab_colors[stab]
    badge = f"  Stability: {stab}  "
    if sel:
        badge += "  |  [SELECTED FOR PRODUCTION]  "
    ax.text(
        0.99, 0.08, badge, transform=ax.transAxes, ha="right", va="bottom",
        color=sc if not sel else "#60a5fa",
        fontsize=9, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#1e293b",
                  edgecolor=sc if not sel else "#60a5fa", linewidth=1.5)
    )

    # Silhouette quality annotation — placed at the Silhouette bar (index 1)
    sil_val = vals[1]
    qual = "Strong" if sil_val >= 0.60 else ("Moderate" if sil_val >= 0.40 else "Weak")
    qual_color = "#22c55e" if sil_val >= 0.60 else ("#f59e0b" if sil_val >= 0.40 else "#ef4444")
    sil_bar = bars[1]
    ax.text(
        sil_val + 0.015,
        sil_bar.get_y() + sil_bar.get_height() / 2 + 0.28,
        f"{qual} separation",
        va="bottom", ha="left", color=qual_color,
        fontsize=8, fontweight="bold"
    )

    if sel:
        for bar in bars:
            bar.set_edgecolor("#60a5fa")
            bar.set_linewidth(2)

    ax.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor=BENCH_COLOR, loc="lower right")

plt.tight_layout(pad=2.2)

out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..")
out_path = os.path.join(out_dir, "OnboardIQ_OULAD_Experiment_Individual.png")
plt.savefig(out_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"\n✅ Saved: {os.path.abspath(out_path)}")
print("Done.")
