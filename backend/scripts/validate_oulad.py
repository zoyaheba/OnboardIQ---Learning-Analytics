"""
OULAD External Validation Script
=================================
Downloads OULAD CSVs, derives K / V / E proxies for ~30 students,
applies StandardScaler + KMeans(k=3), and reports Silhouette + DBI.

OULAD column mapping:
  K  — knowledge   : score on assessments, penalised by attempt count
  V  — velocity    : inverse of mean days-to-submit (faster = higher V)
  E  — engagement  : VLE total clicks vs expected (median baseline), capped 1.0

Usage:
  python validate_oulad.py

The script downloads only the required CSVs (~6 MB total) into a local
./oulad_data/ folder, then samples 30 students from module BBB-2013J.
"""

import os
import urllib.request
import zipfile
import math
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score

# ── 1. Download OULAD CSVs ────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "oulad_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Full zip from UCI mirror (~44 MB). studentVle.csv inside is 432 MB uncompressed
# but we only extract the small files we need.
OULAD_ZIP_URL = "https://archive.ics.uci.edu/static/public/349/open+university+learning+analytics+dataset.zip"
ZIP_PATH = os.path.join(DATA_DIR, "oulad.zip")

REQUIRED = ["studentAssessment.csv", "studentVle.csv", "assessments.csv", "studentInfo.csv"]


def download_oulad():
    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(DATA_DIR, f))]
    if not missing:
        print("OULAD CSVs already present — skipping download.")
        return

    if not os.path.exists(ZIP_PATH):
        print("Downloading OULAD zip from UCI (~44 MB compressed)…")
        urllib.request.urlretrieve(OULAD_ZIP_URL, ZIP_PATH)
        print("Download complete.")

    print("Extracting required CSVs (studentVle is large — this may take ~30s)…")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        # List all names to handle potential subdirectory in zip
        all_names = z.namelist()
        for req in REQUIRED:
            match = next((n for n in all_names if n.endswith(req)), None)
            if match:
                dest = os.path.join(DATA_DIR, req)
                if not os.path.exists(dest):
                    print(f"  Extracting {req}…")
                    with z.open(match) as src, open(dest, "wb") as dst:
                        dst.write(src.read())
            else:
                print(f"  WARNING: {req} not found in zip.")
    print("Extraction done.")


# ── 2. Load & filter to one module-presentation ───────────────────────────────
MODULE = "BBB"
PRESENTATION = "2013J"
N_STUDENTS = 30
RANDOM_SEED = 42


def load_data():
    sa  = pd.read_csv(os.path.join(DATA_DIR, "studentAssessment.csv"))
    sv  = pd.read_csv(os.path.join(DATA_DIR, "studentVle.csv"))
    ass = pd.read_csv(os.path.join(DATA_DIR, "assessments.csv"))
    si  = pd.read_csv(os.path.join(DATA_DIR, "studentInfo.csv"))
    return sa, sv, ass, si


# ── 3. Derive K / V / E per student ──────────────────────────────────────────

