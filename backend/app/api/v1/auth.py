from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    service = AuthService(db)
    user = service.login(payload.username, payload.password)
    return LoginResponse(message="Login successful", user=user)
