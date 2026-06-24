from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ml_clustering import run_clustering_pipeline

router = APIRouter()


@router.get("/cohorts")
def get_cohorts(
    manager_id: Optional[str] = Query(default=None, description="Filter cohort to direct reports of this manager"),
    db: Session = Depends(get_db),
):
    return run_clustering_pipeline(db, manager_id=manager_id)
