from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dictionary import CognitiveLevel, Competency, Grade, Subject
    from app.models.imports import SourceQuestionRecord
    from app.models.question import Question


class QuestionGoldLabel(Base):
    __tablename__ = "question_gold_labels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_question_records.id"))
    cognitive_level_id: Mapped[int | None] = mapped_column(ForeignKey("cognitive_levels.id"))
    label_source: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    question: Mapped["Question"] = relationship("Question")
    source_record: Mapped["SourceQuestionRecord | None"] = relationship("SourceQuestionRecord")
    cognitive_level: Mapped["CognitiveLevel | None"] = relationship("CognitiveLevel")
    competencies: Mapped[list["QuestionGoldCompetency"]] = relationship(
        back_populates="gold_label",
        cascade="all, delete-orphan",
    )


class QuestionGoldCompetency(Base):
    __tablename__ = "question_gold_competencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gold_label_id: Mapped[int] = mapped_column(ForeignKey("question_gold_labels.id"), nullable=False)
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"), nullable=False)
    level_value: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    gold_label: Mapped["QuestionGoldLabel"] = relationship(back_populates="competencies")
    competency: Mapped["Competency"] = relationship("Competency")


class SchoolClass(TimestampMixin, Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_class_id: Mapped[str | None] = mapped_column(String(64))
    grade_id: Mapped[int | None] = mapped_column(ForeignKey("grades.id"))
    class_name: Mapped[str] = mapped_column(String(128), nullable=False)
    class_seq: Mapped[int | None] = mapped_column(SmallInteger)

    grade: Mapped["Grade | None"] = relationship("Grade")


class Student(TimestampMixin, Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_student_id: Mapped[str] = mapped_column(String(64), nullable=False)
    student_name: Mapped[str | None] = mapped_column(String(128))
    grade_id: Mapped[int | None] = mapped_column(ForeignKey("grades.id"))
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"))

    grade: Mapped["Grade | None"] = relationship("Grade")
    school_class: Mapped["SchoolClass | None"] = relationship("SchoolClass")


class Exam(TimestampMixin, Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_exam_id: Mapped[str] = mapped_column(String(64), nullable=False)
    exam_code: Mapped[str | None] = mapped_column(String(64))
    exam_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id"))
    grade_id: Mapped[int | None] = mapped_column(ForeignKey("grades.id"))
    exam_type: Mapped[str | None] = mapped_column(String(64))
    term_name: Mapped[str | None] = mapped_column(String(64))
    exam_time: Mapped[datetime | None] = mapped_column(DateTime)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    subject: Mapped["Subject | None"] = relationship("Subject")
    grade: Mapped["Grade | None"] = relationship("Grade")


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    question_no: Mapped[str | None] = mapped_column(String(32))
    custom_question_no: Mapped[str | None] = mapped_column(String(32))
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    exam: Mapped["Exam"] = relationship("Exam")
    question: Mapped["Question"] = relationship("Question")


class StudentExamScore(TimestampMixin, Base):
    __tablename__ = "student_exam_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"))
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    exam: Mapped["Exam"] = relationship("Exam")
    student: Mapped["Student"] = relationship("Student")
    school_class: Mapped["SchoolClass | None"] = relationship("SchoolClass")


class StudentQuestionResponse(TimestampMixin, Base):
    __tablename__ = "student_question_responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    response_text: Mapped[str | None] = mapped_column(Text)
    response_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    subquestion_answer_text: Mapped[str | None] = mapped_column(Text)

    exam: Mapped["Exam"] = relationship("Exam")
    question: Mapped["Question"] = relationship("Question")
    student: Mapped["Student"] = relationship("Student")
