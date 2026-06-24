from datetime import datetime
from typing import Dict
from pydantic import BaseModel


class TelemetryLogCreate(BaseModel):
    user_id: str
    concept_id: str
    event_type: str
    duration_seconds: int | None = None


class QuizSubmitSchema(BaseModel):
    user_id: str
    module_id: str
    started_at: datetime
    selected_options: Dict[str, str]
