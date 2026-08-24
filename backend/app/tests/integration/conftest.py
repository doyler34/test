import shutil
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from alembic import command
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.main import create_app

BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _run_migrations() -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def _prepare_test_environment() -> None:
    settings = get_settings()
    storage_root = Path(settings.storage_root)
    if storage_root.exists():
        shutil.rmtree(storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    _run_migrations()


@pytest.fixture(scope="session")
async def app_instance(_prepare_test_environment: None) -> AsyncIterator:
    app = create_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture(scope="session")
async def client(app_instance) -> AsyncIterator[AsyncClient]:
    """The one true anonymous client: never logs in except inside a test that
    is itself exercising login/logout. Every other fixture below gets its own
    independent AsyncClient (same ASGI transport/app, separate cookie jar) so
    logging in as one identity never leaks into another fixture's client."""
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _new_isolated_client(app_instance) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app_instance), base_url="http://test")


@pytest.fixture
async def admin_client(app_instance) -> AsyncIterator[AsyncClient]:
    settings = get_settings()
    admin = _new_isolated_client(app_instance)
    # The suite runs many logins in quick succession against the real 5/minute
    # limiter (exercised end-to-end in test_auth.py::test_login_is_rate_limited).
    # Reset before each fixture-driven login so unrelated tests aren't starved
    # by that one; production traffic obviously gets no such reset.
    limiter.reset()
    resp = await admin.post(
        "/api/auth/login",
        json={"username": settings.first_admin_username, "password": settings.first_admin_password},
    )
    assert resp.status_code == 200, resp.text
    yield admin
    await admin.aclose()


async def _create_and_login_user(
    app_instance, admin_client: AsyncClient, *, role: str = "user"
) -> tuple[AsyncClient, dict]:
    suffix = uuid.uuid4().hex[:10]
    username = f"testuser-{suffix}"
    password = "test-password-123"
    resp = await admin_client.post(
        "/api/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()

    user_client = _new_isolated_client(app_instance)
    limiter.reset()
    login_resp = await user_client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert login_resp.status_code == 200, login_resp.text
    return user_client, user


@pytest.fixture
async def new_user(
    app_instance, admin_client: AsyncClient
) -> AsyncIterator[tuple[AsyncClient, dict]]:
    user_client, user = await _create_and_login_user(app_instance, admin_client)
    yield user_client, user
    await user_client.aclose()
    await admin_client.delete(f"/api/users/{user['id']}")


@pytest.fixture
async def second_user(
    app_instance, admin_client: AsyncClient
) -> AsyncIterator[tuple[AsyncClient, dict]]:
    """A second, independent user — distinct from `new_user` — for tests that
    need to prove two different accounts can't see each other's resources.
    (A test that depends on both `new_user` and `second_user` gets two
    genuinely different users; depending on `new_user` twice would not, since
    pytest caches a function-scoped fixture per test.)"""
    user_client, user = await _create_and_login_user(app_instance, admin_client)
    yield user_client, user
    await user_client.aclose()
    await admin_client.delete(f"/api/users/{user['id']}")


@pytest.fixture
def unique_magnet() -> str:
    """A syntactically valid, guaranteed-unique magnet link. qBittorrent
    dedupes by info-hash, so tests must never reuse one — real download
    completion isn't reachable from this sandbox anyway (no peer traffic),
    so a fabricated-but-valid 40-hex-char hash exercises the exact same
    add/list/pause/resume/cancel code paths as a real magnet would."""
    hash_hex = (uuid.uuid4().hex + uuid.uuid4().hex)[:40]
    return f"magnet:?xt=urn:btih:{hash_hex}&dn=test-job"
