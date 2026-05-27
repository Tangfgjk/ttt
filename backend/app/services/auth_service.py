from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auth import Role, User
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import ForgotPasswordRequest, RegisterRequest, UserSessionOut


DEFAULT_USERS = [
    {
        "role_code": "admin",
        "role_name": "管理员",
        "username": "admin",
        "email": "admin@ttt.local",
        "password": "admin123",
        "real_name": "系统管理员",
        "is_verified": True,
        "training_scope": "none",
    },
    {
        "role_code": "reviewer",
        "role_name": "复核员",
        "username": "reviewer",
        "email": "reviewer@ttt.local",
        "password": "reviewer123",
        "real_name": "示例复核员",
        "is_verified": True,
        "training_scope": "none",
    },
]

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5]{3,20}$")
RESERVED_USERNAMES = {"admin", "administrator", "reviewer", "管理员", "复核员", "系统管理员"}


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuthRepository(db)

    def login(self, login_name: str, password: str) -> UserSessionOut:
        self.bootstrap_default_users_if_needed()
        normalized_login_name = login_name.strip()
        user = self.repository.get_user_by_login(normalized_login_name)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        if user.password_hash != password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用",
            )

        self.repository.touch_last_login(user)
        self.db.commit()
        self.db.refresh(user)
        return self._to_session(user)

    def register(self, payload: RegisterRequest) -> UserSessionOut:
        self.bootstrap_default_users_if_needed()
        username = payload.username.strip()
        self._validate_registration(username, payload.password, payload.confirm_password)

        if self.repository.get_user_by_username(username) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在，请更换后再试",
            )

        annotator_role = self.repository.get_role_by_code("annotator")
        if annotator_role is None:
            annotator_role = self.repository.save_role(Role(code="annotator", name="标注员"))

        user = self.repository.save_user(
            User(
                username=username,
                email=None,
                password_hash=payload.password,
                role_id=annotator_role.id,
                real_name=username,
                is_active=True,
                is_verified=True,
                training_scope="none",
                must_change_password=False,
            )
        )
        self.db.commit()
        self.db.refresh(user)
        return self._to_session(user)

    def forgot_password(self, payload: ForgotPasswordRequest) -> str:
        self.bootstrap_default_users_if_needed()
        _ = self.repository.get_user_by_username(payload.username.strip())
        return "请联系系统管理员重置密码，重置后请使用临时密码登录并尽快修改。"

    def bootstrap_default_users_if_needed(self) -> None:
        for item in DEFAULT_USERS:
            role = self.repository.get_role_by_code(item["role_code"])
            if role is None:
                role = self.repository.save_role(
                    Role(
                        code=item["role_code"],
                        name=item["role_name"],
                    )
                )

            if self.repository.get_user_by_login(item["username"]) is not None:
                continue

            self.repository.save_user(
                User(
                    username=item["username"],
                    email=item["email"],
                    password_hash=item["password"],
                    role_id=role.id,
                    real_name=item["real_name"],
                    is_verified=item["is_verified"],
                    training_scope=item.get("training_scope", "none"),
                )
            )

        self.db.commit()

    def _to_session(self, user: User) -> UserSessionOut:
        return UserSessionOut(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.code,
            real_name=user.real_name,
            is_verified=user.is_verified,
            training_scope=user.training_scope,
            must_change_password=user.must_change_password,
        )

    def _validate_registration(self, username: str, password: str, confirm_password: str) -> None:
        if not USERNAME_PATTERN.match(username):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="用户名需为 3-20 位中文、字母、数字或下划线",
            )
        if username.lower() in RESERVED_USERNAMES or username in RESERVED_USERNAMES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="该用户名为系统保留名称，请更换后再试",
            )
        if password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="两次输入的密码不一致",
            )
        if len(password.strip()) < 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="密码长度至少为 6 位",
            )
