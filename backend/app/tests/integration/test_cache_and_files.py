import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.db.session import AsyncSessionLocal
from app.models.job import Job, JobStatus
from app.models.job_file import JobFile
from app.providers.cache.db import DbCacheProvider
from app.services.cache_manager import CacheManager

FILE_CONTENT = b"0123456789" * 100  # 1000 bytes, real bytes on real disk


@pytest.fixture
async def cached_file(app_instance, new_user: tuple[AsyncClient, dict]):
    """Builds a real completed job + real file on disk + a real cache_entries
    row via CacheManager.register_completed_job — the same code path the
    poller uses on real completion, just without waiting on an actual
    BitTorrent transfer (peer connections aren't reachable from this sandbox)."""
    user_client, user = new_user
    storage = app_instance.state.storage

    async with AsyncSessionLocal() as session:
        job = Job(
            user_id=uuid.UUID(user["id"]),
            source="magnet:?xt=urn:btih:fixturejob0000000000000000000000000000",
            external_id=None,
            status=JobStatus.COMPLETED,
            save_path=f"cache-test-{uuid.uuid4().hex[:8]}",
        )
        session.add(job)
        await session.flush()

        file_dir = storage.root / job.save_path
        file_dir.mkdir(parents=True, exist_ok=True)
        (file_dir / "video.mp4").write_bytes(FILE_CONTENT)

        session.add(
            JobFile(job_id=job.id, relative_path="video.mp4", size_bytes=len(FILE_CONTENT))
        )
        await session.commit()
        await session.refresh(job, attribute_names=["files"])

        manager = CacheManager(
            session, DbCacheProvider(session), storage, app_instance.state.stream,
            app_instance.state.settings,
        )
        entries = await manager.register_completed_job(job)
        assert len(entries) == 1
        entry_id = entries[0].id

    yield user_client, str(entry_id), user

    async with AsyncSessionLocal() as session:
        await session.execute(delete(JobFile).where(JobFile.job_id == job.id))
        await session.delete(await session.get(Job, job.id))
        await session.commit()


async def test_download_full_file(cached_file) -> None:
    user_client, entry_id, _ = cached_file
    resp = await user_client.get(f"/api/files/{entry_id}")
    assert resp.status_code == 200
    assert resp.content == FILE_CONTENT
    assert resp.headers["accept-ranges"] == "bytes"


async def test_download_with_range_header(cached_file) -> None:
    user_client, entry_id, _ = cached_file
    resp = await user_client.get(f"/api/files/{entry_id}", headers={"Range": "bytes=0-99"})
    assert resp.status_code == 206
    assert resp.content == FILE_CONTENT[0:100]
    assert resp.headers["content-range"] == f"bytes 0-99/{len(FILE_CONTENT)}"


async def test_download_suffix_range(cached_file) -> None:
    user_client, entry_id, _ = cached_file
    resp = await user_client.get(f"/api/files/{entry_id}", headers={"Range": "bytes=-100"})
    assert resp.status_code == 206
    assert resp.content == FILE_CONTENT[-100:]


async def test_other_user_cannot_download_file(
    cached_file, second_user: tuple[AsyncClient, dict]
) -> None:
    _, entry_id, _ = cached_file
    other_client, _ = second_user
    resp = await other_client.get(f"/api/files/{entry_id}")
    assert resp.status_code == 404


async def test_download_unauthenticated_rejected(cached_file, client: AsyncClient) -> None:
    _, entry_id, _ = cached_file
    resp = await client.get(f"/api/files/{entry_id}")
    assert resp.status_code == 401


async def test_download_nonexistent_entry_404(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get(f"/api/files/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_admin_cache_list_and_summary(cached_file, admin_client: AsyncClient) -> None:
    _, entry_id, _ = cached_file
    list_resp = await admin_client.get("/api/cache")
    assert list_resp.status_code == 200
    assert any(e["id"] == entry_id for e in list_resp.json())

    summary_resp = await admin_client.get("/api/cache/summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["entry_count"] >= 1


async def test_non_admin_cannot_list_cache(new_user: tuple[AsyncClient, dict]) -> None:
    user_client, _ = new_user
    resp = await user_client.get("/api/cache")
    assert resp.status_code == 403


async def test_protect_cache_entry(cached_file, admin_client: AsyncClient) -> None:
    _, entry_id, _ = cached_file
    resp = await admin_client.patch(f"/api/cache/{entry_id}", json={"protected": True})
    assert resp.status_code == 200
    assert resp.json()["protected"] is True


async def test_delete_cache_entry_removes_file_from_disk(
    app_instance, cached_file, admin_client: AsyncClient
) -> None:
    user_client, entry_id, _ = cached_file
    resp = await admin_client.delete(f"/api/cache/{entry_id}")
    assert resp.status_code == 204

    get_resp = await admin_client.get(f"/api/cache/{entry_id}")
    assert get_resp.json()["status"] == "evicted"

    # file is gone; serving it must now 404, never reveal a stale path
    download_resp = await user_client.get(f"/api/files/{entry_id}")
    assert download_resp.status_code == 404
