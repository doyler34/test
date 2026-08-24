from httpx import AsyncClient

from app.core.config import get_settings
from app.core.rate_limit import limiter


async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_login_with_bootstrap_admin(client: AsyncClient) -> None:
    settings = get_settings()
    limiter.reset()
    resp = await client.post(
        "/api/auth/login",
        json={"username": settings.first_admin_username, "password": settings.first_admin_password},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["username"] == settings.first_admin_username
    assert body["user"]["role"] == "admin"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    await client.post("/api/auth/logout")


async def test_login_with_wrong_password_is_rejected(client: AsyncClient) -> None:
    settings = get_settings()
    limiter.reset()
    resp = await client.post(
        "/api/auth/login",
        json={"username": settings.first_admin_username, "password": "definitely-wrong"},
    )
    assert resp.status_code == 401


async def test_me_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_refresh_issues_new_access_token(admin_client: AsyncClient) -> None:
    resp = await admin_client.post("/api/auth/refresh")
    assert resp.status_code == 200


async def test_logout_revokes_session(client: AsyncClient) -> None:
    settings = get_settings()
    limiter.reset()
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": settings.first_admin_username, "password": settings.first_admin_password},
    )
    assert login_resp.status_code == 200

    logout_resp = await client.post("/api/auth/logout")
    assert logout_resp.status_code == 204

    refresh_resp = await client.post("/api/auth/refresh")
    assert refresh_resp.status_code == 401


async def test_login_is_rate_limited(client: AsyncClient) -> None:
    """Exercises the real slowapi limiter end-to-end (not mocked): the
    configured login_rate_limit is 5/minute, so the 6th rapid attempt in a
    clean window must be rejected with 429."""
    limiter.reset()
    settings = get_settings()
    assert settings.login_rate_limit == "5/minute"

    last_status = None
    for _ in range(6):
        resp = await client.post(
            "/api/auth/login",
            json={"username": "no-such-user", "password": "wrong"},
        )
        last_status = resp.status_code

    assert last_status == 429
    limiter.reset()  # leave a clean slate for tests that run after this one
