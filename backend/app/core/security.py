import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import get_settings

TokenType = Literal["access", "refresh"]

# bcrypt's own hard limit; longer inputs raise instead of silently truncating.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except ValueError:
        return False


def create_jwt(
    *, subject: uuid.UUID, token_type: TokenType, expires_delta: timedelta
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    return create_jwt(
        subject=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def new_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, sha256_hash, expires_at). Only the hash is persisted."""
    settings = get_settings()
    raw = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return raw, hash_token(raw), expires_at


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, prefix_for_display, sha256_hash). Only prefix+hash are persisted."""
    raw = secrets.token_urlsafe(32)
    prefix = raw[:10]
    return raw, prefix, hash_token(raw)
