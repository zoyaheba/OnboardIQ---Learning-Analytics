import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.content_db import Track, Module, QuizQuestion
from app.models.telemetry_db import QuizAttempt
from app.models.user_db import UserTrackState
from app.schemas.content_pyd import TrackSchema, ModuleDetailSchema
from app.schemas.telemetry_pyd import QuizSubmitSchema

router = APIRouter()


@router.get("/", response_model=List[TrackSchema])
@router.get("", response_model=List[TrackSchema])
def get_all_tracks(db: Session = Depends(get_db)):
    tracks = db.query(Track).order_by(Track.name).all()
    return tracks


@router.get("/tracks/{user_id}")
def get_tracks_for_user(user_id: str, db: Session = Depends(get_db)):
    tracks = db.query(Track).order_by(Track.name).all()

    passed_module_ids: set[str] = {
        a.module_id
        for a in db.query(QuizAttempt.module_id)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.is_passed == True)  # noqa: E712
        .distinct()
        .all()
    }

    result = []
    for track in tracks:
        modules_sorted = sorted(track.modules, key=lambda m: m.sequence_order)
        passed_in_track = sum(1 for m in modules_sorted if m.id in passed_module_ids)

        if passed_in_track == 0:
            dynamic_level = "Beginner"
        elif passed_in_track == 1:
            dynamic_level = "Intermediate"
        else:
            dynamic_level = "Advanced"

        modules_out = []
        for i, mod in enumerate(modules_sorted):
            concepts_sorted = sorted(mod.concepts, key=lambda c: c.sequence_order)
            module_unlocked = (i == 0) or (modules_sorted[i - 1].id in passed_module_ids)

            concepts_out = []
            for j, concept in enumerate(concepts_sorted):
                if i == 0 and j == 0:
                    # Very first concept is always unlocked (entry point)
                    is_locked = False
                elif i == 0 and j > 0:
                    # Rest of module 0's concepts: locked until module 0 is passed
                    is_locked = mod.id not in passed_module_ids
                else:
                    # All concepts in later modules: locked until previous module is passed
                    is_locked = not module_unlocked
                concepts_out.append({
                    "id": concept.id,
                    "module_id": concept.module_id,
                    "title": concept.title,
                    "summary_text": concept.summary_text,
                    "youtube_video_id": concept.youtube_video_id,
                    "sequence_order": concept.sequence_order,
                    "is_locked": is_locked,
                })

            modules_out.append({
                "id": mod.id,
                "track_id": mod.track_id,
                "title": mod.title,
                "difficulty_level": dynamic_level,
                "sequence_order": mod.sequence_order,
                "is_locked": not module_unlocked,
                "concepts": concepts_out,
            })

        result.append({
            "id": track.id,
            "name": track.name,
            "description": track.description,
            "dynamic_level": dynamic_level,
            "modules": modules_out,
        })

    return result


@router.get("/modules/{module_id}", response_model=ModuleDetailSchema)
def get_module_detail(module_id: str, db: Session = Depends(get_db)):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


@router.get("/track-state/{user_id}")
def get_track_state(user_id: str, db: Session = Depends(get_db)):
    states = (
        db.query(UserTrackState)
        .filter(UserTrackState.user_id == user_id)
        .all()
    )
    return [
        {
            "track_id": s.track_id,
            "current_module_id": s.current_module_id,
            "status": s.status,
        }
        for s in states
    ]


@router.post("/quiz/submit")
def submit_quiz(payload: QuizSubmitSchema, db: Session = Depends(get_db)):
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.module_id == payload.module_id)
        .all()
    )
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this module")

    question_map = {q.id: q.correct_option for q in questions}
    correct = sum(
        1
        for qid, chosen in payload.selected_options.items()
        if question_map.get(qid) == chosen
    )
    total = len(questions)
    score = round((correct / total) * 100, 2) if total else 0.0
    is_passed = score >= 70.0

    existing_attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == payload.user_id,
            QuizAttempt.module_id == payload.module_id,
        )
        .count()
    )
    attempt_number = existing_attempts + 1

    attempt = QuizAttempt(
        id=str(uuid.uuid4()),
        user_id=payload.user_id,
        module_id=payload.module_id,
        attempt_number=attempt_number,
        score_percentage=score,
        is_passed=is_passed,
        started_at=payload.started_at,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    next_module_id: Optional[str] = None

    if is_passed:
        current_module = db.query(Module).filter(Module.id == payload.module_id).first()
        if current_module:
            next_module = (
                db.query(Module)
                .filter(
                    Module.track_id == current_module.track_id,
                    Module.sequence_order > current_module.sequence_order,
                )
                .order_by(Module.sequence_order)
                .first()
            )
            next_module_id = next_module.id if next_module else None

            track_state = (
                db.query(UserTrackState)
                .filter(
                    UserTrackState.user_id == payload.user_id,
                    UserTrackState.track_id == current_module.track_id,
                )
                .first()
            )
            if track_state:
                track_state.current_module_id = next_module_id if next_module_id else current_module.id
                track_state.status = "Completed" if not next_module_id else "In Progress"
            else:
                track_state = UserTrackState(
                    id=str(uuid.uuid4()),
                    user_id=payload.user_id,
                    track_id=current_module.track_id,
                    current_module_id=next_module_id if next_module_id else current_module.id,
                    status="Completed" if not next_module_id else "In Progress",
                )
                db.add(track_state)
            db.commit()

    return {
        "attempt_id": attempt.id,
        "score": score,
        "is_passed": is_passed,
        "attempt_number": attempt_number,
        "correct": correct,
        "total": total,
        "next_module_id": next_module_id,
    }
