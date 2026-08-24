from pydantic import BaseModel

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user: UserRead
