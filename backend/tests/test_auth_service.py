from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
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
