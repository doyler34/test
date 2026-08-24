import uuid

from httpx import AsyncClient


async def test_non_admin_cannot_list_users(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get("/api/users")
    assert resp.status_code == 403


async def test_admin_can_create_and_list_users(admin_client: AsyncClient) -> None:
    username = f"listtest-{uuid.uuid4().hex[:8]}"
    create_resp = await admin_client.post(
        "/api/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "test-password-123",
            "role": "user",
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    list_resp = await admin_client.get("/api/users")
    assert list_resp.status_code == 200
    assert any(u["id"] == user_id for u in list_resp.json())

    await admin_client.delete(f"/api/users/{user_id}")


async def test_duplicate_username_rejected(admin_client: AsyncClient) -> None:
    username = f"dup-{uuid.uuid4().hex[:8]}"
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "test-password-123",
        "role": "user",
    }
    first = await admin_client.post("/api/users", json=payload)
    assert first.status_code == 201
    second = await admin_client.post("/api/users", json=payload)
    assert second.status_code == 409
    await admin_client.delete(f"/api/users/{first.json()['id']}")


async def test_admin_can_disable_user(
    admin_client: AsyncClient, new_user: tuple[AsyncClient, dict]
) -> None:
    _, user = new_user
    resp = await admin_client.patch(f"/api/users/{user['id']}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_disabled_user_cannot_login(admin_client: AsyncClient, client: AsyncClient) -> None:
    username = f"disabled-{uuid.uuid4().hex[:8]}"
    password = "test-password-123"
    create_resp = await admin_client.post(
        "/api/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "role": "user",
        },
    )
    user_id = create_resp.json()["id"]
    await admin_client.patch(f"/api/users/{user_id}", json={"is_active": False})

    login_resp = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert login_resp.status_code == 401
    await admin_client.delete(f"/api/users/{user_id}")


async def test_admin_cannot_delete_self(admin_client: AsyncClient) -> None:
    me = await admin_client.get("/api/auth/me")
    resp = await admin_client.delete(f"/api/users/{me.json()['id']}")
    assert resp.status_code == 400


async def test_delete_nonexistent_user_returns_404(admin_client: AsyncClient) -> None:
    resp = await admin_client.delete(f"/api/users/{uuid.uuid4()}")
    assert resp.status_code == 404
