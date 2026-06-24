from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel


class ConceptSchema(BaseModel):
    id: str
    module_id: str
    title: str
    summary_text: Optional[str]
    youtube_video_id: Optional[str]
    sequence_order: int

    model_config = {"from_attributes": True}


class QuizQuestionSchema(BaseModel):
    id: str
    module_id: str
    question_text: str
    options: Dict[str, str]
    correct_option: str

    model_config = {"from_attributes": True}


class ModuleSchema(BaseModel):
    id: str
    track_id: str
    title: str
    difficulty_level: str
    sequence_order: int

    model_config = {"from_attributes": True}


class ModuleDetailSchema(ModuleSchema):
    concepts: List[ConceptSchema] = []
    quiz_questions: List[QuizQuestionSchema] = []


class TrackSchema(BaseModel):
    id: str
    name: str
    description: Optional[str]
    modules: List[ModuleSchema] = []

    model_config = {"from_attributes": True}
