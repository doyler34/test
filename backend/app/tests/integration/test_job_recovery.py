import uuid

from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.models.job import Job, JobStatus
from app.services.job_service import JobService


async def test_reconcile_recovers_still_active_job(
    app_instance, new_user: tuple[AsyncClient, dict], unique_magnet: str
) -> None:
    user_client, user = new_user
    create_resp = await user_client.post("/api/jobs", json={"source": unique_magnet})
    job_id = uuid.UUID(create_resp.json()["id"])

    # Simulate what happens on a fresh API process boot: a brand-new
    # JobService (backed by the same provider/storage the running app uses)
    # reconciling DB state against whatever qBittorrent is still doing.
    async with AsyncSessionLocal() as session:
        job_service = JobService(session, app_instance.state.provider, app_instance.state.storage)
        recovered = await job_service.reconcile_on_startup()
        recovered_ids = {j.id for j in recovered}
        assert job_id in recovered_ids

        refetched = await job_service.get_job(job_id)
        assert refetched.status in (JobStatus.QUEUED, JobStatus.DOWNLOADING)

    await user_client.delete(f"/api/jobs/{job_id}")


async def test_reconcile_marks_orphaned_job_failed(
    app_instance, new_user: tuple[AsyncClient, dict]
) -> None:
    _, user = new_user
    # 40 hex chars that certainly aren't a real torrent hash in qBittorrent.
    fake_hash = uuid.uuid4().hex + uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        orphan = Job(
            user_id=uuid.UUID(user["id"]),
            source=f"magnet:?xt=urn:btih:{fake_hash}",
            external_id=fake_hash,
            status=JobStatus.DOWNLOADING,
            save_path="orphan-recovery-test",
        )
        session.add(orphan)
        await session.commit()
        await session.refresh(orphan)
        orphan_id = orphan.id

    async with AsyncSessionLocal() as session:
        job_service = JobService(session, app_instance.state.provider, app_instance.state.storage)
        await job_service.reconcile_on_startup()

        refetched = await job_service.get_job(orphan_id)
        assert refetched.status == JobStatus.FAILED
        assert refetched.error_message

        await session.delete(refetched)
        await session.commit()


async def test_reconcile_marks_job_without_external_id_failed(
    app_instance, new_user: tuple[AsyncClient, dict]
) -> None:
    _, user = new_user

    async with AsyncSessionLocal() as session:
        broken = Job(
            user_id=uuid.UUID(user["id"]),
            source="magnet:?xt=urn:btih:neverassigned",
            external_id=None,
            status=JobStatus.QUEUED,
        )
        session.add(broken)
        await session.commit()
        await session.refresh(broken)
        broken_id = broken.id

    async with AsyncSessionLocal() as session:
        job_service = JobService(session, app_instance.state.provider, app_instance.state.storage)
        await job_service.reconcile_on_startup()

        refetched = await job_service.get_job(broken_id)
        assert refetched.status == JobStatus.FAILED

        await session.delete(refetched)
        await session.commit()
