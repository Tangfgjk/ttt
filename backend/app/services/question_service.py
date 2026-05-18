from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.question_repository import QuestionFilters, QuestionRepository
from app.schemas.question import DifficultyLevelStatOut


class QuestionService:
    def __init__(self, db: Session) -> None:
        self.repository = QuestionRepository(db)

    def list_questions(self, filters: QuestionFilters):
        return self.repository.list_questions(filters)

    def get_question_detail(self, question_id: int):
        question = self.repository.get_question_by_id(question_id)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question {question_id} not found.",
            )
        source_difficulty_level = self.repository.get_source_difficulty_level(question_id)
        difficulty_level_stats = [
            DifficultyLevelStatOut(level=level, question_count=question_count)
            for level, question_count in self.repository.list_difficulty_level_stats()
        ]
        return question, source_difficulty_level, difficulty_level_stats
