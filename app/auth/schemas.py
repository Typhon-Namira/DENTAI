from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    clinic_slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    identifier: str = Field(min_length=2, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: str
    clinic_id: str
    username: str
    email: EmailStr
    role: str
    branch_scope: list[str]
