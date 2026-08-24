import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import decode_jwt
from app.db.session import get_db
from app.models.user import User, UserRole
from app.providers.cache.db import DbCacheProvider
from app.providers.download.base import DownloadProvider
from app.providers.storage.local import LocalStorageProvider
from app.providers.stream.local import LocalStreamProvider
from app.services import auth_service
from app.services.cache_manager import CacheManager
from app.services.job_service import JobService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_provider(request: Request) -> DownloadProvider:
    return request.app.state.provider


def get_storage(request: Request) -> LocalStorageProvider:
    return request.app.state.storage


def get_stream(request: Request) -> LocalStreamProvider:
    return request.app.state.stream


async def get_current_user(request: Request, session: DbSession) -> User:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        raw_key = auth_header[7:].strip()
        user = await auth_service.get_user_by_api_key(session, raw_key)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked API key")
        return user

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_jwt(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

    user_id = uuid.UUID(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def get_job_service(
    session: DbSession,
    provider: Annotated[DownloadProvider, Depends(get_provider)],
    storage: Annotated[LocalStorageProvider, Depends(get_storage)],
) -> JobService:
    return JobService(session, provider, storage)


def get_cache_manager(
    session: DbSession,
    storage: Annotated[LocalStorageProvider, Depends(get_storage)],
    stream: Annotated[LocalStreamProvider, Depends(get_stream)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> CacheManager:
    return CacheManager(session, DbCacheProvider(session), storage, stream, settings)
