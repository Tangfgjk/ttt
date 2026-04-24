from fastapi import APIRouter

from app.api.v1 import annotations, auth, dictionaries, imports, questions, system

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dictionaries.router, prefix="/dictionaries", tags=["dictionaries"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
