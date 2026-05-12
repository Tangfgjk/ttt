from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, description="用户名或邮箱")
    password: str = Field(min_length=1, description="登录密码")


class UserSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    real_name: str | None = None
    is_verified: bool
    training_scope: str


class LoginResponse(BaseModel):
    message: str
    user: UserSessionOut
