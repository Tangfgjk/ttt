from __future__ import annotations

from threading import Lock, Thread

from fastapi import HTTPException

from app.db.session import SessionLocal
from app.services.import_service import ImportService

_running_batch_ids: set[int] = set()
_running_batch_ids_lock = Lock()


def enqueue_import_batch(batch_id: int) -> None:
    with _running_batch_ids_lock:
        if batch_id in _running_batch_ids:
            return
        _running_batch_ids.add(batch_id)

    thread = Thread(target=_run_import_batch, args=(batch_id,), daemon=True)
    thread.start()


def _run_import_batch(batch_id: int) -> None:
    db = SessionLocal()
    try:
        service = ImportService(db)
        service.process_enqueued_batch(batch_id)
    except HTTPException:
        pass
    finally:
        db.close()
        with _running_batch_ids_lock:
            _running_batch_ids.discard(batch_id)
