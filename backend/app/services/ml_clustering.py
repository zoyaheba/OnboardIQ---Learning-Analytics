"""
ml_clustering.py
Builds the full unsupervised clustering pipeline over all seeded users:
  - Feature matrix X = [K, V, E] via scoring.py
  - StandardScaler normalization
  - KMeans (k=3, random_state=42)
  - Silhouette + Davies-Bouldin internal validation
  - Centroid-to-flag mapping -> Project Ready / Needs Coaching / At-Risk
  - Deterministic diagnostic comment generation
"""

import math
import os
import time
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sqlalchemy.orm import Session

from app.models.user_db import User
from app.models.content_db import Module
from app.services.scoring import compute_user_scores

_OULAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "oulad_data")

# ── In-memory model cache ─────────────────────────────────────────────────────
# Keyed by manager_id (or "__all__" for global). Stores:
#   {"n_users": int, "result": dict, "trained_at": float}
# Cache is invalidated when n_users changes (new learner joined / removed).
_MODEL_CACHE: Dict[str, Dict] = {}
_OULAD_CACHE: Dict[str, Any] = {}  # OULAD CSVs never change — cache permanently


def run_oulad_validation(n: int = 30, seed: int = 42) -> Optional[Dict]:  # noqa: C901
    """
    Reads pre-downloaded OULAD CSVs, derives K/V/E proxies for n students
    from module BBB-2013J, runs StandardScaler+KMeans(k=3), and returns
    silhouette + DBI. Returns None if the data files are not present.
    """
    if "result" in _OULAD_CACHE:
        return _OULAD_CACHE["result"]

    required = ["studentAssessment.csv", "assessments.csv", "studentInfo.csv", "studentVle.csv"]
    for fname in required:
        if not os.path.exists(os.path.join(_OULAD_DIR, fname)):
            return None

    MODULE, PRESENTATION = "BBB", "2013J"

    sa  = pd.read_csv(os.path.join(_OULAD_DIR, "studentAssessment.csv"))
    sv  = pd.read_csv(os.path.join(_OULAD_DIR, "studentVle.csv"))
    ass = pd.read_csv(os.path.join(_OULAD_DIR, "assessments.csv"))
    si  = pd.read_csv(os.path.join(_OULAD_DIR, "studentInfo.csv"))

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
    if len(df) < 3:
        return None

    sample = df.sample(min(n, len(df)), random_state=seed).reset_index(drop=True)
    X = sample[["K", "V", "E"]].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    km = KMeans(n_clusters=3, random_state=seed, n_init=10)
    labels = km.fit_predict(X_scaled)

    # Map cluster index → archetype label by centroid K value (highest K = Project Ready)
    centres_raw = scaler.inverse_transform(km.cluster_centers_)
    k_vals = centres_raw[:, 0]
    order = np.argsort(k_vals)[::-1]  # descending K
    archetype_names = ["Project Ready", "Needs Coaching", "At-Risk"]
    cluster_label_map = {int(order[i]): archetype_names[i] for i in range(3)}

    # Per-student rows
    students = []
    for i, row in sample.iterrows():
        students.append({
            "student_id": f"S{int(row['id_student'])}",
            "K": round(float(row["K"]), 3),
            "V": round(float(row["V"]), 3),
            "E": round(float(row["E"]), 3),
            "cluster": cluster_label_map[int(labels[i])],
        })

    # Centroid summary
    centroids = []
    for i in range(3):
        c = centres_raw[i]
        centroids.append({
            "cluster": cluster_label_map[i],
            "K": round(float(c[0]), 3),
            "V": round(float(c[1]), 3),
            "E": round(float(c[2]), 3),
            "count": int((labels == i).sum()),
        })

    oulad_result = {
        "silhouette_score": round(float(silhouette_score(X_scaled, labels)), 4),
        "davies_bouldin_score": round(float(davies_bouldin_score(X_scaled, labels)), 4),
        "n_students": len(sample),
        "module": f"{MODULE}-{PRESENTATION}",
        "students": students,
        "centroids": centroids,
    }
    _OULAD_CACHE["result"] = oulad_result
    return oulad_result


