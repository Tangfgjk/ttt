from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.training import (
    TrainingAttemptResponse,
    TrainingModuleResponse,
    TrainingStage,
    TrainingStatusResponse,
    TrainingSubmitRequest,
    TrainingSubmitResponse,
)
from app.services.training_service import TrainingService

router = APIRouter()


@router.get("/status", response_model=TrainingStatusResponse)
async def get_training_status(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
) -> TrainingStatusResponse:
    return TrainingService(db).get_status(user_id)


@router.get("/modules/{stage}", response_model=TrainingModuleResponse)
async def get_training_module(
    stage: TrainingStage,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
) -> TrainingModuleResponse:
    return TrainingService(db).get_module(user_id, stage)


@router.get("/attempts/{stage}", response_model=list[TrainingAttemptResponse])
async def list_training_attempts(
    stage: TrainingStage,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[TrainingAttemptResponse]:
    return TrainingService(db).list_attempts(user_id, stage)


@router.post("/submit", response_model=TrainingSubmitResponse)
async def submit_training(
    payload: TrainingSubmitRequest,
    db: Session = Depends(get_db),
) -> TrainingSubmitResponse:
    return TrainingService(db).submit_training(payload)
