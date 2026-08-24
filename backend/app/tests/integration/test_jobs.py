import asyncio
import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
async def job(new_user: tuple[AsyncClient, dict], unique_magnet: str):
    user_client, _ = new_user
    resp = await user_client.post("/api/jobs", json={"source": unique_magnet})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    yield user_client, body
    await user_client.delete(f"/api/jobs/{body['id']}")


async def test_create_job_against_real_qbittorrent(job, unique_magnet: str) -> None:
    _, body = job
    assert body["status"] == "queued"
    assert body["source"] == unique_magnet
    assert body["progress"] == 0.0


async def test_get_job(job) -> None:
    user_client, body = job
    resp = await user_client.get(f"/api/jobs/{body['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == body["id"]


async def test_job_reaches_downloading_via_poller(job) -> None:
    user_client, body = job
    resp = None
    for _ in range(10):
        resp = await user_client.get(f"/api/jobs/{body['id']}")
        if resp.json()["status"] == "downloading":
            break
        await asyncio.sleep(1)
    assert resp.json()["status"] == "downloading"
    assert resp.json()["started_at"] is not None


async def test_list_jobs_only_shows_own_jobs(
    job, second_user: tuple[AsyncClient, dict]
) -> None:
    other_client, _ = second_user
    resp = await other_client.get("/api/jobs")
    assert resp.status_code == 200
    _, job_body = job
    assert all(j["id"] != job_body["id"] for j in resp.json())


async def test_cannot_get_another_users_job(job, second_user: tuple[AsyncClient, dict]) -> None:
    other_client, _ = second_user
    _, job_body = job
    resp = await other_client.get(f"/api/jobs/{job_body['id']}")
    assert resp.status_code == 404


async def test_admin_can_see_all_jobs(job, admin_client: AsyncClient) -> None:
    _, job_body = job
    resp = await admin_client.get(f"/api/jobs/{job_body['id']}")
    assert resp.status_code == 200


async def test_pause_and_resume_job(job) -> None:
    user_client, body = job
    resp = None
    for _ in range(10):
        resp = await user_client.get(f"/api/jobs/{body['id']}")
        if resp.json()["status"] == "downloading":
            break
        await asyncio.sleep(1)

    pause_resp = await user_client.post(f"/api/jobs/{body['id']}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    resume_resp = await user_client.post(f"/api/jobs/{body['id']}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "downloading"


async def test_pause_already_paused_job_conflicts(job) -> None:
    user_client, body = job
    for _ in range(10):
        resp = await user_client.get(f"/api/jobs/{body['id']}")
        if resp.json()["status"] == "downloading":
            break
        await asyncio.sleep(1)

    await user_client.post(f"/api/jobs/{body['id']}/pause")
    second_pause = await user_client.post(f"/api/jobs/{body['id']}/pause")
    assert second_pause.status_code == 409


async def test_delete_job_removes_it(
    new_user: tuple[AsyncClient, dict], unique_magnet: str
) -> None:
    user_client, _ = new_user
    create_resp = await user_client.post("/api/jobs", json={"source": unique_magnet})
    job_id = create_resp.json()["id"]

    delete_resp = await user_client.delete(f"/api/jobs/{job_id}")
    assert delete_resp.status_code == 204

    get_resp = await user_client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 404


async def test_create_job_requires_authentication(client: AsyncClient, unique_magnet: str) -> None:
    resp = await client.post("/api/jobs", json={"source": unique_magnet})
    assert resp.status_code == 401


async def test_pausing_nonexistent_job_returns_404(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.post(f"/api/jobs/{uuid.uuid4()}/pause")
    assert resp.status_code == 404
