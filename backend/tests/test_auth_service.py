from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_login_bootstraps_default_users_and_returns_admin_session() -> None:
    db = _build_session()
    service = AuthService(db)

    session = service.login("admin", "admin123")

    assert session.username == "admin"
    assert session.role == "admin"
    assert session.training_scope == "none"


def test_login_rejects_wrong_password() -> None:
    db = _build_session()
    service = AuthService(db)
    service.bootstrap_default_users_if_needed()

    try:
        service.login("admin", "wrong-password")
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "用户名或密码错误"
    else:
        raise AssertionError("Expected wrong-password login to fail.")


def test_register_creates_annotator_user() -> None:
    db = _build_session()
    service = AuthService(db)

    session = service.register(
        RegisterRequest(
            username="新标注员1",
            password="annotator123",
            confirm_password="annotator123",
        )
    )

    assert session.username == "新标注员1"
    assert session.role == "annotator"
    assert session.training_scope == "none"


def test_register_rejects_reserved_username() -> None:
    db = _build_session()
    service = AuthService(db)

    try:
        service.register(
            RegisterRequest(
                username="admin",
                password="annotator123",
                confirm_password="annotator123",
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "该用户名为系统保留名称，请更换后再试"
    else:
        raise AssertionError("Expected reserved username registration to fail.")
