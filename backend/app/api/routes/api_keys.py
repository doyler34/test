import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead
from app.services import audit, auth_service

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyRead])
async def list_api_keys(user: CurrentUser, session: DbSession) -> list[ApiKey]:
    result = await session.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate, user: CurrentUser, session: DbSession, request: Request
) -> ApiKeyCreated:
    api_key, raw_key = await auth_service.create_api_key(session, user, payload.name)
    await audit.log_action(
        session,
        actor_user_id=user.id,
        action="api_key_created",
        target_type="api_key",
        target_id=str(api_key.id),
        ip_address=request.client.host if request.client else None,
    )
    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        key=raw_key,
    )


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: uuid.UUID, user: CurrentUser, session: DbSession, request: Request
) -> None:
    revoked = await auth_service.revoke_api_key(session, user, api_key_id)
    if not revoked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    await audit.log_action(
        session,
        actor_user_id=user.id,
        action="api_key_revoked",
        target_type="api_key",
        target_id=str(api_key_id),
        ip_address=request.client.host if request.client else None,
    )
