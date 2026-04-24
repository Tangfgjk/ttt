from fastapi import APIRouter

from app.schemas.common import MessageResponse

router = APIRouter()


@router.post("/login", response_model=MessageResponse)
async def login_placeholder() -> MessageResponse:
    # Placeholder endpoint so frontend and backend can start integrating before
    # the full auth module is implemented.
    return MessageResponse(message="Auth module skeleton is ready. Implement real login next.")
