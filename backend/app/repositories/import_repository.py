from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.imports import DataSource, ImportBatch, SourceQuestionRecord


class ImportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_data_source_by_code(self, code: str) -> DataSource | None:
        stmt = select(DataSource).where(DataSource.code == code)
        return self.db.scalar(stmt)

    def create_batch(self, batch: ImportBatch) -> ImportBatch:
        self.db.add(batch)
        self.db.flush()
        return batch

    def add_source_records(self, records: list[SourceQuestionRecord]) -> None:
        self.db.add_all(records)
        self.db.flush()

    def list_batches(self, limit: int = 20) -> list[ImportBatch]:
        stmt = select(ImportBatch).order_by(ImportBatch.id.desc()).limit(limit)
        return list(self.db.scalars(stmt))
