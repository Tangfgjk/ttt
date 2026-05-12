from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.dictionary import CognitiveLevel, Competency, Grade, KnowledgePoint, Subject
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
    gold_label_id: Mapped[int] = mapped_column(
        ForeignKey("question_gold_labels.id"),
        nullable=False,
    )
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


class EmbeddingModel(TimestampMixin, Base):
    __tablename__ = "embedding_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dimension: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RecommendationBatch(Base):
    __tablename__ = "recommendation_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    algorithm_code: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    target_stage: Mapped[str | None] = mapped_column(String(32))
    context_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    triggered_by_user: Mapped["User | None"] = relationship("User")
    items: Mapped[list["RecommendationItem"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("recommendation_batches.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    rank_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_accepted: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    batch: Mapped["RecommendationBatch"] = relationship(back_populates="items")
    question: Mapped["Question"] = relationship("Question")


class CoresetExperiment(Base):
    __tablename__ = "coreset_experiments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("recommendation_batches.id"), nullable=False)
    algorithm_code: Mapped[str] = mapped_column(String(64), nullable=False)
    params_json: Mapped[dict | None] = mapped_column(JSON)
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    selected_question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    batch: Mapped["RecommendationBatch"] = relationship("RecommendationBatch")


class QuestionEmbedding(Base):
    __tablename__ = "question_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    embedding_model_id: Mapped[int] = mapped_column(
        ForeignKey("embedding_models.id"),
        nullable=False,
    )
    vector_json: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    vector_norm: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    question: Mapped["Question"] = relationship("Question")
    embedding_model: Mapped["EmbeddingModel"] = relationship("EmbeddingModel")


class AnnotatorTrainingAttempt(Base):
    __tablename__ = "annotator_training_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    edu_stage: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_no: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    score_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    pass_threshold: Mapped[int] = mapped_column(SmallInteger, default=80, nullable=False)
    total_questions: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    correct_questions: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User")


class AnnotationTask(Base):
    __tablename__ = "annotation_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey("recommendation_batches.id"))
    task_status: Mapped[str] = mapped_column(String(32), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)

    question: Mapped["Question"] = relationship("Question")
    assignee: Mapped["User"] = relationship("User")
    source_batch: Mapped["RecommendationBatch | None"] = relationship("RecommendationBatch")
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="task")


class Annotation(TimestampMixin, Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("annotation_tasks.id"))
    version_no: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    cognitive_level_id: Mapped[int | None] = mapped_column(ForeignKey("cognitive_levels.id"))
    confidence_level: Mapped[int | None] = mapped_column(SmallInteger)
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    annotation_status: Mapped[str] = mapped_column(String(32), nullable=False)

    question: Mapped["Question"] = relationship("Question")
    user: Mapped["User"] = relationship("User")
    task: Mapped["AnnotationTask | None"] = relationship(back_populates="annotations")
    cognitive_level: Mapped["CognitiveLevel | None"] = relationship("CognitiveLevel")
    competencies: Mapped[list["AnnotationCompetency"]] = relationship(
        back_populates="annotation",
        cascade="all, delete-orphan",
    )
    knowledge_points: Mapped[list["AnnotationKnowledgePoint"]] = relationship(
        back_populates="annotation",
        cascade="all, delete-orphan",
    )


class AnnotationCompetency(Base):
    __tablename__ = "annotation_competencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    annotation_id: Mapped[int] = mapped_column(ForeignKey("annotations.id"), nullable=False)
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"), nullable=False)
    level_value: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    annotation: Mapped["Annotation"] = relationship(back_populates="competencies")
    competency: Mapped["Competency"] = relationship("Competency")


class AnnotationKnowledgePoint(Base):
    __tablename__ = "annotation_knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    annotation_id: Mapped[int] = mapped_column(ForeignKey("annotations.id"), nullable=False)
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    annotation: Mapped["Annotation"] = relationship(back_populates="knowledge_points")
    knowledge_point: Mapped["KnowledgePoint"] = relationship("KnowledgePoint")


class QuestionLabelAggregate(TimestampMixin, Base):
    __tablename__ = "question_label_aggregates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"),
        unique=True,
        nullable=False,
    )
    final_cognitive_level_id: Mapped[int | None] = mapped_column(ForeignKey("cognitive_levels.id"))
    agreement_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_annotation_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime)

    question: Mapped["Question"] = relationship("Question")
    final_cognitive_level: Mapped["CognitiveLevel | None"] = relationship("CognitiveLevel")
    competencies: Mapped[list["QuestionAggregateCompetency"]] = relationship(
        back_populates="aggregate",
        cascade="all, delete-orphan",
    )


