from fastapi import APIRouter

from app.schemas.common import MessageResponse

router = APIRouter()


@router.post("/submit", response_model=MessageResponse)
async def submit_annotation_placeholder() -> MessageResponse:
    return MessageResponse(
        message="Annotation module skeleton is ready. Implement submit workflow next."
    )
