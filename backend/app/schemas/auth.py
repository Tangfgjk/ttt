from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, description="用户名或邮箱")
    password: str = Field(min_length=1, description="登录密码")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20, description="注册用户名")
    password: str = Field(min_length=6, max_length=64, description="登录密码")
    confirm_password: str = Field(min_length=6, max_length=64, description="确认密码")


class ForgotPasswordRequest(BaseModel):
    username: str = Field(min_length=1, description="用户名")


class UserSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    role: str
    real_name: str | None = None
    is_verified: bool
    training_scope: str
    must_change_password: bool = False


class LoginResponse(BaseModel):
    message: str
    user: UserSessionOut