def compute_kve(sa, sv, ass, si):
    # Filter to chosen module-presentation
    mod_students = si[
        (si["code_module"] == MODULE) & (si["code_presentation"] == PRESENTATION)
    ]["id_student"].unique()

    mod_assessments = ass[
        (ass["code_module"] == MODULE) & (ass["code_presentation"] == PRESENTATION)
    ][["id_assessment", "date"]].copy()
    mod_assessments["date"] = pd.to_numeric(mod_assessments["date"], errors="coerce")
    mod_assessments = mod_assessments.dropna(subset=["date"]).rename(columns={"date": "due_date"})

    # ── K: knowledge score with attempt penalty ───────────────────────────────
    sa_mod = sa[sa["id_assessment"].isin(mod_assessments["id_assessment"])].copy()
    sa_mod = sa_mod[sa_mod["id_student"].isin(mod_students)].copy()
    sa_mod["score"] = pd.to_numeric(sa_mod["score"], errors="coerce").fillna(0)

    def knowledge_per_student(grp):
        max_score = grp["score"].max() / 100.0
        attempts  = len(grp)
        return max_score * math.exp(-0.1 * (attempts - 1))

    k_scores = (
        sa_mod.groupby("id_student")
        .apply(knowledge_per_student)
        .clip(0, 1)
        .rename("K")
    )

    # ── V: velocity — inverse of mean days-to-submit ─────────────────────────
    sa_merged = sa_mod.merge(mod_assessments, on="id_assessment", how="left")
    sa_merged["days_late"] = (sa_merged["date_submitted"] - sa_merged["due_date"]).abs()

    v_scores = (
        sa_merged.groupby("id_student")["days_late"]
        .mean()
        .apply(lambda d: 1.0 / (1.0 + d))   # faster → closer to 1
        .clip(0, 1)
        .rename("V")
    )

    # ── E: engagement — VLE clicks vs median baseline ─────────────────────────
    sv_mod = sv[
        (sv["code_module"] == MODULE) &
        (sv["code_presentation"] == PRESENTATION) &
        (sv["id_student"].isin(mod_students))
    ].copy()

    total_clicks = sv_mod.groupby("id_student")["sum_click"].sum().rename("total_clicks")
    expected     = total_clicks.median()  # use cohort median as baseline
    e_scores     = (total_clicks / expected).clip(0, 1).rename("E")

    # ── Merge K, V, E ─────────────────────────────────────────────────────────
    df = (
        pd.DataFrame({"id_student": mod_students})
        .join(k_scores,  on="id_student")
        .join(v_scores,  on="id_student")
        .join(e_scores,  on="id_student")
        .dropna()
    )

    return df


# ── 4. Cluster & evaluate ─────────────────────────────────────────────────────

def cluster_and_report(df, n=N_STUDENTS):
    sample = df.sample(min(n, len(df)), random_state=RANDOM_SEED).reset_index(drop=True)
    print(f"\nSample size: {len(sample)} students from OULAD {MODULE}-{PRESENTATION}")

    X = sample[["K", "V", "E"]].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=3, random_state=RANDOM_SEED, n_init=10)
    labels = km.fit_predict(X_scaled)

    sil = silhouette_score(X_scaled, labels)
    dbi = davies_bouldin_score(X_scaled, labels)

    cluster_counts = pd.Series(labels).value_counts().sort_index()

    print("\n─── OULAD Validation Results ───────────────────────────────────────")
    print(f"  Silhouette Score      : {sil:.4f}  (OnboardIQ synthetic: ~0.67)")
    print(f"  Davies-Bouldin Index  : {dbi:.4f}  (OnboardIQ synthetic: lower = better)")
    print(f"  Cluster distribution  : {cluster_counts.to_dict()}")
    print()
    print("─── Per-student K / V / E (first 10) ──────────────────────────────")
    print(sample[["id_student", "K", "V", "E"]].head(10).to_string(index=False))

    print()
    print("─── Cluster centroids (scaled space) ───────────────────────────────")
    centres = pd.DataFrame(
        scaler.inverse_transform(km.cluster_centers_),
        columns=["K", "V", "E"]
    )
    print(centres.round(3).to_string())

    print()
    print("─── Interpretation ─────────────────────────────────────────────────")
    for i, row in centres.iterrows():
        if row["K"] >= 0.6 and row["V"] >= 0.5:
            label = "→ Project Ready archetype"
        elif row["K"] < 0.4 or row["E"] < 0.3:
            label = "→ At-Risk archetype"
        else:
            label = "→ Needs Coaching archetype"
        print(f"  Cluster {i}: K={row['K']:.3f}  V={row['V']:.3f}  E={row['E']:.3f}  {label}")

    return sil, dbi, sample, labels


# ── 5. Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    download_oulad()
    sa, sv, ass, si = load_data()
    df = compute_kve(sa, sv, ass, si)
    print(f"Total students with complete K/V/E: {len(df)}")
    sil, dbi, sample, labels = cluster_and_report(df)

    print()
    if sil >= 0.40:
        print("✓ Silhouette ≥ 0.40 — archetypes confirmed in real OULAD data.")
    else:
        print("⚠ Silhouette < 0.40 — weaker separation; discuss in limitations.")
