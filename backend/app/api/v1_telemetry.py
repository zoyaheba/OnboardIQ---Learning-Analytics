from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.models.telemetry_db import TelemetryLog
from app.schemas.telemetry_pyd import TelemetryLogCreate

router = APIRouter()


@router.post("/log", status_code=201)
async def log_telemetry(payload: TelemetryLogCreate, db: Session = Depends(get_db)):
    entry = TelemetryLog(
        user_id=payload.user_id,
        concept_id=payload.concept_id,
        event_type=payload.event_type,
        duration_seconds=payload.duration_seconds,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
        return {"log_id": entry.id, "status": "recorded"}
    except IntegrityError:
        db.rollback()
        return {"log_id": None, "status": "skipped"}
