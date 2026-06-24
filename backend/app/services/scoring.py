"""
scoring.py
Computes per-user learning feature vectors (K, V, E) and the Onboarding
Readiness Index (ORI) for a given user_id / module_id pair.
"""

import math
from sqlalchemy.orm import Session

from app.models.telemetry_db import QuizAttempt, TelemetryLog
from app.models.content_db import Concept


def compute_knowledge_score(user_id: str, module_id: str, db: Session) -> float:
    """K = max_score * exp(-0.1 * (total_attempts - 1)), bounded [0, 1]."""
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.module_id == module_id)
        .all()
    )
    if not attempts:
        return 0.0
    max_score = max(float(a.score_percentage) for a in attempts) / 100.0
    total_attempts = len(attempts)
    k = max_score * math.exp(-0.1 * (total_attempts - 1))
    return max(0.0, min(1.0, k))


def compute_velocity_score(user_id: str, module_id: str, db: Session) -> float:
    """V = max(0, min(1, 300 / avg_latency_seconds))."""
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.module_id == module_id)
        .all()
    )
    if not attempts:
        return 0.0
    latencies = [
        (a.completed_at - a.started_at).total_seconds()
        for a in attempts
        if a.completed_at and a.started_at
    ]
    if not latencies:
        return 0.0
    avg_latency = sum(latencies) / len(latencies)
    if avg_latency <= 0:
        return 1.0
    return max(0.0, min(1.0, 300.0 / avg_latency))


def compute_engagement_score(user_id: str, module_id: str, db: Session) -> float:
    """E = max(0, min(1, total_duration / (n_concepts * 300)))."""
    concept_ids = [
        c.id
        for c in db.query(Concept.id).filter(Concept.module_id == module_id).all()
    ]
    total_concepts = len(concept_ids)
    if total_concepts == 0:
        return 0.0

    logs = (
        db.query(TelemetryLog)
        .filter(
            TelemetryLog.user_id == user_id,
            TelemetryLog.concept_id.in_(concept_ids),
            TelemetryLog.duration_seconds.isnot(None),
        )
        .all()
    )
    total_duration = sum(l.duration_seconds for l in logs if l.duration_seconds)
    expected = total_concepts * 300.0
    return max(0.0, min(1.0, total_duration / expected))


def compute_ori(k: float, v: float, e: float) -> float:
    """ORI = 0.5*K + 0.3*V + 0.2*E"""
    return round((0.5 * k) + (0.3 * v) + (0.2 * e), 4)


def compute_user_scores(user_id: str, module_id: str, db: Session) -> dict:
    """Return all four metrics for a user/module pair."""
    k = compute_knowledge_score(user_id, module_id, db)
    v = compute_velocity_score(user_id, module_id, db)
    e = compute_engagement_score(user_id, module_id, db)
    ori = compute_ori(k, v, e)
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.module_id == module_id)
        .count()
    )
    return {"K": k, "V": v, "E": e, "ORI": ori, "attempts": attempts}
