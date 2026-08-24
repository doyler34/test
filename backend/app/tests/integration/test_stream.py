import json
import uuid

from httpx import AsyncClient

from app.api.routes.stream import jobs_event_stream, system_event_stream


class _FakeRequest:
    """Stands in for the real Starlette Request in the two SSE generator
    functions, which only ever call `await request.is_disconnected()`.
    Reports "connected" for `disconnect_after` iterations, then
    "disconnected", so the otherwise-infinite generator terminates
    naturally — testing the real generator logic without going through an
    ASGI transport, which buffers full responses and deadlocks against an
    intentionally unbounded stream (see stream.py's docstring)."""

    def __init__(self, disconnect_after: int) -> None:
        self._remaining = disconnect_after

    async def is_disconnected(self) -> bool:
        if self._remaining <= 0:
            return True
        self._remaining -= 1
        return False


async def test_jobs_stream_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/stream/jobs")
    assert resp.status_code == 401


async def test_system_stream_requires_admin(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get("/api/stream/system")
    assert resp.status_code == 403


async def test_jobs_event_stream_emits_valid_json(
    app_instance, new_user: tuple[AsyncClient, dict], unique_magnet: str
) -> None:
    user_client, user = new_user
    create_resp = await user_client.post("/api/jobs", json={"source": unique_magnet})
    job_id = create_resp.json()["id"]

    request = _FakeRequest(disconnect_after=1)
    events = [
        event
        async for event in jobs_event_stream(
            request,
            owner_id=uuid.UUID(user["id"]),
            provider=app_instance.state.provider,
            storage=app_instance.state.storage,
            interval=0.01,
        )
    ]
    assert len(events) == 1
    assert events[0].startswith("data: ")
    payload = json.loads(events[0][len("data: ") :])
    assert any(j["id"] == job_id for j in payload)

    await user_client.delete(f"/api/jobs/{job_id}")


async def test_system_event_stream_emits_valid_metrics(app_instance) -> None:
    request = _FakeRequest(disconnect_after=1)
    events = [
        event
        async for event in system_event_stream(
            request, app_state=app_instance.state, interval=0.01
        )
    ]
    assert len(events) == 1
    payload = json.loads(events[0][len("data: ") :])
    assert "cpu_percent" in payload
    assert "active_downloads" in payload
