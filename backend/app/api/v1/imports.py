from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.imports import (
    ImportBatchDetailOut,
    ImportBatchOut,
    ImportRunResponse,
    ImportSourceRecordListOut,
    LocalImportRequest,
)
from app.services.import_background_jobs import enqueue_import_batch
from app.services.import_service import ImportService

router = APIRouter()


@router.get("/batches", response_model=list[ImportBatchOut])
async def list_import_batches(db: Session = Depends(get_db)) -> list[ImportBatchOut]:
    service = ImportService(db)
    return [service.serialize_batch(item) for item in service.list_batches()]


@router.get("/batches/{batch_id}", response_model=ImportBatchDetailOut)
async def get_import_batch_detail(
    batch_id: int,
    db: Session = Depends(get_db),
) -> ImportBatchDetailOut:
    service = ImportService(db)
    return service.get_batch_detail(batch_id)


@router.get("/batches/{batch_id}/records", response_model=ImportSourceRecordListOut)
async def list_import_batch_records(
    batch_id: int,
    parse_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ImportSourceRecordListOut:
    service = ImportService(db)
    return service.list_batch_source_records(
        batch_id,
        parse_status=parse_status,
        page=page,
        page_size=page_size,
    )


@router.post("/run-local", response_model=ImportRunResponse)
async def run_local_import(
    payload: LocalImportRequest,
    db: Session = Depends(get_db),
) -> ImportRunResponse:
    service = ImportService(db)
    result = service.import_local_file(payload.data_source_code, payload.file_path)
    batch = service.get_batch_detail(result.batch.id)
    return ImportRunResponse(
        batch=batch.batch,
        summary=batch.summary,
        imported_records=result.imported_records,
    )


@router.post("/upload", response_model=ImportRunResponse)
async def upload_import_file(
    data_source_code: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ImportRunResponse:
    service = ImportService(db)
    result = service.import_uploaded_file(data_source_code, file)
    batch = service.get_batch_detail(result.batch.id)
    return ImportRunResponse(
        batch=batch.batch,
        summary=batch.summary,
        imported_records=result.imported_records,
    )


@router.post("/upload-folder", response_model=ImportRunResponse)
async def upload_import_folder(
    data_source_code: str = Form(...),
    folder_name: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> ImportRunResponse:
    service = ImportService(db)
    result = service.import_uploaded_files(
        data_source_code,
        files,
        folder_name=folder_name,
    )
    batch = service.get_batch_detail(result.batch.id)
    return ImportRunResponse(
        batch=batch.batch,
        summary=batch.summary,
        imported_records=result.imported_records,
    )


@router.post("/upload-folder/init", response_model=ImportBatchOut)
async def initialize_import_folder_upload(
    data_source_code: str = Form(...),
    folder_name: str | None = Form(default=None),
    file_count: int | None = Form(default=None),
    expected_records: int | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ImportBatchOut:
    service = ImportService(db)
    clean_name = folder_name.strip() if folder_name else "folder-upload"
    display_name = f"{clean_name} ({file_count} files)" if file_count and file_count > 1 else clean_name
    batch = service.initialize_upload_batch(
        data_source_code,
        file_name=display_name,
        total_file_count=file_count or 0,
        expected_records=expected_records,
    )
    return service.serialize_batch(batch)


@router.post("/batches/{batch_id}/upload-chunk", response_model=ImportRunResponse)
async def upload_import_batch_chunk(
    batch_id: int,
    finalize: bool = Form(default=False),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> ImportRunResponse:
    service = ImportService(db)
    result = service.append_uploaded_files_to_batch(
        batch_id,
        files,
        finalize=finalize,
    )
    if finalize:
        enqueue_import_batch(result.batch.id)
    batch = service.get_batch_detail(result.batch.id)
    return ImportRunResponse(
        batch=batch.batch,
        summary=batch.summary,
        imported_records=result.imported_records,
    )
