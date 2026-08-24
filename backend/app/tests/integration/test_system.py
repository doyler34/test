from httpx import AsyncClient


async def test_system_status_requires_admin(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get("/api/system/status")
    assert resp.status_code == 403


async def test_system_status_reports_real_component_health(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/system/status")
    assert resp.status_code == 200
    body = resp.json()
    names = {c["name"] for c in body["components"]}
    assert names == {"database", "qbittorrent", "storage", "poller", "evictor"}
    # this is a live check against the real Postgres + real qBittorrent
    # instance the test session is running against, so these must be "ok"
    db_component = next(c for c in body["components"] if c["name"] == "database")
    qbt_component = next(c for c in body["components"] if c["name"] == "qbittorrent")
    assert db_component["status"] == "ok"
    assert qbt_component["status"] == "ok"
    assert body["status"] == "ok"


async def test_system_metrics_requires_admin(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get("/api/system/metrics")
    assert resp.status_code == 403


async def test_system_metrics_returns_real_values(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/system/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["memory_total_bytes"] > 0
    assert body["cpu_percent"] >= 0
    assert body["active_downloads"] >= 0
    assert body["uptime_seconds"] >= 0


async def test_events_requires_admin(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get("/api/system/events")
    assert resp.status_code == 403


async def test_events_lists_real_startup_event(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/system/events")
    assert resp.status_code == 200
    events = resp.json()
    # the app's own lifespan logs a startup-recovery event on boot
    assert any(e["component"] == "api" for e in events)


async def test_audit_logs_requires_admin(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get("/api/system/audit-logs")
    assert resp.status_code == 403


async def test_audit_logs_records_real_actions(
    admin_client: AsyncClient, new_user: tuple[AsyncClient, dict]
) -> None:
    _, user = new_user
    resp = await admin_client.get("/api/system/audit-logs")
    assert resp.status_code == 200
    logs = resp.json()
    assert any(
        entry["action"] == "user_created" and entry["target_id"] == user["id"] for entry in logs
    )
