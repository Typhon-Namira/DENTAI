from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    clinic_slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    identifier: str = Field(min_length=2, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def passwords_must_differ(self):
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password.")
        return self


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
    subscription_plan: str | None
    subscription_starts_at: datetime | None
    subscription_expires_at: datetime | None
    subscription_days_remaining: int | None
