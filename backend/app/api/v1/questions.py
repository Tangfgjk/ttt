from fastapi import APIRouter

from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("/", response_model=MessageResponse)
async def list_questions_placeholder() -> MessageResponse:
    return MessageResponse(message="Question module skeleton is ready. Implement query API next.")
