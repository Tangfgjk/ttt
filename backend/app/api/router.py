from fastapi import APIRouter

from app.api.v1 import (
    active_learning,
    annotations,
    auth,
    dedup_review,
    dictionaries,
    imports,
    questions,
    system,
    training,
    visualization,
)

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dictionaries.router, prefix="/dictionaries", tags=["dictionaries"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(dedup_review.router, prefix="/dedup-review", tags=["dedup-review"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
api_router.include_router(training.router, prefix="/training", tags=["training"])
api_router.include_router(visualization.router, prefix="/visualization", tags=["visualization"])
api_router.include_router(
    active_learning.router,
    prefix="/active-learning",
    tags=["active-learning"],
)
