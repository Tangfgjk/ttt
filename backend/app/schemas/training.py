from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TrainingStage = Literal["junior", "senior"]
TrainingScope = Literal["none", "junior", "senior", "both"]


class TrainingCompetencyDefinition(BaseModel):
    code: str
    name: str
    definition: str
    focus_tip: str


class TrainingQuestionOut(BaseModel):
    question_id: int
    stem_text: str
    subject_name: str
    grade_name: str | None = None
    question_type_name: str | None = None
    answer_text: str | None = None
    solution_text: str | None = None


class TrainingGuideExampleCompetencyOut(BaseModel):
    competency_id: int
    competency_name: str
    level_value: int = Field(ge=0, le=3)
    definition: str
    focus_tip: str
    level_reason: str


class TrainingGuideExampleOut(BaseModel):
    question_id: int
    stem_text: str
    subject_name: str
    grade_name: str | None = None
    question_type_name: str | None = None
    answer_text: str | None = None
    solution_text: str | None = None
    coach_tip: str
    competencies: list[TrainingGuideExampleCompetencyOut]


class TrainingModuleResponse(BaseModel):
    stage: TrainingStage
    title: str
    summary: str
    pass_threshold: int
    required_question_count: int
    competency_definitions: list[TrainingCompetencyDefinition]
    guide_examples: list[TrainingGuideExampleOut]
    questions: list[TrainingQuestionOut]


class TrainingStatusResponse(BaseModel):
    user_id: int
    training_scope: TrainingScope
    available_stages: list[TrainingStage]
    junior_completed: bool
    senior_completed: bool


class TrainingCompetencyAnswer(BaseModel):
    competency_id: int
    level_value: int = Field(ge=0, le=3)


class TrainingQuestionAnswer(BaseModel):
    question_id: int
    competencies: list[TrainingCompetencyAnswer] = Field(default_factory=list)


class TrainingSubmitRequest(BaseModel):
    user_id: int
    stage: TrainingStage
    answers: list[TrainingQuestionAnswer] = Field(default_factory=list)


class TrainingQuestionResult(BaseModel):
    question_id: int
    score_percent: float
    is_passed: bool
    expected_competency_names: list[str]
    predicted_competency_names: list[str]


class TrainingSubmitResponse(BaseModel):
    stage: TrainingStage
    passed: bool
    score_percent: float
    pass_threshold: int
    training_scope: TrainingScope
    attempt_no: int
    completed_at: datetime
    question_results: list[TrainingQuestionResult]