def _generate_diagnostic(
    cluster_flag: str,
    k: float,
    v: float,
    e: float,
    attempts: int,
    track_breakdown: List[Dict] | None = None,
) -> str:
    weak_tracks = []
    strong_tracks = []
    if track_breakdown:
        for t in track_breakdown:
            if t["ori"] < 0.45:
                weak_tracks.append(t["track"])
            elif t["ori"] >= 0.70:
                strong_tracks.append(t["track"])

    if cluster_flag == "At-Risk":
        if weak_tracks:
            track_list = " and ".join(weak_tracks)
            return (
                f"Below readiness threshold in {track_list}. "
                f"Knowledge retention and engagement scores are significantly below cohort average in "
                f"{'this track' if len(weak_tracks) == 1 else 'these tracks'}. "
                f"Recommend targeted remediation sessions before project allocation."
            )
        if attempts >= 3:
            return (
                "Struggling with concept retention across modules. Multiple quiz attempts with low "
                "score improvement indicators. Recommend targeted remediation sessions."
            )
        if e < 0.2:
            return (
                "Minimal reading engagement detected. Learner is skimming content blocks "
                "without sufficient active reading depth. Coaching intervention advised."
            )
        if v < 0.25:
            return (
                "Unusually slow quiz completion velocity detected despite adequate knowledge scores. "
                "Learner may be experiencing difficulty under timed conditions. "
                "Consider timed practice drills to build evaluation confidence."
            )
        return (
            "Feature profile places this learner below cohort readiness threshold. "
            "Review engagement and velocity patterns and schedule a check-in."
        )

    if cluster_flag == "Needs Coaching":
        borderline_tracks = [t["track"] for t in (track_breakdown or []) if 0.45 <= t["ori"] < 0.60]
        if weak_tracks and strong_tracks:
            return (
                f"Strong performance in {' and '.join(strong_tracks)}, but needs attention in "
                f"{' and '.join(weak_tracks)}. Focus coaching effort on the weaker track(s) "
                f"to bring overall readiness to deployment level."
            )
        if weak_tracks:
            return (
                f"Performance dip detected in {' and '.join(weak_tracks)}. "
                f"Solid engagement overall, but quiz scores in this area are pulling the ORI below threshold. "
                f"Targeted practice in {weak_tracks[0]} is recommended."
            )
        if borderline_tracks and strong_tracks:
            return (
                f"Performing well in {' and '.join(strong_tracks)}, but {' and '.join(borderline_tracks)} "
                f"is borderline. Focused review of quiz material in {borderline_tracks[0]} "
                f"should push overall readiness above deployment threshold."
            )
        if v < 0.4:
            return (
                "Strong conceptual understanding, but exhibiting pacing bottlenecks during "
                "evaluation blocks. Time-management coaching recommended."
            )
        if e > 0.6:
            return (
                "High reading engagement with moderate quiz performance. "
                "Focus on applying conceptual knowledge under timed conditions."
            )
        return (
            "Solid foundational engagement with room for improvement in quiz velocity. "
            "Periodic check-ins with a mentor will accelerate progress."
        )

    if strong_tracks and track_breakdown and len(track_breakdown) > 1:
        return (
            f"Demonstrating strong readiness across all tracks — particularly in "
            f"{' and '.join(strong_tracks)}. Knowledge retention, quiz velocity, and reading "
            f"engagement are all above cohort threshold. Learner is on track for early project allocation."
        )
    return (
        "Demonstrating strong knowledge retention, fast quiz completion, and deep reading "
        "engagement. Learner is on track for early project allocation."
    )


def _map_centroids_to_flags(centroids_scaled: np.ndarray, scaler: StandardScaler) -> Dict[int, str]:
    """
    Map each of the 3 KMeans cluster indices to a human flag.
    Strategy: un-scale centroids back to [K, V, E] space, then rank by
    combined K+E (primary) and V (secondary) to assign flags deterministically.
    """
    centroids_orig = scaler.inverse_transform(centroids_scaled)
    scores = [(i, centroids_orig[i][0] + centroids_orig[i][2], centroids_orig[i][1])
              for i in range(len(centroids_orig))]
    scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
    flags = ["Project Ready", "Needs Coaching", "At-Risk"]
    return {scores[i][0]: flags[i] for i in range(len(scores))}


