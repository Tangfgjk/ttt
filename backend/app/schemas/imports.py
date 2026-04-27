from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocalImportRequest(BaseModel):
    data_source_code: str = Field(description="Data source code.")
    file_path: str = Field(description="Absolute local file path.")


class ImportBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_source_id: int
    data_source_code: str
    data_source_name: str
    batch_no: str
    file_name: str
    import_status: str
    total_records: int
    success_records: int
    failed_records: int
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ImportBatchSummaryOut(BaseModel):
    total_records: int
    raw_imported: int = 0
    created_new_question: int = 0
    matched_by_external_id: int = 0
    matched_by_content_hash: int = 0
    pending_review: int = 0
    failed: int = 0


class ImportSourceRecordOut(BaseModel):
    id: int
    source_record_key: str
    record_type: str
    parse_status: str
    normalized_hash: str | None = None
    normalized_question_id: int | None = None
    duplicate_candidate_count: int = 0
    error_message: str | None = None


class ImportBatchDetailOut(BaseModel):
    batch: ImportBatchOut
    summary: ImportBatchSummaryOut
    records: list[ImportSourceRecordOut]


class ImportRunResponse(BaseModel):
    batch: ImportBatchOut
    summary: ImportBatchSummaryOut
    imported_records: int

