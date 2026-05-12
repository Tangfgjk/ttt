from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.active_learning import (
    ActiveLearningOverviewResponse,
    CoresetRunCreateRequest,
    CoresetRunOut,
    ModelVersionOut,
    PredictionRunCreateRequest,
    PredictionRunOut,
    TrainingRunCreateRequest,
    TrainingRunLogOut,
    TrainingRunOut,
)
from app.services.active_learning_service import ActiveLearningService

router = APIRouter()


@router.get("/overview", response_model=ActiveLearningOverviewResponse)
async def get_active_learning_overview(
    db: Session = Depends(get_db),
) -> ActiveLearningOverviewResponse:
    return ActiveLearningService(db).overview()


@router.post("/training-runs", response_model=TrainingRunOut)
async def start_training_run(
    payload: TrainingRunCreateRequest,
    db: Session = Depends(get_db),
) -> TrainingRunOut:
    return ActiveLearningService(db).start_training_run(payload)


@router.get("/training-runs", response_model=list[TrainingRunOut])
async def list_training_runs(db: Session = Depends(get_db)) -> list[TrainingRunOut]:
    return ActiveLearningService(db).list_training_runs()


@router.get("/training-runs/{run_id}", response_model=TrainingRunOut)
async def get_training_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> TrainingRunOut:
    return ActiveLearningService(db).get_training_run(run_id)


@router.get("/training-runs/{run_id}/logs", response_model=TrainingRunLogOut)
async def get_training_run_logs(
    run_id: int,
    db: Session = Depends(get_db),
) -> TrainingRunLogOut:
    return ActiveLearningService(db).get_training_run_logs(run_id)


@router.post("/training-runs/{run_id}/cancel", response_model=TrainingRunOut)
async def cancel_training_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> TrainingRunOut:
    return ActiveLearningService(db).cancel_training_run(run_id)


@router.get("/model-versions", response_model=list[ModelVersionOut])
async def list_model_versions(db: Session = Depends(get_db)) -> list[ModelVersionOut]:
    return ActiveLearningService(db).list_model_versions()


@router.post("/model-versions/{model_version_id}/activate", response_model=ModelVersionOut)
async def activate_model_version(
    model_version_id: int,
    db: Session = Depends(get_db),
) -> ModelVersionOut:
    return ActiveLearningService(db).activate_model_version(model_version_id)


@router.post("/prediction-runs", response_model=PredictionRunOut)
async def start_prediction_run(
    payload: PredictionRunCreateRequest,
    db: Session = Depends(get_db),
) -> PredictionRunOut:
    return ActiveLearningService(db).start_prediction_run(payload)


@router.get("/prediction-runs", response_model=list[PredictionRunOut])
async def list_prediction_runs(db: Session = Depends(get_db)) -> list[PredictionRunOut]:
    return ActiveLearningService(db).list_prediction_runs()


@router.get("/prediction-runs/{run_id}", response_model=PredictionRunOut)
async def get_prediction_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> PredictionRunOut:
    return ActiveLearningService(db).get_prediction_run(run_id)


@router.post("/prediction-runs/{run_id}/cancel", response_model=PredictionRunOut)
async def cancel_prediction_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> PredictionRunOut:
    return ActiveLearningService(db).cancel_prediction_run(run_id)


@router.post("/coreset-runs", response_model=CoresetRunOut)
async def start_coreset_run(
    payload: CoresetRunCreateRequest,
    db: Session = Depends(get_db),
) -> CoresetRunOut:
    return ActiveLearningService(db).start_coreset_run(payload)


@router.get("/coreset-runs", response_model=list[CoresetRunOut])
async def list_coreset_runs(db: Session = Depends(get_db)) -> list[CoresetRunOut]:
    return ActiveLearningService(db).list_coreset_runs()


@router.get("/coreset-runs/{run_id}", response_model=CoresetRunOut)
async def get_coreset_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> CoresetRunOut:
    return ActiveLearningService(db).get_coreset_run(run_id)


@router.post("/coreset-runs/{run_id}/cancel", response_model=CoresetRunOut)
async def cancel_coreset_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> CoresetRunOut:
    return ActiveLearningService(db).cancel_coreset_run(run_id)