class QuestionAggregateCompetency(Base):
    __tablename__ = "question_aggregate_competencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    aggregate_id: Mapped[int] = mapped_column(
        ForeignKey("question_label_aggregates.id"),
        nullable=False,
    )
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"), nullable=False)
    level_value: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    agreement_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    aggregate: Mapped["QuestionLabelAggregate"] = relationship(back_populates="competencies")
    competency: Mapped["Competency"] = relationship("Competency")


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    aggregate_id: Mapped[int] = mapped_column(
        ForeignKey("question_label_aggregates.id"),
        nullable=False,
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    question: Mapped["Question"] = relationship("Question")
    aggregate: Mapped["QuestionLabelAggregate"] = relationship("QuestionLabelAggregate")
    reviewer: Mapped["User | None"] = relationship("User")


class AnnotationReviewLog(Base):
    __tablename__ = "annotation_review_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    aggregate_id: Mapped[int | None] = mapped_column(ForeignKey("question_label_aggregates.id"))
    review_task_id: Mapped[int | None] = mapped_column(ForeignKey("review_tasks.id"))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action_code: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    detail_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    question: Mapped["Question"] = relationship("Question")
    aggregate: Mapped["QuestionLabelAggregate | None"] = relationship("QuestionLabelAggregate")
    review_task: Mapped["ReviewTask | None"] = relationship("ReviewTask")
    actor_user: Mapped["User | None"] = relationship("User")


class ModelTrainingRun(Base):
    __tablename__ = "model_training_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    base_model_path: Mapped[str] = mapped_column(String(512), nullable=False)
    target_stage: Mapped[str] = mapped_column(String(32), default="junior", nullable=False)
    train_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    val_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    params_json: Mapped[dict | None] = mapped_column(JSON)
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    triggered_by_user: Mapped["User | None"] = relationship("User")
    epochs: Mapped[list["ModelTrainingEpoch"]] = relationship(
        back_populates="training_run",
        cascade="all, delete-orphan",
    )
    model_versions: Mapped[list["ModelVersion"]] = relationship(back_populates="training_run")


class ModelTrainingEpoch(Base):
    __tablename__ = "model_training_epochs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_run_id: Mapped[int] = mapped_column(
        ForeignKey("model_training_runs.id"),
        nullable=False,
    )
    epoch_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    train_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    val_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    level_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    macro_f1: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    detection_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    training_run: Mapped["ModelTrainingRun"] = relationship(back_populates="epochs")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(64), nullable=False)
    base_model_name: Mapped[str | None] = mapped_column(String(128))
    artifact_path: Mapped[str | None] = mapped_column(String(255))
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    training_run_id: Mapped[int] = mapped_column(
        ForeignKey("model_training_runs.id"),
        nullable=False,
    )
    checkpoint_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    level_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    macro_f1: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    detection_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    val_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    train_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    val_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    params_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    training_run: Mapped["ModelTrainingRun"] = relationship(back_populates="model_versions")
    prediction_runs: Mapped[list["ModelPredictionRun"]] = relationship(
        back_populates="model_version"
    )


class ModelPredictionRun(Base):
    __tablename__ = "model_prediction_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    confidence_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommendation_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendation_batches.id")
    )
    params_json: Mapped[dict | None] = mapped_column(JSON)
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    model_version: Mapped["ModelVersion"] = relationship(back_populates="prediction_runs")
    triggered_by_user: Mapped["User | None"] = relationship("User")
    recommendation_batch: Mapped["RecommendationBatch | None"] = relationship("RecommendationBatch")
    items: Mapped[list["ModelPredictionItem"]] = relationship(
        back_populates="prediction_run",
        cascade="all, delete-orphan",
    )


class ModelCoresetRun(Base):
    __tablename__ = "model_coreset_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    data_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommendation_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendation_batches.id")
    )
    params_json: Mapped[dict | None] = mapped_column(JSON)
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    triggered_by_user: Mapped["User | None"] = relationship("User")
    recommendation_batch: Mapped["RecommendationBatch | None"] = relationship("RecommendationBatch")


class ModelPredictionItem(Base):
    __tablename__ = "model_prediction_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prediction_run_id: Mapped[int] = mapped_column(
        ForeignKey("model_prediction_runs.id"),
        nullable=False,
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    predicted_levels_json: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    probabilities_json: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    uncertainty_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    rank_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    prediction_run: Mapped["ModelPredictionRun"] = relationship(back_populates="items")
    question: Mapped["Question"] = relationship("Question")
