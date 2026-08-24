from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, DbSession, get_settings_dep
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserRead
from app.services import audit, auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str, settings: Settings
) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth",
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(get_settings().login_rate_limit)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> LoginResponse:
    try:
        user = await auth_service.authenticate_user(session, payload.username, payload.password)
    except auth_service.AuthError as exc:
        await audit.log_action(
            session,
            actor_user_id=None,
            action="login_failed",
            target_type="user",
            target_id=payload.username,
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    access_token = create_access_token(user.id)
    refresh_token = await auth_service.create_session(
        session,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    _set_auth_cookies(
        response, access_token=access_token, refresh_token=refresh_token, settings=settings
    )
    await audit.log_action(
        session,
        actor_user_id=user.id,
        action="login",
        target_type="user",
        target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    return LoginResponse(user=UserRead.model_validate(user))


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    request: Request,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> LoginResponse:
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    if not raw_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token")
    user = await auth_service.get_user_by_refresh_token(session, raw_refresh)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    access_token = create_access_token(user.id)
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return LoginResponse(user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, session: DbSession) -> None:
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    if raw_refresh:
        await auth_service.revoke_session(session, raw_refresh)
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
