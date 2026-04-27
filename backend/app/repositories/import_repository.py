from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import (
    Exam,
    ExamQuestion,
    QuestionGoldCompetency,
    QuestionGoldLabel,
    SchoolClass,
    Student,
    StudentExamScore,
    StudentQuestionResponse,
)
from app.models.dictionary import Catalog, Grade, KnowledgePoint, KnowledgeType, QuestionType, Subject, Textbook
from app.models.imports import DataSource, ImportBatch, SourceQuestionRecord
from app.models.question import (
    Question,
    QuestionCatalog,
    QuestionContent,
    QuestionDedupFeature,
    QuestionDuplicateCandidate,
    QuestionExternalRef,
    QuestionKnowledgePoint,
)


class ImportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_data_source_by_code(self, code: str) -> DataSource | None:
        stmt = select(DataSource).where(DataSource.code == code)
        return self.db.scalar(stmt)

    def get_subject_by_code(self, code: str) -> Subject | None:
        stmt = select(Subject).where(Subject.code == code).limit(1)
        return self.db.scalar(stmt)

    def get_grade_by_index(self, grade_index: int) -> Grade | None:
        stmt = select(Grade).where(Grade.grade_index == grade_index).limit(1)
        return self.db.scalar(stmt)

    def get_question_type_by_code(self, code: str) -> QuestionType | None:
        stmt = select(QuestionType).where(QuestionType.code == code).limit(1)
        return self.db.scalar(stmt)

    def get_cognitive_level_by_name(self, name: str):
        from app.models.dictionary import CognitiveLevel

        stmt = select(CognitiveLevel).where(CognitiveLevel.name == name).limit(1)
        return self.db.scalar(stmt)

    def get_competency_by_name(self, name: str):
        from app.models.dictionary import Competency

        stmt = select(Competency).where(Competency.name == name).limit(1)
        return self.db.scalar(stmt)

    def get_knowledge_type_by_source_code(self, source_type_code: str) -> KnowledgeType | None:
        stmt = select(KnowledgeType).where(KnowledgeType.source_type_code == source_type_code).limit(1)
        return self.db.scalar(stmt)

    def save_knowledge_type(self, knowledge_type: KnowledgeType) -> KnowledgeType:
        self.db.add(knowledge_type)
        self.db.flush()
        return knowledge_type

    def get_knowledge_point_by_source_id(
        self,
        *,
        source_knowledge_id: str,
        knowledge_type_id: int,
    ) -> KnowledgePoint | None:
        stmt = (
            select(KnowledgePoint)
            .where(
                KnowledgePoint.source_knowledge_id == source_knowledge_id,
                KnowledgePoint.knowledge_type_id == knowledge_type_id,
            )
            .limit(1)
        )
        return self.db.scalar(stmt)

    def save_knowledge_point(self, knowledge_point: KnowledgePoint) -> KnowledgePoint:
        self.db.add(knowledge_point)
        self.db.flush()
        return knowledge_point

    def get_textbook_by_source_id(self, source_textbook_id: str) -> Textbook | None:
        stmt = select(Textbook).where(Textbook.source_textbook_id == source_textbook_id).limit(1)
        return self.db.scalar(stmt)

    def save_textbook(self, textbook: Textbook) -> Textbook:
        self.db.add(textbook)
        self.db.flush()
        return textbook

    def get_catalog_by_source_id(
        self,
        *,
        source_catalog_id: str,
        textbook_id: int | None,
        school_code: str | None,
    ) -> Catalog | None:
        stmt = (
            select(Catalog)
            .where(Catalog.source_catalog_id == source_catalog_id)
            .order_by(Catalog.id.asc())
            .limit(1)
        )
        if textbook_id is None:
            stmt = stmt.where(Catalog.textbook_id.is_(None))
        else:
            stmt = stmt.where(Catalog.textbook_id == textbook_id)
        if school_code is None:
            stmt = stmt.where(Catalog.school_code.is_(None))
        else:
            stmt = stmt.where(Catalog.school_code == school_code)
        return self.db.scalar(stmt)

    def save_catalog(self, catalog: Catalog) -> Catalog:
        self.db.add(catalog)
        self.db.flush()
        return catalog

    def create_batch(self, batch: ImportBatch) -> ImportBatch:
        self.db.add(batch)
        self.db.flush()
        return batch

    def add_source_records(self, records: list[SourceQuestionRecord]) -> None:
        self.db.add_all(records)
        self.db.flush()

    def list_batches(self, limit: int = 20) -> list[ImportBatch]:
        stmt = (
            select(ImportBatch)
            .options(selectinload(ImportBatch.data_source))
            .order_by(ImportBatch.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def get_batch_by_id(self, batch_id: int) -> ImportBatch | None:
        stmt = (
            select(ImportBatch)
            .options(selectinload(ImportBatch.data_source))
            .where(ImportBatch.id == batch_id)
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_source_records_by_batch(
        self,
        batch_id: int,
        *,
        limit: int = 200,
    ) -> list[SourceQuestionRecord]:
        stmt = (
            select(SourceQuestionRecord)
            .options(selectinload(SourceQuestionRecord.normalized_question))
            .where(SourceQuestionRecord.import_batch_id == batch_id)
            .order_by(SourceQuestionRecord.id.asc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def count_duplicate_candidates_by_source_record(self, batch_id: int) -> dict[int, int]:
        stmt = (
            select(
                QuestionDuplicateCandidate.source_record_id,
                func.count(QuestionDuplicateCandidate.id),
            )
            .join(
                SourceQuestionRecord,
                SourceQuestionRecord.id == QuestionDuplicateCandidate.source_record_id,
            )
            .where(SourceQuestionRecord.import_batch_id == batch_id)
            .group_by(QuestionDuplicateCandidate.source_record_id)
        )
        return {source_record_id: count for source_record_id, count in self.db.execute(stmt).all()}

    def summarize_batch_statuses(self, batch_id: int) -> dict[str, int]:
        stmt = select(SourceQuestionRecord.parse_status).where(
            SourceQuestionRecord.import_batch_id == batch_id
        )
        return dict(Counter(self.db.scalars(stmt)))

    def save_question(self, question: Question) -> Question:
        self.db.add(question)
        self.db.flush()
        return question

    def save_question_content(self, content: QuestionContent) -> QuestionContent:
        self.db.add(content)
        self.db.flush()
        return content

    def get_question_by_id(self, question_id: int) -> Question | None:
        stmt = (
            select(Question)
            .options(selectinload(Question.content))
            .where(Question.id == question_id)
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get_question_by_normalized_stem(
        self,
        *,
        normalized_stem_text: str,
        subject_id: int,
    ) -> Question | None:
        stmt = (
            select(Question)
            .join(QuestionDedupFeature, QuestionDedupFeature.question_id == Question.id)
            .options(selectinload(Question.content))
            .where(
                Question.subject_id == subject_id,
                QuestionDedupFeature.normalized_stem_text == normalized_stem_text,
            )
            .limit(1)
        )
        return self.db.scalar(stmt)

    def ensure_external_ref(
        self,
        *,
        question_id: int,
        data_source_id: int,
        external_question_id: str,
        external_type: str | None = None,
        is_primary: bool = False,
    ) -> QuestionExternalRef:
        stmt = (
            select(QuestionExternalRef)
            .where(
                QuestionExternalRef.question_id == question_id,
                QuestionExternalRef.data_source_id == data_source_id,
                QuestionExternalRef.external_question_id == external_question_id,
            )
            .limit(1)
        )
        existing = self.db.scalar(stmt)
        if existing is not None:
            existing.external_type = external_type
            existing.is_primary = is_primary or existing.is_primary
            self.db.flush()
            return existing

        external_ref = QuestionExternalRef(
            question_id=question_id,
            data_source_id=data_source_id,
            external_question_id=external_question_id,
            external_type=external_type,
            is_primary=is_primary,
        )
        self.db.add(external_ref)
        self.db.flush()
        return external_ref

    def replace_question_knowledge_points(
        self,
        *,
        question_id: int,
        knowledge_points: list[QuestionKnowledgePoint],
    ) -> None:
        delete_stmt = select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question_id)
        for item in self.db.scalars(delete_stmt):
            self.db.delete(item)
        self.db.flush()
        if knowledge_points:
            self.db.add_all(knowledge_points)
            self.db.flush()

    def replace_question_catalogs(
        self,
        *,
        question_id: int,
        catalogs: list[QuestionCatalog],
    ) -> None:
        delete_stmt = select(QuestionCatalog).where(QuestionCatalog.question_id == question_id)
        for item in self.db.scalars(delete_stmt):
            self.db.delete(item)
        self.db.flush()
        if catalogs:
            self.db.add_all(catalogs)
            self.db.flush()

    def get_gold_label_by_question_id(self, question_id: int) -> QuestionGoldLabel | None:
        stmt = (
            select(QuestionGoldLabel)
            .options(selectinload(QuestionGoldLabel.competencies))
            .where(QuestionGoldLabel.question_id == question_id)
            .limit(1)
        )
        return self.db.scalar(stmt)

    def save_gold_label(self, gold_label: QuestionGoldLabel) -> QuestionGoldLabel:
        self.db.add(gold_label)
        self.db.flush()
        return gold_label

    def replace_gold_competencies(
        self,
        *,
        gold_label_id: int,
        competencies: list[QuestionGoldCompetency],
    ) -> None:
        stmt = select(QuestionGoldCompetency).where(
            QuestionGoldCompetency.gold_label_id == gold_label_id
        )
        for item in self.db.scalars(stmt):
            self.db.delete(item)
        self.db.flush()
        if competencies:
            self.db.add_all(competencies)
            self.db.flush()

    def get_class_by_source_id(
        self,
        *,
        source_class_id: str | None,
        grade_id: int | None,
    ) -> SchoolClass | None:
        stmt = select(SchoolClass).limit(1)
        if source_class_id is None:
            stmt = stmt.where(SchoolClass.source_class_id.is_(None))
        else:
            stmt = stmt.where(SchoolClass.source_class_id == source_class_id)
        if grade_id is None:
            stmt = stmt.where(SchoolClass.grade_id.is_(None))
        else:
            stmt = stmt.where(SchoolClass.grade_id == grade_id)
        return self.db.scalar(stmt)

    def save_class(self, school_class: SchoolClass) -> SchoolClass:
        self.db.add(school_class)
        self.db.flush()
        return school_class

    def get_student_by_source_id(self, source_student_id: str) -> Student | None:
        stmt = select(Student).where(Student.source_student_id == source_student_id).limit(1)
        return self.db.scalar(stmt)

    def save_student(self, student: Student) -> Student:
        self.db.add(student)
        self.db.flush()
        return student

    def get_exam_by_source_id(self, source_exam_id: str) -> Exam | None:
        stmt = select(Exam).where(Exam.source_exam_id == source_exam_id).limit(1)
        return self.db.scalar(stmt)

    def save_exam(self, exam: Exam) -> Exam:
        self.db.add(exam)
        self.db.flush()
        return exam

    def upsert_exam_question(self, exam_question: ExamQuestion) -> ExamQuestion:
        stmt = (
            select(ExamQuestion)
            .where(
                ExamQuestion.exam_id == exam_question.exam_id,
                ExamQuestion.question_id == exam_question.question_id,
            )
            .limit(1)
        )
        existing = self.db.scalar(stmt)
        if existing is not None:
            existing.question_no = exam_question.question_no
            existing.custom_question_no = exam_question.custom_question_no
            existing.score = exam_question.score
            self.db.flush()
            return existing
        self.db.add(exam_question)
        self.db.flush()
        return exam_question

    def upsert_student_exam_score(self, student_exam_score: StudentExamScore) -> StudentExamScore:
        stmt = (
            select(StudentExamScore)
            .where(
                StudentExamScore.exam_id == student_exam_score.exam_id,
                StudentExamScore.student_id == student_exam_score.student_id,
            )
            .limit(1)
        )
        existing = self.db.scalar(stmt)
        if existing is not None:
            existing.class_id = student_exam_score.class_id
            existing.total_score = student_exam_score.total_score
            self.db.flush()
            return existing
        self.db.add(student_exam_score)
        self.db.flush()
        return student_exam_score

    def upsert_student_question_response(
        self,
        response: StudentQuestionResponse,
    ) -> StudentQuestionResponse:
        stmt = (
            select(StudentQuestionResponse)
            .where(
                StudentQuestionResponse.exam_id == response.exam_id,
                StudentQuestionResponse.question_id == response.question_id,
                StudentQuestionResponse.student_id == response.student_id,
            )
            .limit(1)
        )
        existing = self.db.scalar(stmt)
        if existing is not None:
            existing.response_text = response.response_text
            existing.response_score = response.response_score
            existing.subquestion_answer_text = response.subquestion_answer_text
            self.db.flush()
            return existing
        self.db.add(response)
        self.db.flush()
        return response
