"""
plot_experiments.py
───────────────────
Generates experiment comparison charts and saves them to the OnboardIQ root folder.

Charts produced:
  1. OnboardIQ_Experiment_Comparison.png  — 3 subplots side by side (Silhouette, DBI, Combined)
  2. OnboardIQ_Experiment_Individual.png  — 3 separate full-size charts, one per experiment

READ-ONLY — makes no changes to the database or codebase.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ── Real measured experiment results ─────────────────────────────────────────

experiments = {
    "Exp 1\nK-Means\n(Raw)":        {"silhouette": 0.6478, "dbi": 0.4355, "stability": "High",     "color": "#64748b", "selected": False},
    "Exp 2\nK-Means\n(Scaled) [*]":  {"silhouette": 0.6322, "dbi": 0.4532, "stability": "High",     "color": "#3b82f6", "selected": True},
    "Exp 3\nGMM\n(Scaled)":         {"silhouette": 0.6510, "dbi": 0.3841, "stability": "Moderate", "color": "#f97316", "selected": False},
}

labels   = list(experiments.keys())
sil      = [experiments[k]["silhouette"] for k in labels]
dbi      = [experiments[k]["dbi"]        for k in labels]
colors   = [experiments[k]["color"]      for k in labels]
stabs    = [experiments[k]["stability"]  for k in labels]
selected = [experiments[k]["selected"]   for k in labels]

x = np.arange(len(labels))

# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — Combined 3-subplot comparison
# ─────────────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(18, 7))
fig.patch.set_facecolor("#0f172a")
gs = GridSpec(1, 3, figure=fig, wspace=0.38)

TITLE_COLOR  = "#f1f5f9"
LABEL_COLOR  = "#94a3b8"
GRID_COLOR   = "#1e293b"
BENCH_COLOR  = "#fbbf24"
SELECTED_BOX = "#1d4ed8"

def style_ax(ax, title):
    ax.set_facecolor("#0f172a")
    ax.set_title(title, color=TITLE_COLOR, fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors=LABEL_COLOR, labelsize=10)
    ax.spines["bottom"].set_color("#334155")
    ax.spines["left"].set_color("#334155")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

# ── Subplot 1: Silhouette ─────────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0])
bars1 = ax1.bar(x, sil, color=colors, width=0.5, zorder=3, edgecolor="#1e293b", linewidth=1.2)
ax1.axhline(0.60, color=BENCH_COLOR, linewidth=1.5, linestyle="--", zorder=4, label="0.60 threshold")
ax1.set_ylim(0.58, 0.68)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, color=LABEL_COLOR, fontsize=9)
ax1.set_ylabel("Silhouette Score (↑ higher = better)", color=LABEL_COLOR, fontsize=10)
style_ax(ax1, "Silhouette Coefficient")
ax1.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor=BENCH_COLOR)
for bar, val, sel in zip(bars1, sil, selected):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
             f"{val:.4f}", ha="center", va="bottom", color=TITLE_COLOR, fontsize=10, fontweight="bold")
    if sel:
        bar.set_edgecolor("#60a5fa")
        bar.set_linewidth(2.5)

# ── Subplot 2: DBI ────────────────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[1])
bars2 = ax2.bar(x, dbi, color=colors, width=0.5, zorder=3, edgecolor="#1e293b", linewidth=1.2)
ax2.axhline(1.0, color="#ef4444", linewidth=1.5, linestyle="--", zorder=4, label="1.0 danger threshold")
ax2.set_ylim(0.30, 0.55)
ax2.set_xticks(x)
ax2.set_xticklabels(labels, color=LABEL_COLOR, fontsize=9)
ax2.set_ylabel("Davies-Bouldin Index (↓ lower = better)", color=LABEL_COLOR, fontsize=10)
style_ax(ax2, "Davies-Bouldin Index")
ax2.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor="#ef4444")
for bar, val, sel in zip(bars2, dbi, selected):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
             f"{val:.4f}", ha="center", va="bottom", color=TITLE_COLOR, fontsize=10, fontweight="bold")
    if sel:
        bar.set_edgecolor("#60a5fa")
        bar.set_linewidth(2.5)

# ── Subplot 3: Combined radar-style grouped bar ───────────────────────────────
ax3 = fig.add_subplot(gs[2])
bar_w = 0.3
b1 = ax3.bar(x - bar_w/2, sil, width=bar_w, label="Silhouette ↑", color=colors, alpha=0.9,
             zorder=3, edgecolor="#1e293b")
b2 = ax3.bar(x + bar_w/2, dbi, width=bar_w, label="DBI ↓",
             color=colors, alpha=0.45, zorder=3, edgecolor="#1e293b", hatch="///")
ax3.set_ylim(0.0, 0.80)
ax3.set_xticks(x)
ax3.set_xticklabels(labels, color=LABEL_COLOR, fontsize=9)
ax3.set_ylabel("Score", color=LABEL_COLOR, fontsize=10)
style_ax(ax3, "Combined Comparison")

# Stability badges
stab_colors = {"High": "#22c55e", "Moderate": "#f59e0b", "Low": "#ef4444"}
for i, (stab, sel) in enumerate(zip(stabs, selected)):
    sc = stab_colors[stab]
    ax3.text(i, -0.07, f"Stability: {stab}", ha="center", va="top",
             color=sc, fontsize=8, fontweight="bold",
             transform=ax3.get_xaxis_transform())

sil_patch = mpatches.Patch(facecolor="#64748b", alpha=0.9, label="Silhouette ↑")
dbi_patch = mpatches.Patch(facecolor="#64748b", alpha=0.45, hatch="///", label="DBI ↓")
sel_patch = mpatches.Patch(edgecolor="#60a5fa", facecolor="none", linewidth=2, label="Selected (Exp 2)")
ax3.legend(handles=[sil_patch, dbi_patch, sel_patch], fontsize=8,
           facecolor="#1e293b", edgecolor="#334155", labelcolor=TITLE_COLOR, loc="upper right")

for bar, val, sel in zip(b1, sil, selected):
    if sel:
        bar.set_edgecolor("#60a5fa")
        bar.set_linewidth(2.5)

# ── Main title ────────────────────────────────────────────────────────────────
fig.suptitle("OnboardIQ — Clustering Algorithm Experiment Comparison",
             color=TITLE_COLOR, fontsize=15, fontweight="bold", y=1.01)

out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..")
out1 = os.path.join(out_dir, "OnboardIQ_Experiment_Comparison.png")
plt.savefig(out1, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"✅ Saved: {os.path.abspath(out1)}")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — Three individual full-size charts stacked vertically
# ─────────────────────────────────────────────────────────────────────────────

exp_names  = ["Exp 1: K-Means (Raw)", "Exp 2: K-Means + StandardScaler  [SELECTED]", "Exp 3: GMM + StandardScaler"]
exp_colors = ["#64748b", "#3b82f6", "#f97316"]
metrics    = ["Silhouette ↑", "DBI ↓"]
values     = [[0.6478, 0.4355], [0.6322, 0.4532], [0.6510, 0.3841]]
benchmarks = [0.60, None]
bench_lbls = ["Strong structure threshold (0.60)", None]

fig2, axes = plt.subplots(3, 1, figsize=(10, 13))
fig2.patch.set_facecolor("#0f172a")
fig2.suptitle("OnboardIQ — Individual Experiment Breakdown",
              color=TITLE_COLOR, fontsize=14, fontweight="bold", y=1.01)

for i, (ax, exp_name, exp_color, vals, sel) in enumerate(zip(axes, exp_names, exp_colors, values, selected)):
    ax.set_facecolor("#111827")
    bars = ax.barh(metrics, vals, color=exp_color, height=0.4, zorder=3, edgecolor="#1e293b")
    ax.set_xlim(0, 0.80)
    ax.set_title(exp_name, color=TITLE_COLOR, fontsize=11, fontweight="bold", loc="left", pad=8)
    ax.tick_params(colors=LABEL_COLOR, labelsize=10)
    ax.spines["bottom"].set_color("#334155")
    ax.spines["left"].set_color("#334155")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    # Silhouette benchmark line
    ax.axvline(0.60, color=BENCH_COLOR, linewidth=1.5, linestyle="--", zorder=4, label="Silhouette 0.60 threshold")

    # Value labels
    for bar, val in zip(bars, vals):
        ax.text(val + 0.01, bar.get_y() + bar.get_height()/2,
                f"{val:.4f}", va="center", color=TITLE_COLOR, fontsize=11, fontweight="bold")

    # Stability + selection badge
    stab = stabs[i]
    sc = stab_colors[stab]
    badge = f"  Stability: {stab}  "
    if sel:
        badge += "  |  [SELECTED FOR PRODUCTION]  "
    ax.text(0.99, 0.08, badge, transform=ax.transAxes, ha="right", va="bottom",
            color=sc if not sel else "#60a5fa",
            fontsize=9, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#1e293b", edgecolor=sc if not sel else "#60a5fa", linewidth=1.5))

    if sel:
        for bar in bars:
            bar.set_edgecolor("#60a5fa")
            bar.set_linewidth(2)

    ax.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor=BENCH_COLOR, loc="lower right")

plt.tight_layout(pad=2.0)
out2 = os.path.join(out_dir, "OnboardIQ_Experiment_Individual.png")
plt.savefig(out2, dpi=180, bbox_inches="tight", facecolor=fig2.get_facecolor())
plt.close()
print(f"✅ Saved: {os.path.abspath(out2)}")
print("\nDone. Both charts saved to the OnboardIQ root folder.")
