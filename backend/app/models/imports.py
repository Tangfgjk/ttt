from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.question import Question
    from app.models.question import QuestionExternalRef


class DataSource(TimestampMixin, Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

    import_batches: Mapped[list["ImportBatch"]] = relationship(back_populates="data_source")
    source_records: Mapped[list["SourceQuestionRecord"]] = relationship(
        back_populates="data_source"
    )
    question_refs: Mapped[list["QuestionExternalRef"]] = relationship(back_populates="data_source")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    batch_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    import_status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_records: Mapped[int] = mapped_column(default=0, nullable=False)
    success_records: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_records: Mapped[int] = mapped_column(default=0, nullable=False)
    total_file_count: Mapped[int] = mapped_column(default=0, nullable=False)
    uploaded_file_count: Mapped[int] = mapped_column(default=0, nullable=False)
    processed_file_count: Mapped[int] = mapped_column(default=0, nullable=False)
    expected_records: Mapped[int | None]
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    data_source: Mapped["DataSource"] = relationship(back_populates="import_batches")
    source_records: Mapped[list["SourceQuestionRecord"]] = relationship(
        back_populates="import_batch"
    )


class SourceQuestionRecord(Base):
    __tablename__ = "source_question_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    source_record_key: Mapped[str] = mapped_column(String(128), nullable=False)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_hash: Mapped[str | None] = mapped_column(String(64))
    normalized_question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id"))
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    import_batch: Mapped["ImportBatch"] = relationship(back_populates="source_records")
    data_source: Mapped["DataSource"] = relationship(back_populates="source_records")
    normalized_question: Mapped["Question | None"] = relationship("Question")
