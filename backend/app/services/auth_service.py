from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auth import Role, User
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import UserSessionOut


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
        "role_code": "annotator",
        "role_name": "标注员",
        "username": "annotator",
        "email": "annotator@ttt.local",
        "password": "annotator123",
        "real_name": "示例标注员",
        "is_verified": True,
        "training_scope": "none",
    },
    {
        "role_code": "annotator",
        "role_name": "标注员",
        "username": "annotator_dev_1",
        "email": "annotator_dev_1@ttt.local",
        "password": "annotator123",
        "real_name": "开发标注员1",
        "is_verified": True,
        "training_scope": "none",
    },
    {
        "role_code": "annotator",
        "role_name": "标注员",
        "username": "annotator_dev_2",
        "email": "annotator_dev_2@ttt.local",
        "password": "annotator123",
        "real_name": "开发标注员2",
        "is_verified": True,
        "training_scope": "none",
    },
    {
        "role_code": "annotator",
        "role_name": "标注员",
        "username": "annotator_dev_3",
        "email": "annotator_dev_3@ttt.local",
        "password": "annotator123",
        "real_name": "开发标注员3",
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


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuthRepository(db)

    def login(self, login_name: str, password: str) -> UserSessionOut:
        self.bootstrap_default_users_if_needed()
        user = self.repository.get_user_by_login(login_name)
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

        return UserSessionOut(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.code,
            real_name=user.real_name,
            is_verified=user.is_verified,
            training_scope=user.training_scope,
        )

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
