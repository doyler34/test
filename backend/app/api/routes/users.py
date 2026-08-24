import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import AdminUser, DbSession
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import audit

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(_: AdminUser, session: DbSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate, admin: AdminUser, session: DbSession, request: Request
) -> User:
    existing = await session.execute(
        select(User.id).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    )
    if existing.first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email already in use")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await audit.log_action(
        session,
        actor_user_id=admin.id,
        action="user_created",
        target_type="user",
        target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    admin: AdminUser,
    session: DbSession,
    request: Request,
) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    changes = payload.model_dump(exclude_unset=True, exclude={"password"})
    for field, value in changes.items():
        setattr(user, field, value)
    if payload.password:
        user.password_hash = hash_password(payload.password)

    await session.commit()
    await session.refresh(user)
    await audit.log_action(
        session,
        actor_user_id=admin.id,
        action="user_updated",
        target_type="user",
        target_id=str(user.id),
        details={k: str(v) for k, v in changes.items()},
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID, admin: AdminUser, session: DbSession, request: Request
) -> None:
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete your own account")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await session.delete(user)
    await session.commit()
    await audit.log_action(
        session,
        actor_user_id=admin.id,
        action="user_deleted",
        target_type="user",
        target_id=str(user_id),
        ip_address=request.client.host if request.client else None,
    )
