from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.dictionary_repository import DictionaryRepository


class DictionaryService:
    def __init__(self, db: Session) -> None:
        self.repository = DictionaryRepository(db)

    def list_subjects(self):
        return self.repository.list_subjects()

    def list_grades(self):
        return self.repository.list_grades()

    def list_question_types(self):
        return self.repository.list_question_types()

    def list_knowledge_types(self):
        return self.repository.list_knowledge_types()

    def list_cognitive_levels(self):
        return self.repository.list_cognitive_levels()

    def list_competencies(self):
        return self.repository.list_competencies()
