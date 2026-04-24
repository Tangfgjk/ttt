from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.importers.base import BaseImporter, ImporterError, make_json_safe
from app.importers.dataset1_labeled import Dataset1LabeledImporter
from app.importers.dataset2_question_json import Dataset2QuestionJsonImporter
from app.importers.dataset3_exam_sheet import Dataset3ExamSheetImporter
from app.models.imports import ImportBatch, SourceQuestionRecord
from app.repositories.import_repository import ImportRepository

IMPORTER_REGISTRY: dict[str, type[BaseImporter]] = {
    "dataset1_labeled": Dataset1LabeledImporter,
    "dataset2_question_json": Dataset2QuestionJsonImporter,
    "dataset3_exam_sheet": Dataset3ExamSheetImporter,
}


class ImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ImportRepository(db)

    def list_batches(self) -> list[ImportBatch]:
        return self.repository.list_batches()

    def import_local_file(self, data_source_code: str, file_path: str) -> tuple[ImportBatch, int]:
        data_source = self.repository.get_data_source_by_code(data_source_code)
        if data_source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown data source: {data_source_code}",
            )

        importer_cls = IMPORTER_REGISTRY.get(data_source_code)
        if importer_cls is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No importer registered for data source: {data_source_code}",
            )

        path = Path(file_path)
        batch = ImportBatch(
            data_source_id=data_source.id,
            batch_no=f"imp_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
            file_name=path.name,
            import_status="RUNNING",
            total_records=0,
            success_records=0,
            failed_records=0,
        )
        self.repository.create_batch(batch)

        importer = importer_cls()
        try:
            parsed_records = importer.parse(path)
            source_records = [
                SourceQuestionRecord(
                    import_batch_id=batch.id,
                    data_source_id=data_source.id,
                    source_record_key=item["source_record_key"],
                    record_type=importer.record_type,
                    raw_payload=make_json_safe(item["raw_payload"]),
                    parse_status="RAW_IMPORTED",
                )
                for item in parsed_records
            ]
            self.repository.add_source_records(source_records)
            batch.total_records = len(parsed_records)
            batch.success_records = len(parsed_records)
            batch.import_status = "SUCCESS"
            batch.finished_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(batch)
            return batch, len(parsed_records)
        except Exception as exc:
            self.db.rollback()
            error_batch = ImportBatch(
                data_source_id=data_source.id,
                batch_no=f"imp_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
                file_name=path.name,
                import_status="FAILED",
                total_records=0,
                success_records=0,
                failed_records=0,
                error_message=str(exc),
                finished_at=datetime.utcnow(),
            )
            self.repository.create_batch(error_batch)
            self.db.commit()
            self.db.refresh(error_batch)
            status_code = (
                status.HTTP_400_BAD_REQUEST
                if isinstance(exc, ImporterError)
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
