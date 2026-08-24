import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    hash_token,
    new_api_key,
    new_refresh_token,
    verify_password,
)
from app.db.base import utcnow
from app.models.api_key import ApiKey
from app.models.session import Session as SessionModel
from app.models.user import User


class AuthError(Exception):
    """Raised for invalid credentials or an unusable account."""


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid username or password")
    if not user.is_active:
        raise AuthError("Account is disabled")
    user.last_login_at = utcnow()
    await session.commit()
    await session.refresh(user)
    return user


async def create_session(
    session: AsyncSession, user: User, *, user_agent: str | None, ip_address: str | None
) -> str:
    raw_token, token_hash, expires_at = new_refresh_token()
    session.add(
        SessionModel(
            user_id=user.id,
            refresh_token_hash=token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )
    )
    await session.commit()
    return raw_token


async def get_user_by_refresh_token(session: AsyncSession, raw_token: str) -> User | None:
    token_hash = hash_token(raw_token)
    result = await session.execute(
        select(SessionModel).where(SessionModel.refresh_token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record is None or record.revoked_at is not None:
        return None
    if record.expires_at < datetime.now(UTC):
        return None
    user_result = await session.execute(select(User).where(User.id == record.user_id))
    return user_result.scalar_one_or_none()


async def revoke_session(session: AsyncSession, raw_token: str) -> None:
    token_hash = hash_token(raw_token)
    result = await session.execute(
        select(SessionModel).where(SessionModel.refresh_token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record is not None and record.revoked_at is None:
        record.revoked_at = utcnow()
        await session.commit()


async def revoke_all_sessions(session: AsyncSession, user_id: uuid.UUID) -> None:
    result = await session.execute(
        select(SessionModel).where(
            SessionModel.user_id == user_id, SessionModel.revoked_at.is_(None)
        )
    )
    now = utcnow()
    for record in result.scalars().all():
        record.revoked_at = now
    await session.commit()


async def create_api_key(session: AsyncSession, user: User, name: str) -> tuple[ApiKey, str]:
    raw_key, prefix, key_hash = new_api_key()
    api_key = ApiKey(user_id=user.id, name=name, prefix=prefix, key_hash=key_hash)
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key, raw_key


async def get_user_by_api_key(session: AsyncSession, raw_key: str) -> User | None:
    key_hash = hash_token(raw_key)
    result = await session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    record = result.scalar_one_or_none()
    if record is None or record.revoked_at is not None:
        return None
    record.last_used_at = utcnow()
    await session.commit()
    user_result = await session.execute(select(User).where(User.id == record.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


async def revoke_api_key(session: AsyncSession, user: User, api_key_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return False
    record.revoked_at = utcnow()
    await session.commit()
    return True


async def ensure_first_admin(
    session: AsyncSession, *, username: str, email: str, password: str
) -> None:
    """Bootstrap an admin account on first startup if the users table is empty."""
    from app.models.user import UserRole

    result = await session.execute(select(User.id).limit(1))
    if result.first() is not None:
        return
    session.add(
        User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
    )
    await session.commit()
