from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import ForgotPasswordRequest, LoginRequest, LoginResponse, RegisterRequest
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    service = AuthService(db)
    user = service.login(payload.username, payload.password)
    return LoginResponse(message="登录成功", user=user)


@router.post("/register", response_model=LoginResponse)
async def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    service = AuthService(db)
    user = service.register(payload)
    return LoginResponse(message="注册成功，请开始培训准入", user=user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = AuthService(db)
    return MessageResponse(message=service.forgot_password(payload))
