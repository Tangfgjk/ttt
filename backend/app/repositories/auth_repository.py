from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.auth import Role, User


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_login(self, login_name: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(or_(User.username == login_name, User.email == login_name))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def count_users(self) -> int:
        stmt = select(func.count()).select_from(User)
        return self.db.scalar(stmt) or 0

    def get_role_by_code(self, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code).limit(1)
        return self.db.scalar(stmt)

    def save_role(self, role: Role) -> Role:
        self.db.add(role)
        self.db.flush()
        return role

    def save_user(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
