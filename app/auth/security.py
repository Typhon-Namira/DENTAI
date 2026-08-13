import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import AppError

password_hash = PasswordHash.recommended()
settings = get_settings()


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def make_access_token(user_id: uuid.UUID, clinic_id: uuid.UUID, token_version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "clinic": str(clinic_id),
        "ver": token_version,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.access_token_secret, algorithm="HS256")


def make_refresh_token(user_id: uuid.UUID, clinic_id: uuid.UUID, token_version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "clinic": str(clinic_id),
        "ver": token_version,
        "sid": secrets.token_urlsafe(18),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_days),
    }
    return jwt.encode(payload, settings.refresh_token_secret, algorithm="HS256")


def decode_token(token: str, kind: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.access_token_secret if kind == "access" else settings.refresh_token_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise AppError("INVALID_TOKEN", "Authentication token is invalid or expired.", 401) from exc
    if payload.get("type") != kind:
        raise AppError("INVALID_TOKEN", "Authentication token type is invalid.", 401)
    return payload
