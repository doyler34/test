import uuid

from httpx import ASGITransport, AsyncClient


async def test_create_and_list_api_key(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.post("/api/api-keys", json={"name": "my key"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"]
    assert body["prefix"]
    assert body["key"].startswith(body["prefix"])

    list_resp = await user_client.get("/api/api-keys")
    assert list_resp.status_code == 200
    assert any(k["id"] == body["id"] for k in list_resp.json())
    assert all("key" not in k for k in list_resp.json())  # raw key never listed again


async def test_api_key_authenticates_requests(
    app_instance, new_user: tuple[AsyncClient, dict]
) -> None:
    user_client, _ = new_user
    create_resp = await user_client.post("/api/api-keys", json={"name": "automation"})
    raw_key = create_resp.json()["key"]

    anon_client = AsyncClient(transport=ASGITransport(app=app_instance), base_url="http://test")
    try:
        resp = await anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
        assert resp.status_code == 200
    finally:
        await anon_client.aclose()


async def test_revoked_api_key_no_longer_authenticates(
    app_instance, new_user: tuple[AsyncClient, dict]
) -> None:
    user_client, _ = new_user
    create_resp = await user_client.post("/api/api-keys", json={"name": "temp"})
    key_id = create_resp.json()["id"]
    raw_key = create_resp.json()["key"]

    revoke_resp = await user_client.delete(f"/api/api-keys/{key_id}")
    assert revoke_resp.status_code == 204

    anon_client = AsyncClient(transport=ASGITransport(app=app_instance), base_url="http://test")
    try:
        resp = await anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
        assert resp.status_code == 401
    finally:
        await anon_client.aclose()


async def test_revoking_nonexistent_key_returns_404(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.delete(f"/api/api-keys/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_cannot_revoke_another_users_api_key(
    new_user: tuple[AsyncClient, dict], admin_client: AsyncClient
) -> None:
    user_client, _ = new_user
    create_resp = await user_client.post("/api/api-keys", json={"name": "victim key"})
    key_id = create_resp.json()["id"]

    resp = await admin_client.delete(f"/api/api-keys/{key_id}")
    assert resp.status_code == 404  # admin has no special access to others' API keys