def run_clustering_pipeline(db: Session, manager_id: str | None = None) -> Dict[str, Any]:
    """
    Full pipeline: query users -> score -> scale -> cluster -> validate -> annotate.
    If manager_id is provided, only direct reports of that manager are included.
    Returns structured results ready for the /cohorts endpoint.
    Results are cached in-memory and only retrained when the user count changes.
    """
    cache_key = manager_id or "__all__"

    query = db.query(User).filter(User.role == "Learner")
    if manager_id:
        query = query.filter(User.manager_id == manager_id)
    users = query.all()
    modules = db.query(Module).all()

    # Fast-path: return cached result if cohort size hasn't changed
    cached = _MODEL_CACHE.get(cache_key)
    if cached and cached["n_users"] == len(users):
        return cached["result"]

    if not modules:
        return {"error": "No modules found in database."}

    rows: List[Dict] = []
    for user in users:
        total_attempts = 0
        track_scores: Dict[str, Dict] = {}

        for module in modules:
            scores = compute_user_scores(user.id, module.id, db)
            total_attempts += scores["attempts"]
            if scores["attempts"] == 0 and scores["ORI"] == 0.0:
                continue
            track_name = module.track.name if module.track else "Unknown"
            if track_name not in track_scores:
                track_scores[track_name] = {"K": [], "V": [], "E": [], "ORI": []}
            track_scores[track_name]["K"].append(scores["K"])
            track_scores[track_name]["V"].append(scores["V"])
            track_scores[track_name]["E"].append(scores["E"])
            track_scores[track_name]["ORI"].append(scores["ORI"])

        if not track_scores:
            avg_k = avg_v = avg_e = avg_ori = 0.0
            track_breakdown: List[Dict] = []
            tracks_display = "Unknown"
        else:
            track_breakdown = []
            for tname, tvals in track_scores.items():
                t_k = sum(tvals["K"]) / len(tvals["K"])
                t_v = sum(tvals["V"]) / len(tvals["V"])
                t_e = sum(tvals["E"]) / len(tvals["E"])
                t_ori = sum(tvals["ORI"]) / len(tvals["ORI"])
                track_breakdown.append({"track": tname, "K": round(t_k, 4), "V": round(t_v, 4), "E": round(t_e, 4), "ori": round(t_ori, 4)})
            track_breakdown.sort(key=lambda x: x["ori"], reverse=True)

            all_k = [v for tvals in track_scores.values() for v in tvals["K"]]
            all_v = [v for tvals in track_scores.values() for v in tvals["V"]]
            all_e = [v for tvals in track_scores.values() for v in tvals["E"]]
            avg_k = sum(all_k) / len(all_k)
            avg_v = sum(all_v) / len(all_v)
            avg_e = sum(all_e) / len(all_e)
            avg_ori = 0.5 * avg_k + 0.3 * avg_v + 0.2 * avg_e
            tracks_display = ", ".join(t["track"] for t in track_breakdown)

        if avg_k >= 0.7:
            difficulty_label = "Advanced"
        elif avg_k >= 0.4:
            difficulty_label = "Intermediate"
        else:
            difficulty_label = "Beginner"

        if total_attempts == 0:
            continue

        rows.append({
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "track_name": tracks_display,
            "K": avg_k,
            "V": avg_v,
            "E": avg_e,
            "ORI": avg_ori,
            "attempts": total_attempts,
            "difficulty_label": difficulty_label,
            "track_breakdown": track_breakdown,
        })

    if len(rows) < 3:
        return {"error": f"Insufficient users ({len(rows)}) to run clustering (need ≥3)."}

    X = np.array([[r["K"], r["V"], r["E"]] for r in rows])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    sil = float(silhouette_score(X_scaled, labels))
    dbi = float(davies_bouldin_score(X_scaled, labels))

    flag_map = _map_centroids_to_flags(kmeans.cluster_centers_, scaler)

    cohort_list = []
    for i, row in enumerate(rows):
        cluster_idx = int(labels[i])
        flag = flag_map[cluster_idx]
        comment = _generate_diagnostic(flag, row["K"], row["V"], row["E"], row["attempts"], row.get("track_breakdown"))
        cohort_list.append({
            "user_name": row["user_name"],
            "user_email": row["user_email"],
            "track_name": row["track_name"],
            "numeric_ori_percentage": round(row["ORI"] * 100, 1),
            "cluster_flag": flag,
            "difficulty_label": row["difficulty_label"],
            "diagnostic_comment": comment,
            "scores": {
                "K": round(row["K"], 4),
                "V": round(row["V"], 4),
                "E": round(row["E"], 4),
            },
            "track_breakdown": row.get("track_breakdown", []),
        })

    cohort_list.sort(key=lambda x: x["numeric_ori_percentage"], reverse=True)

    oulad = run_oulad_validation()

    result = {
        "model_validation": {
            "silhouette_score": round(sil, 4),
            "davies_bouldin_score": round(dbi, 4),
            "n_users_clustered": len(rows),
            "oulad_validation": oulad,
        },
        "cohorts": cohort_list,
    }

    # Store in cache — invalidated automatically next time user count changes
    _MODEL_CACHE[cache_key] = {
        "n_users": len(users),
        "result": result,
        "trained_at": time.time(),
    }

    return result
