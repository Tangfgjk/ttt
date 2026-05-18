from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from shutil import copyfileobj
from typing import Iterable
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.importers.base import BaseImporter, ImporterError, make_json_safe
from app.importers.dataset1_labeled import Dataset1LabeledImporter
from app.importers.dataset2_question_json import Dataset2QuestionJsonImporter
from app.importers.dataset3_exam_sheet import Dataset3ExamSheetImporter
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
from app.models.dictionary import Catalog, KnowledgePoint, KnowledgeType, Textbook
from app.models.imports import DataSource, ImportBatch, SourceQuestionRecord
from app.models.question import Question, QuestionCatalog, QuestionContent, QuestionKnowledgePoint
from app.repositories.import_repository import ImportRepository
from app.schemas.imports import (
    ImportBatchDetailOut,
    ImportBatchOut,
    ImportBatchSummaryOut,
    ImportSourceRecordListOut,
    ImportSourceRecordOut,
)
from app.schemas.pagination import PageMeta
from app.services.annotation_policy import AnnotationPolicyStore
from app.services.embedding_service import EmbeddingService
from app.services.question_dedup_service import DedupDecision, DedupInput, QuestionDedupService

IMPORTER_REGISTRY: dict[str, type[BaseImporter]] = {
    "dataset1_labeled": Dataset1LabeledImporter,
    "dataset2_question_json": Dataset2QuestionJsonImporter,
    "dataset3_exam_sheet": Dataset3ExamSheetImporter,
}

QUESTION_TYPE_BY_BASE_INDEX = {
    1: "single_choice",
    2: "fill_blank",
    3: "essay",
}

QUESTION_TYPE_BY_LABEL = {
    "单选题": "single_choice",
    "填空题": "fill_blank",
    "解答题": "essay",
}


@dataclass(frozen=True)
class ImportExecutionResult:
    batch: ImportBatch
    summary: ImportBatchSummaryOut
    imported_records: int


class ImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ImportRepository(db)
        self.dedup_service = QuestionDedupService(db)
        self.policy_store = AnnotationPolicyStore(db)
        self.settings = get_settings()

    def list_batches(self) -> list[ImportBatch]:
        return self.repository.list_batches()

    def get_batch_detail(self, batch_id: int) -> ImportBatchDetailOut:
        batch = self.repository.get_batch_by_id(batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found.")

        records = self.repository.list_source_records_by_batch(batch_id)
        duplicate_counts = self.repository.count_duplicate_candidates_by_source_record(batch_id)
        summary = self._build_summary(batch_id)
        return ImportBatchDetailOut(
            batch=self.serialize_batch(batch),
            summary=summary,
            records=[self.serialize_source_record(item, duplicate_counts.get(item.id, 0)) for item in records],
        )

    def list_batch_source_records(
        self,
        batch_id: int,
        *,
        parse_status: str | None = None,
        normalized_question_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ImportSourceRecordListOut:
        batch = self.repository.get_batch_by_id(batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found.")

        offset = (page - 1) * page_size
        records = self.repository.list_source_records_by_batch(
            batch_id,
            parse_status=parse_status,
            normalized_question_id=normalized_question_id,
            offset=offset,
            limit=page_size,
        )
        duplicate_counts = self.repository.count_duplicate_candidates_by_source_record(batch_id)
        total = self.repository.count_source_records_by_batch(
            batch_id,
            parse_status=parse_status,
            normalized_question_id=normalized_question_id,
        )
        return ImportSourceRecordListOut(
            items=[self.serialize_source_record(item, duplicate_counts.get(item.id, 0)) for item in records],
            meta=PageMeta(page=page, page_size=page_size, total=total),
        )

    def import_local_file(self, data_source_code: str, file_path: str) -> ImportExecutionResult:
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {file_path}")

        data_source, importer_cls = self._resolve_source_and_importer(data_source_code)
        batch = self._create_batch(data_source=data_source, file_name=path.name)
        return self._execute_batch(data_source=data_source, importer_cls=importer_cls, batch=batch, file_path=path)

    def import_uploaded_file(self, data_source_code: str, upload: UploadFile) -> ImportExecutionResult:
        data_source, importer_cls = self._resolve_source_and_importer(data_source_code)
        original_name = upload.filename or "upload.bin"
        batch = self._create_batch(data_source=data_source, file_name=original_name)
        upload_path = self._persist_uploaded_file(batch.batch_no, original_name, upload)
        return self._execute_batch(
            data_source=data_source,
            importer_cls=importer_cls,
            batch=batch,
            file_path=upload_path,
        )

    def import_uploaded_files(
        self,
        data_source_code: str,
        uploads: list[UploadFile],
        *,
        folder_name: str | None = None,
    ) -> ImportExecutionResult:
        if not uploads:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files were uploaded.",
            )

        data_source, importer_cls = self._resolve_source_and_importer(data_source_code)
        display_name = self._resolve_multi_file_display_name(folder_name, uploads)
        batch = self._create_batch(data_source=data_source, file_name=display_name)
        upload_paths = [
            self._persist_uploaded_file(batch.batch_no, upload.filename or f"upload_{index}.bin", upload)
            for index, upload in enumerate(uploads, start=1)
        ]
        return self._execute_batch_files(
            data_source=data_source,
            importer_cls=importer_cls,
            batch=batch,
            file_paths=upload_paths,
            finalize=True,
        )

    def initialize_upload_batch(
        self,
        data_source_code: str,
        *,
        file_name: str,
        total_file_count: int = 0,
        expected_records: int | None = None,
    ) -> ImportBatch:
        data_source, _ = self._resolve_source_and_importer(data_source_code)
        batch = self._create_batch(
            data_source=data_source,
            file_name=file_name,
            import_status="RUNNING",
            total_file_count=total_file_count,
            expected_records=expected_records,
        )
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def append_uploaded_files_to_batch(
        self,
        batch_id: int,
        uploads: list[UploadFile],
        *,
        finalize: bool = False,
    ) -> ImportExecutionResult:
        if not uploads:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files were uploaded.",
            )

        batch = self.repository.get_batch_by_id(batch_id)
        if batch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import batch not found.",
            )
        if batch.import_status not in {"UPLOADING", "RUNNING", "QUEUED"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import batch is not accepting more files.",
            )
        if batch.data_source is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Import batch data source is missing.",
            )

        upload_paths = [
            self._persist_uploaded_file(batch.batch_no, upload.filename or f"upload_{index}.bin", upload)
            for index, upload in enumerate(uploads, start=1)
        ]

        batch.uploaded_file_count += len(uploads)
        if batch.total_file_count < batch.uploaded_file_count:
            batch.total_file_count = batch.uploaded_file_count
        batch.import_status = "RUNNING"
        batch.error_message = None
        batch.finished_at = None
        self.db.commit()
        self.db.refresh(batch)

        _, importer_cls = self._resolve_source_and_importer(batch.data_source.code)
        return self._execute_batch_files(
            data_source=batch.data_source,
            importer_cls=importer_cls,
            batch=batch,
            file_paths=upload_paths,
            finalize=finalize,
        )

    def process_enqueued_batch(self, batch_id: int) -> ImportExecutionResult:
        batch = self.repository.get_batch_by_id(batch_id)
        if batch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import batch not found.",
            )
        if batch.data_source is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Import batch data source is missing.",
            )
        if batch.import_status not in {"QUEUED", "RUNNING"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import batch is not ready for background processing.",
            )

        if batch.processing_started_at is None:
            batch.processing_started_at = datetime.utcnow()
        batch.import_status = "RUNNING"
        batch.error_message = None
        batch.finished_at = None
        self.db.commit()
        self.db.refresh(batch)

        _, importer_cls = self._resolve_source_and_importer(batch.data_source.code)
        file_paths = self._list_uploaded_files_for_batch(batch.batch_no)
        if batch.processed_file_count > 0:
            file_paths = file_paths[batch.processed_file_count :]
        return self._execute_batch_files(
            data_source=batch.data_source,
            importer_cls=importer_cls,
            batch=batch,
            file_paths=file_paths,
            finalize=True,
        )

    def attach_source_record_to_existing_question(
        self,
        source_record: SourceQuestionRecord,
        *,
        question_id: int,
        parse_status: str = "MATCHED_BY_REVIEW",
    ) -> Question:
        question = self.repository.get_question_by_id(question_id)
        if question is None:
            raise ValueError(f"Question {question_id} not found.")

        self.repository.ensure_external_ref(
            question_id=question.id,
            data_source_id=source_record.data_source_id,
            external_question_id=self._extract_external_question_id(source_record),
            external_type=self._extract_external_type(source_record),
            is_primary=False,
        )
        source_record.normalized_question_id = question.id
        source_record.parse_status = parse_status
        source_record.error_message = None

        data_source_code = source_record.data_source.code if source_record.data_source else ""
        if data_source_code == "dataset1_labeled":
            self._upsert_gold_label(question.id, source_record, source_record.raw_payload or {})
        elif data_source_code == "dataset3_exam_sheet":
            self._upsert_exam_domain_entities(question, source_record.raw_payload or {})
        return question

    def materialize_source_record_as_new_question(
        self,
        source_record: SourceQuestionRecord,
        *,
        parse_status: str = "CREATED_BY_REVIEW",
    ) -> Question:
        if source_record.data_source is None:
            raise ValueError("Source record data source is required.")

        data_source = source_record.data_source
        payload = source_record.raw_payload or {}

        if data_source.code == "dataset2_question_json":
            subject = self._require_subject(payload)
            question_type = self._resolve_question_type(payload)
            grade = self._resolve_grade(payload)
            question = self._create_question_from_dataset2(
                data_source=data_source,
                payload=payload,
                subject_id=subject.id,
                grade_id=grade.id if grade else None,
                question_type_id=question_type.id if question_type else None,
                fingerprint_hash=source_record.normalized_hash or "",
            )
        elif data_source.code == "dataset1_labeled":
            subject = self._require_subject({"subjectCategory": "math"})
            grade = self._resolve_grade(payload)
            question = self._create_minimal_question(
                data_source=data_source,
                external_question_id=self._extract_external_question_id(source_record),
                subject_id=subject.id,
                stem_text=self._first_text(payload, "question_text", "questionText") or "",
                answer_text=None,
                solution_text=None,
                question_type_id=None,
                grade_id=grade.id if grade else None,
                fingerprint_hash=source_record.normalized_hash or "",
            )
            self._upsert_gold_label(question.id, source_record, payload)
        elif data_source.code == "dataset3_exam_sheet":
            subject = self._require_subject({"subjectCategory": payload.get("测试学科") or "math"})
            grade = self._resolve_grade({"gradeIndex": payload.get("测试年级") or payload.get("年级编号")})
            question_type = self._resolve_question_type_from_label(str(payload.get("题型标签") or ""))
            question = self._create_minimal_question(
                data_source=data_source,
                external_question_id=self._extract_external_question_id(source_record),
                subject_id=subject.id,
                stem_text=self._first_text(payload, "题目内容", "题干（子题）") or "",
                answer_text=self._first_text(payload, "题目答案"),
                solution_text=None,
                question_type_id=question_type.id if question_type else None,
                grade_id=grade.id if grade else None,
                fingerprint_hash=source_record.normalized_hash or "",
                difficulty_level=self._safe_int(payload.get("难度标签")),
                blank_count=0,
                stem_html=self._first_text(payload, "题目内容"),
            )
            self._upsert_exam_domain_entities(question, payload)
        else:
            raise ValueError(f"Unsupported data source for review materialization: {data_source.code}")

        source_record.normalized_question_id = question.id
        source_record.parse_status = parse_status
        source_record.error_message = None
        return question

    def _execute_batch(
        self,
        *,
        data_source: DataSource,
        importer_cls: type[BaseImporter],
        batch: ImportBatch,
        file_path: Path,
    ) -> ImportExecutionResult:
        return self._execute_batch_files(
            data_source=data_source,
            importer_cls=importer_cls,
            batch=batch,
            file_paths=[file_path],
            finalize=True,
        )

    def _execute_batch_files(
        self,
        *,
        data_source: DataSource,
        importer_cls: type[BaseImporter],
        batch: ImportBatch,
        file_paths: Iterable[Path],
        finalize: bool,
    ) -> ImportExecutionResult:
        file_path_list = list(file_paths)
        if batch.total_file_count == 0:
            batch.total_file_count = batch.processed_file_count + len(file_path_list)
        if batch.uploaded_file_count < batch.total_file_count:
            batch.uploaded_file_count = batch.total_file_count
        if batch.processing_started_at is None:
            batch.processing_started_at = datetime.utcnow()
        batch.import_status = "RUNNING"
        batch.error_message = None
        batch.finished_at = None
        self.db.commit()
        self.db.refresh(batch)

        importer = importer_cls()
        try:
            for file_path in file_path_list:
                source_records: list[SourceQuestionRecord] = []
                normalized_question_ids: list[int] = []
                try:
                    parsed_records = importer.parse(file_path)
                    source_records.extend(
                        [
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
                    )
                except Exception as exc:
                    source_records.append(
                        SourceQuestionRecord(
                            import_batch_id=batch.id,
                            data_source_id=data_source.id,
                            source_record_key=self._trim_source_record_key(file_path.name),
                            record_type=importer.record_type,
                            raw_payload=make_json_safe(
                                {
                                    "source_file_name": file_path.name,
                                }
                            ),
                            parse_status="FAILED",
                            error_message=f"Failed to parse file {file_path.name}: {exc}",
                        )
                    )

                self.repository.add_source_records(source_records)

                for source_record in source_records:
                    if source_record.parse_status == "FAILED":
                        continue
                    self._normalize_source_record(data_source, source_record)
                    if source_record.normalized_question_id is not None:
                        normalized_question_ids.append(source_record.normalized_question_id)

                self._try_generate_embeddings(normalized_question_ids)

                chunk_total = len(source_records)
                chunk_failed = sum(1 for item in source_records if item.parse_status == "FAILED")
                chunk_success = chunk_total - chunk_failed
                batch.total_records += chunk_total
                batch.failed_records += chunk_failed
                batch.success_records += chunk_success
                batch.processed_file_count += 1
                batch.import_status = "RUNNING"
                batch.finished_at = None
                self.db.commit()
                self.db.refresh(batch)

            batch.import_status = self._resolve_batch_status(batch) if finalize else "RUNNING"
            batch.finished_at = datetime.utcnow() if finalize else None
            self.db.commit()
            self.db.refresh(batch)
            return ImportExecutionResult(
                batch=batch,
                summary=self._build_summary(batch.id),
                imported_records=len(source_records),
            )
        except Exception as exc:
            self.db.rollback()
            batch.import_status = "FAILED"
            batch.error_message = str(exc)
            batch.finished_at = datetime.utcnow()
            self.db.add(batch)
            self.db.commit()
            self.db.refresh(batch)
            status_code = (
                status.HTTP_400_BAD_REQUEST
                if isinstance(exc, ImporterError)
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    def _resolve_source_and_importer(
        self,
        data_source_code: str,
    ) -> tuple[DataSource, type[BaseImporter]]:
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
        return data_source, importer_cls

    def _create_batch(
        self,
        *,
        data_source: DataSource,
        file_name: str,
        import_status: str = "RUNNING",
        total_file_count: int = 0,
        expected_records: int | None = None,
    ) -> ImportBatch:
        batch = ImportBatch(
            data_source_id=data_source.id,
            batch_no=f"imp_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
            file_name=file_name,
            import_status=import_status,
            total_records=0,
            success_records=0,
            failed_records=0,
            total_file_count=total_file_count,
            uploaded_file_count=0,
            processed_file_count=0,
            expected_records=expected_records,
        )
        return self.repository.create_batch(batch)

    def _list_uploaded_files_for_batch(self, batch_no: str) -> list[Path]:
        upload_dir = self._uploads_dir()
        if not upload_dir.exists():
            return []
        return sorted(upload_dir.glob(f"{batch_no}_*"))

    def _persist_uploaded_file(
        self,
        batch_no: str,
        original_name: str,
        upload: UploadFile,
    ) -> Path:
        safe_name = Path(original_name).name or "upload.bin"
        upload_dir = self._uploads_dir()
        upload_dir.mkdir(parents=True, exist_ok=True)
        target_path = upload_dir / f"{batch_no}_{safe_name}"
        with target_path.open("wb") as buffer:
            copyfileobj(upload.file, buffer)
        return target_path

    def _resolve_multi_file_display_name(
        self,
        folder_name: str | None,
        uploads: list[UploadFile],
    ) -> str:
        clean_folder_name = (folder_name or "").strip()
        if clean_folder_name:
            return f"{clean_folder_name} ({len(uploads)} files)"
        if len(uploads) == 1:
            return uploads[0].filename or "upload.bin"
        return f"multi-file-upload ({len(uploads)} files)"

    @staticmethod
    def _trim_source_record_key(value: str) -> str:
        return value[:128]

    def _uploads_dir(self) -> Path:
        configured = getattr(self.settings, "import_upload_dir", None)
        if configured:
            return Path(configured)
        return Path(__file__).resolve().parents[2] / "uploads" / "imports"

    def _normalize_dataset2_record(
        self,
        data_source: DataSource,
        source_record: SourceQuestionRecord,
    ) -> None:
        try:
            payload = source_record.raw_payload or {}
            subject = self._require_subject(payload)
            question_type = self._resolve_question_type(payload)
            grade = self._resolve_grade(payload)
            stem_text = self._first_text(payload, "question", "stem", "content")
            if not stem_text:
                raise ValueError("Dataset2 record is missing question text.")

            answer_text = self._first_text(payload, "queAns", "answer", "answerText")
            decision = self.dedup_service.evaluate(
                DedupInput(
                    subject_id=subject.id,
                    question_type_id=question_type.id if question_type else None,
                    stem_text=stem_text,
                    answer_text=answer_text,
                    data_source_id=data_source.id,
                    external_question_id=str(payload.get("exerciseID") or source_record.source_record_key),
                    grade_id=grade.id if grade else None,
                    subquestion_count=int(payload.get("subQueNum") or 0),
                    source_record_id=source_record.id,
                )
            )
            source_record.normalized_hash = decision.fingerprint.content_hash
            source_record.parse_status = decision.status

            if decision.status == "CREATED_NEW_QUESTION":
                question = self._create_question_from_dataset2(
                    data_source=data_source,
                    payload=payload,
                    subject_id=subject.id,
                    grade_id=grade.id if grade else None,
                    question_type_id=question_type.id if question_type else None,
                    fingerprint_hash=decision.fingerprint.content_hash,
                )
                source_record.normalized_question_id = question.id
            elif decision.question_id is not None:
                source_record.normalized_question_id = decision.question_id
                self.repository.ensure_external_ref(
                    question_id=decision.question_id,
                    data_source_id=data_source.id,
                    external_question_id=str(payload.get("exerciseID") or source_record.source_record_key),
                    external_type=str(payload.get("exerciseType") or "") or None,
                    is_primary=False,
                )
        except Exception as exc:
            source_record.parse_status = "FAILED"
            source_record.error_message = str(exc)

    def _normalize_dataset1_record(
        self,
        data_source: DataSource,
        source_record: SourceQuestionRecord,
    ) -> None:
        try:
            payload = source_record.raw_payload or {}
            subject = self._require_subject({"subjectCategory": "math"})
            grade = self._resolve_grade(payload)
            stem_text = self._first_text(payload, "question_text", "questionText")
            if not stem_text:
                raise ValueError("Dataset1 record is missing question text.")

            fingerprint = self.dedup_service.evaluate(
                DedupInput(
                    subject_id=subject.id,
                    question_type_id=None,
                    stem_text=stem_text,
                    answer_text=None,
                    data_source_id=data_source.id,
                    external_question_id=str(payload.get("question_id") or source_record.source_record_key),
                    grade_id=grade.id if grade else None,
                    source_record_id=source_record.id,
                )
            ).fingerprint
            source_record.normalized_hash = fingerprint.content_hash

            question = self.repository.get_question_by_normalized_stem(
                normalized_stem_text=fingerprint.normalized_stem_text,
                subject_id=subject.id,
            )
            if question is None:
                question = self._create_minimal_question(
                    data_source=data_source,
                    external_question_id=str(payload.get("question_id") or source_record.source_record_key),
                    subject_id=subject.id,
                    stem_text=stem_text,
                    answer_text=None,
                    solution_text=None,
                    question_type_id=None,
                    grade_id=grade.id if grade else None,
                    fingerprint_hash=fingerprint.content_hash,
                )
                source_record.parse_status = "CREATED_NEW_QUESTION"
            else:
                if grade is not None and question.grade_id is None:
                    question.grade_id = grade.id
                    self.repository.save_question(question)
                self.repository.ensure_external_ref(
                    question_id=question.id,
                    data_source_id=data_source.id,
                    external_question_id=str(payload.get("question_id") or source_record.source_record_key),
                    external_type="gold_label",
                    is_primary=False,
                )
                source_record.parse_status = "MATCHED_BY_CONTENT_HASH"

            source_record.normalized_question_id = question.id
            self._upsert_gold_label(question.id, source_record, payload)
            self._mark_question_as_completed_from_gold_label(question)
        except Exception as exc:
            source_record.parse_status = "FAILED"
            source_record.error_message = str(exc)

    def _normalize_dataset3_record(
        self,
        data_source: DataSource,
        source_record: SourceQuestionRecord,
    ) -> None:
        try:
            payload = source_record.raw_payload or {}
            subject = self._require_subject({"subjectCategory": payload.get("测试学科") or "math"})
            grade = self._resolve_grade({"gradeIndex": payload.get("测试年级") or payload.get("年级编号")})
            question_type = self._resolve_question_type_from_label(str(payload.get("题型标签") or ""))
            stem_text = self._first_text(payload, "题目内容", "题干（子题）")
            if not stem_text:
                raise ValueError("Dataset3 record is missing question text.")

            answer_text = self._first_text(payload, "题目答案")
            decision = self.dedup_service.evaluate(
                DedupInput(
                    subject_id=subject.id,
                    question_type_id=question_type.id if question_type else None,
                    stem_text=stem_text,
                    answer_text=answer_text,
                    data_source_id=data_source.id,
                    external_question_id=str(payload.get("题目ID") or source_record.source_record_key),
                    grade_id=grade.id if grade else None,
                    source_record_id=source_record.id,
                )
            )
            source_record.normalized_hash = decision.fingerprint.content_hash
            source_record.parse_status = decision.status

            if decision.status == "CREATED_NEW_QUESTION":
                question = self._create_minimal_question(
                    data_source=data_source,
                    external_question_id=str(payload.get("题目ID") or source_record.source_record_key),
                    subject_id=subject.id,
                    stem_text=stem_text,
                    answer_text=answer_text,
                    solution_text=None,
                    question_type_id=question_type.id if question_type else None,
                    grade_id=grade.id if grade else None,
                    fingerprint_hash=decision.fingerprint.content_hash,
                    difficulty_level=self._safe_int(payload.get("难度标签")),
                    blank_count=0,
                    stem_html=self._first_text(payload, "题目内容"),
                )
            elif decision.question_id is not None:
                question = self.repository.get_question_by_id(decision.question_id)
                if question is None:
                    raise ValueError(f"Question {decision.question_id} not found after dedup match.")
                self.repository.ensure_external_ref(
                    question_id=question.id,
                    data_source_id=data_source.id,
                    external_question_id=str(payload.get("题目ID") or source_record.source_record_key),
                    external_type="exam_question",
                    is_primary=False,
                )
            else:
                raise ValueError(f"Unsupported dedup status for dataset3: {decision.status}")

            source_record.normalized_question_id = question.id
            self._upsert_exam_domain_entities(question, payload)
        except Exception as exc:
            source_record.parse_status = "FAILED"
            source_record.error_message = str(exc)

    def _create_question_from_dataset2(
        self,
        *,
        data_source: DataSource,
        payload: dict,
        subject_id: int,
        grade_id: int | None,
        question_type_id: int | None,
        fingerprint_hash: str,
    ) -> Question:
        sub_questions = payload.get("subQues") or []
        annotator_count = self.policy_store.get_annotator_count()
        question = self.repository.save_question(
            Question(
                subject_id=subject_id,
                grade_id=grade_id,
                question_type_id=question_type_id,
                difficulty_level=self._safe_int(payload.get("difficulty")),
                blank_count=self._safe_int(payload.get("blankCount"), default=0),
                has_subquestions=bool(payload.get("subQueNum") or sub_questions),
                source_status="ACTIVE",
                annotation_status="PENDING",
                required_annotations=annotator_count,
                annotation_count=0,
            )
        )
        content = self.repository.save_question_content(
            QuestionContent(
                question_id=question.id,
                stem_text=self._first_text(payload, "question", "stem", "content") or "",
                stem_html=self._first_text(payload, "questionHtml", "stemHtml"),
                answer_text=self._first_text(payload, "queAns", "answer", "answerText"),
                solution_text=self._first_text(payload, "solution", "analysis", "solutionText"),
                source_content_hash=fingerprint_hash,
            )
        )
        question.content = content
        self.repository.ensure_external_ref(
            question_id=question.id,
            data_source_id=data_source.id,
            external_question_id=str(payload.get("exerciseID")),
            external_type=str(payload.get("exerciseType") or "") or None,
            is_primary=True,
        )

        self.repository.replace_question_knowledge_points(
            question_id=question.id,
            knowledge_points=self._build_question_knowledge_points(question.id, payload),
        )
        self.repository.replace_question_catalogs(
            question_id=question.id,
            catalogs=self._build_question_catalogs(question.id, payload),
        )
        self.dedup_service.sync_question_feature(question)
        self._try_generate_question_embedding(question.id)
        return question

    def _build_question_knowledge_points(
        self,
        question_id: int,
        payload: dict,
    ) -> list[QuestionKnowledgePoint]:
        records: list[QuestionKnowledgePoint] = []
        seen_ids: set[tuple[int, int]] = set()
        for item in payload.get("tags") or []:
            knowledge_point = self._resolve_knowledge_point(item)
            key = (question_id, knowledge_point.id)
            if key in seen_ids:
                continue
            seen_ids.add(key)
            records.append(
                QuestionKnowledgePoint(
                    question_id=question_id,
                    knowledge_point_id=knowledge_point.id,
                    priority=self._safe_int(item.get("priority"), default=0),
                    is_core=bool(item.get("coreFlag")),
                    is_exam_point=bool(item.get("examPointFlag")),
                    is_last_exam_point=bool(item.get("lastExamPointFlag")),
                    sort_index=self._safe_int(item.get("sortIndex")),
                )
            )
        return records

    def _build_question_catalogs(
        self,
        question_id: int,
        payload: dict,
    ) -> list[QuestionCatalog]:
        records: list[QuestionCatalog] = []
        seen_ids: set[tuple[int, int]] = set()
        for item in payload.get("queCtlgs") or []:
            catalog = self._resolve_catalog(item)
            key = (question_id, catalog.id)
            if key in seen_ids:
                continue
            seen_ids.add(key)
            records.append(
                QuestionCatalog(
                    question_id=question_id,
                    catalog_id=catalog.id,
                    school_code=str(item.get("schCode") or "") or None,
                )
            )
        return records

    def _normalize_source_record(
        self,
        data_source: DataSource,
        source_record: SourceQuestionRecord,
    ) -> None:
        if data_source.code == "dataset2_question_json":
            self._normalize_dataset2_record(data_source, source_record)
            return
        if data_source.code == "dataset1_labeled":
            self._normalize_dataset1_record(data_source, source_record)
            return
        if data_source.code == "dataset3_exam_sheet":
            self._normalize_dataset3_record(data_source, source_record)

    def _upsert_gold_label(
        self,
        question_id: int,
        source_record: SourceQuestionRecord,
        payload: dict,
    ) -> None:
        cognitive_levels = payload.get("cognitive_levels") or {}
        competencies = payload.get("competencies") or {}

        cognitive_level_name = None
        cognitive_level_value = -1
        for name, value in cognitive_levels.items():
            int_value = self._safe_int(value, default=0) or 0
            if int_value > cognitive_level_value:
                cognitive_level_name = name
                cognitive_level_value = int_value

        cognitive_level = (
            self.repository.get_cognitive_level_by_name(cognitive_level_name)
            if cognitive_level_name
            else None
        )
        gold_label = self.repository.get_gold_label_by_question_id(question_id)
        if gold_label is None:
            gold_label = self.repository.save_gold_label(
                QuestionGoldLabel(
                    question_id=question_id,
                    source_record_id=source_record.id,
                    cognitive_level_id=cognitive_level.id if cognitive_level else None,
                    label_source="dataset1_labeled",
                )
            )
        else:
            gold_label.source_record_id = source_record.id
            gold_label.cognitive_level_id = cognitive_level.id if cognitive_level else None
            gold_label.label_source = "dataset1_labeled"
            self.repository.save_gold_label(gold_label)

        gold_competencies: list[QuestionGoldCompetency] = []
        for name, value in competencies.items():
            level_value = self._safe_int(value, default=0) or 0
            if level_value <= 0:
                continue
            competency = self.repository.get_competency_by_name(name)
            if competency is None:
                continue
            gold_competencies.append(
                QuestionGoldCompetency(
                    gold_label_id=gold_label.id,
                    competency_id=competency.id,
                    level_value=level_value,
                )
            )
        self.repository.replace_gold_competencies(
            gold_label_id=gold_label.id,
            competencies=gold_competencies,
        )

    def _mark_question_as_completed_from_gold_label(self, question: Question) -> None:
        required_annotations = question.required_annotations or self.policy_store.get_annotator_count()
        question.annotation_count = max(question.annotation_count or 0, required_annotations)
        question.annotation_status = "COMPLETED"
        self.repository.save_question(question)

    def _upsert_exam_domain_entities(self, question: Question, payload: dict) -> None:
        subject = self._require_subject({"subjectCategory": payload.get("测试学科") or "math"})
        grade = self._resolve_grade({"gradeIndex": payload.get("测试年级") or payload.get("年级编号")})

        school_class = self._upsert_class(
            grade_id=grade.id if grade else None,
            source_class_id=self._string_or_none(payload.get("班级编号")),
            class_name=self._first_text(payload, "测试班级") or "未命名班级",
            class_seq=self._safe_int(payload.get("班级序号")),
        )
        student = self._upsert_student(
            source_student_id=str(payload.get("学生编号")),
            grade_id=grade.id if grade else None,
            class_id=school_class.id if school_class else None,
        )
        exam = self._upsert_exam(
            source_exam_id=str(payload.get("考试ID")),
            exam_code=self._string_or_none(payload.get("考试编号")),
            exam_name=self._first_text(payload, "测试名称", "考试编号及名称") or str(payload.get("考试ID")),
            subject_id=subject.id,
            grade_id=grade.id if grade else None,
            exam_type=self._string_or_none(payload.get("测试类型")),
            term_name=self._string_or_none(payload.get("学期")),
            exam_time=payload.get("测试时间"),
            total_score=self._safe_decimal(payload.get("测试总分")),
        )

        self.repository.upsert_exam_question(
            ExamQuestion(
                exam_id=exam.id,
                question_id=question.id,
                question_no=self._string_or_none(payload.get("题号")),
                custom_question_no=self._string_or_none(payload.get("自定义题号")),
                score=self._safe_decimal(payload.get("题目分值")),
            )
        )
        self.repository.upsert_student_exam_score(
            StudentExamScore(
                exam_id=exam.id,
                student_id=student.id,
                class_id=school_class.id if school_class else None,
                total_score=self._safe_decimal(payload.get("测试得分")),
            )
        )
        self.repository.upsert_student_question_response(
            StudentQuestionResponse(
                exam_id=exam.id,
                question_id=question.id,
                student_id=student.id,
                response_text=self._string_or_none(payload.get("学生作答")),
                response_score=self._safe_decimal(payload.get("题目得分")),
                subquestion_answer_text=self._string_or_none(payload.get("子题答案")),
            )
        )

    def _create_minimal_question(
        self,
        *,
        data_source: DataSource,
        external_question_id: str,
        subject_id: int,
        stem_text: str,
        answer_text: str | None,
        solution_text: str | None,
        question_type_id: int | None,
        grade_id: int | None,
        fingerprint_hash: str,
        difficulty_level: int | None = None,
        blank_count: int = 0,
        stem_html: str | None = None,
    ) -> Question:
        annotator_count = self.policy_store.get_annotator_count()
        question = self.repository.save_question(
            Question(
                subject_id=subject_id,
                grade_id=grade_id,
                question_type_id=question_type_id,
                difficulty_level=difficulty_level,
                blank_count=blank_count,
                has_subquestions=False,
                source_status="ACTIVE",
                annotation_status="PENDING",
                required_annotations=annotator_count,
                annotation_count=0,
            )
        )
        content = self.repository.save_question_content(
            QuestionContent(
                question_id=question.id,
                stem_text=stem_text,
                stem_html=stem_html,
                answer_text=answer_text,
                solution_text=solution_text,
                source_content_hash=fingerprint_hash,
            )
        )
        question.content = content
        self.repository.ensure_external_ref(
            question_id=question.id,
            data_source_id=data_source.id,
            external_question_id=external_question_id,
            is_primary=True,
        )
        self.dedup_service.sync_question_feature(question)
        self._try_generate_question_embedding(question.id)
        return question

    def _try_generate_question_embedding(self, question_id: int) -> None:
        try:
            EmbeddingService(self.db).ensure_question_embedding(question_id)
        except Exception:
            return

    def _try_generate_embeddings(self, question_ids: list[int]) -> None:
        if not question_ids:
            return
        try:
            unique_question_ids = list(dict.fromkeys(question_ids))
            EmbeddingService(self.db).ensure_embeddings(unique_question_ids)
        except Exception:
            return

    def _require_subject(self, payload: dict):
        subject_code = str(payload.get("subjectCategory") or "math")
        subject = self.repository.get_subject_by_code(subject_code)
        if subject is None:
            raise ValueError(f"Subject not found for code: {subject_code}")
        return subject

    def _resolve_grade(self, payload: dict):
        grade_index = self._safe_int(payload.get("gradeIndex"))
        if grade_index is None:
            return None
        return self.repository.get_grade_by_index(grade_index)

    def _resolve_question_type(self, payload: dict):
        exercise_type = str(payload.get("exerciseType") or "").strip()
        if exercise_type:
            question_type = self.repository.get_question_type_by_code(exercise_type)
            if question_type is not None:
                return question_type

        fallback_code = QUESTION_TYPE_BY_BASE_INDEX.get(self._safe_int(payload.get("baseTypeIndex")))
        if fallback_code:
            return self.repository.get_question_type_by_code(fallback_code)
        return None

    def _resolve_question_type_from_label(self, label: str):
        code = QUESTION_TYPE_BY_LABEL.get(label.strip())
        if code:
            return self.repository.get_question_type_by_code(code)
        return None

    def _resolve_knowledge_point(self, payload: dict) -> KnowledgePoint:
        source_type_code = str(payload.get("knowTypeId") or payload.get("knowTypeName") or "unknown")
        source_type_name = str(payload.get("knowTypeName") or "Unknown")
        knowledge_type = self.repository.get_knowledge_type_by_source_code(source_type_code)
        if knowledge_type is None:
            knowledge_type = self.repository.save_knowledge_type(
                KnowledgeType(
                    source_type_code=source_type_code,
                    source_type_name=source_type_name,
                )
            )

        source_knowledge_id = str(payload.get("knowId") or payload.get("knowName") or uuid4().hex)
        knowledge_point = self.repository.get_knowledge_point_by_source_id(
            source_knowledge_id=source_knowledge_id,
            knowledge_type_id=knowledge_type.id,
        )
        if knowledge_point is not None:
            return knowledge_point

        return self.repository.save_knowledge_point(
            KnowledgePoint(
                source_knowledge_id=source_knowledge_id,
                knowledge_type_id=knowledge_type.id,
                name=str(payload.get("knowName") or source_knowledge_id),
                is_active=True,
            )
        )

    def _resolve_catalog(self, payload: dict) -> Catalog:
        textbook_id = None
        source_textbook_id = str(payload.get("textbookId") or "")
        if source_textbook_id:
            textbook = self.repository.get_textbook_by_source_id(source_textbook_id)
            if textbook is None:
                textbook = self.repository.save_textbook(
                    Textbook(
                        source_textbook_id=source_textbook_id,
                        name=source_textbook_id,
                    )
                )
            textbook_id = textbook.id

        source_catalog_id = str(payload.get("catalogId") or uuid4().hex)
        school_code = str(payload.get("schCode") or "") or None
        catalog = self.repository.get_catalog_by_source_id(
            source_catalog_id=source_catalog_id,
            textbook_id=textbook_id,
            school_code=school_code,
        )
        if catalog is not None:
            if not catalog.school_code and school_code:
                catalog.school_code = school_code
                self.repository.save_catalog(catalog)
            return catalog

        return self.repository.save_catalog(
            Catalog(
                source_catalog_id=source_catalog_id,
                textbook_id=textbook_id,
                name=source_catalog_id,
                school_code=school_code,
            )
        )

    def _build_summary(self, batch_id: int) -> ImportBatchSummaryOut:
        counts = self.repository.summarize_batch_statuses(batch_id)
        return ImportBatchSummaryOut(
            total_records=sum(counts.values()),
            raw_imported=counts.get("RAW_IMPORTED", 0),
            created_new_question=counts.get("CREATED_NEW_QUESTION", 0),
            matched_by_external_id=counts.get("MATCHED_BY_EXTERNAL_ID", 0),
            matched_by_content_hash=counts.get("MATCHED_BY_CONTENT_HASH", 0),
            pending_review=counts.get("PENDING_REVIEW", 0),
            failed=counts.get("FAILED", 0),
        )

    def serialize_batch(self, batch: ImportBatch) -> ImportBatchOut:
        return ImportBatchOut(
            id=batch.id,
            data_source_id=batch.data_source_id,
            data_source_code=batch.data_source.code,
            data_source_name=batch.data_source.name,
            batch_no=batch.batch_no,
            file_name=batch.file_name,
            import_status=batch.import_status,
            total_records=batch.total_records,
            success_records=batch.success_records,
            failed_records=batch.failed_records,
            total_file_count=batch.total_file_count,
            uploaded_file_count=batch.uploaded_file_count,
            processed_file_count=batch.processed_file_count,
            expected_records=batch.expected_records,
            error_message=batch.error_message,
            created_at=batch.created_at,
            processing_started_at=batch.processing_started_at,
            finished_at=batch.finished_at,
        )

    def serialize_source_record(
        self,
        source_record: SourceQuestionRecord,
        duplicate_candidate_count: int = 0,
    ) -> ImportSourceRecordOut:
        payload = source_record.raw_payload or {}
        normalized_preview = None
        if source_record.normalized_question and source_record.normalized_question.content:
            normalized_preview = source_record.normalized_question.content.stem_text

        return ImportSourceRecordOut(
            id=source_record.id,
            source_record_key=source_record.source_record_key,
            record_type=source_record.record_type,
            parse_status=source_record.parse_status,
            normalized_hash=source_record.normalized_hash,
            normalized_question_id=source_record.normalized_question_id,
            duplicate_candidate_count=duplicate_candidate_count,
            source_preview=self._first_text(payload, "question", "stem", "content", "question_text", "questionText"),
            normalized_question_preview=normalized_preview,
            raw_payload=payload,
            error_message=source_record.error_message,
        )

    @staticmethod
    def _resolve_batch_status(batch: ImportBatch) -> str:
        if batch.total_records == 0:
            return "FAILED"
        if batch.failed_records == 0:
            return "SUCCESS"
        if batch.success_records == 0:
            return "FAILED"
        return "PARTIAL_SUCCESS"

    @staticmethod
    def _safe_int(value, *, default: int | None = None) -> int | None:
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_decimal(value) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _first_text(payload: dict, *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                return str(value)
        return None

    @staticmethod
    def _string_or_none(value) -> str | None:
        if value in (None, ""):
            return None
        return str(value)

    def _extract_external_question_id(self, source_record: SourceQuestionRecord) -> str:
        payload = source_record.raw_payload or {}
        data_source_code = source_record.data_source.code if source_record.data_source else ""
        if data_source_code == "dataset2_question_json":
            return str(payload.get("exerciseID") or source_record.source_record_key)
        if data_source_code == "dataset1_labeled":
            return str(payload.get("question_id") or source_record.source_record_key)
        if data_source_code == "dataset3_exam_sheet":
            return str(payload.get("题目ID") or source_record.source_record_key)
        return source_record.source_record_key

    def _extract_external_type(self, source_record: SourceQuestionRecord) -> str | None:
        payload = source_record.raw_payload or {}
        data_source_code = source_record.data_source.code if source_record.data_source else ""
        if data_source_code == "dataset2_question_json":
            return self._string_or_none(payload.get("exerciseType"))
        if data_source_code == "dataset1_labeled":
            return "gold_label"
        if data_source_code == "dataset3_exam_sheet":
            return "exam_question"
        return None

    def _upsert_class(
        self,
        *,
        grade_id: int | None,
        source_class_id: str | None,
        class_name: str,
        class_seq: int | None,
    ) -> SchoolClass | None:
        if source_class_id is None and not class_name:
            return None
        school_class = self.repository.get_class_by_source_id(
            source_class_id=source_class_id,
            grade_id=grade_id,
        )
        if school_class is None:
            return self.repository.save_class(
                SchoolClass(
                    source_class_id=source_class_id,
                    grade_id=grade_id,
                    class_name=class_name,
                    class_seq=class_seq,
                )
            )
        school_class.class_name = class_name
        school_class.class_seq = class_seq
        school_class.grade_id = grade_id
        return self.repository.save_class(school_class)

    def _upsert_student(
        self,
        *,
        source_student_id: str,
        grade_id: int | None,
        class_id: int | None,
    ) -> Student:
        student = self.repository.get_student_by_source_id(source_student_id)
        if student is None:
            return self.repository.save_student(
                Student(
                    source_student_id=source_student_id,
                    grade_id=grade_id,
                    class_id=class_id,
                )
            )
        student.grade_id = grade_id
        student.class_id = class_id
        return self.repository.save_student(student)

    def _upsert_exam(
        self,
        *,
        source_exam_id: str,
        exam_code: str | None,
        exam_name: str,
        subject_id: int,
        grade_id: int | None,
        exam_type: str | None,
        term_name: str | None,
        exam_time,
        total_score: Decimal | None,
    ) -> Exam:
        parsed_exam_time = self._safe_datetime(exam_time)
        exam = self.repository.get_exam_by_source_id(source_exam_id)
        if exam is None:
            return self.repository.save_exam(
                Exam(
                    source_exam_id=source_exam_id,
                    exam_code=exam_code,
                    exam_name=exam_name,
                    subject_id=subject_id,
                    grade_id=grade_id,
                    exam_type=exam_type,
                    term_name=term_name,
                    exam_time=parsed_exam_time,
                    total_score=total_score,
                )
            )
        exam.exam_code = exam_code
        exam.exam_name = exam_name
        exam.subject_id = subject_id
        exam.grade_id = grade_id
        exam.exam_type = exam_type
        exam.term_name = term_name
        exam.exam_time = parsed_exam_time
        exam.total_score = total_score
        return self.repository.save_exam(exam)

    @staticmethod
    def _safe_datetime(value) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None
