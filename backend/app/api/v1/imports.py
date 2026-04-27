from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.imports import ImportBatchDetailOut, ImportBatchOut, ImportRunResponse, LocalImportRequest
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
