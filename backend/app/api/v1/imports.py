from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.imports import ImportBatchOut, ImportRunResponse, LocalImportRequest
from app.services.import_service import ImportService

router = APIRouter()


@router.get("/batches", response_model=list[ImportBatchOut])
async def list_import_batches(db: Session = Depends(get_db)) -> list[ImportBatchOut]:
    service = ImportService(db)
    return [ImportBatchOut.model_validate(item) for item in service.list_batches()]


@router.post("/run-local", response_model=ImportRunResponse)
async def run_local_import(
    payload: LocalImportRequest,
    db: Session = Depends(get_db),
) -> ImportRunResponse:
    service = ImportService(db)
    batch, imported_records = service.import_local_file(payload.data_source_code, payload.file_path)
    return ImportRunResponse(
        batch=ImportBatchOut.model_validate(batch),
        imported_records=imported_records,
    )
