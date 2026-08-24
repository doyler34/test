import uuid
from datetime import timedelta

from sqlalchemy import delete, select, update

from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import AsyncSessionLocal
from app.models.cache_entry import CacheEntry, CacheEntryStatus
from app.models.job import Job, JobStatus
from app.models.job_file import JobFile
from app.models.user import User, UserRole
from app.providers.cache.db import DbCacheProvider
from app.services.cache_manager import CacheManager

CHUNK = b"x" * 1000  # 1000 bytes per file, real bytes on real disk


async def _make_cached_file(
    app_instance, user_id: uuid.UUID, *, days_old: int, protected: bool = False
):
    storage = app_instance.state.storage
    async with AsyncSessionLocal() as session:
        job = Job(
            user_id=user_id,
            source="magnet:?xt=urn:btih:evicttest00000000000000000000000000000",
            status=JobStatus.COMPLETED,
            save_path=f"evict-test-{uuid.uuid4().hex[:8]}",
        )
        session.add(job)
        await session.flush()
        file_dir = storage.root / job.save_path
        file_dir.mkdir(parents=True, exist_ok=True)
        (file_dir / "data.bin").write_bytes(CHUNK)
        session.add(JobFile(job_id=job.id, relative_path="data.bin", size_bytes=len(CHUNK)))
        await session.commit()
        await session.refresh(job, attribute_names=["files"])

        manager = CacheManager(
            session, DbCacheProvider(session), storage, app_instance.state.stream,
            app_instance.state.settings,
        )
        entries = await manager.register_completed_job(job)
        entry_id = entries[0].id

        await session.execute(
            update(CacheEntry)
            .where(CacheEntry.id == entry_id)
            .values(last_accessed_at=utcnow() - timedelta(days=days_old), protected=protected)
        )
        await session.commit()
        return job.id, entry_id, file_dir / "data.bin"


async def test_eviction_removes_oldest_first_and_spares_protected(app_instance) -> None:
    settings = app_instance.state.settings
    user_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        user = User(
            username=f"evict-{user_id.hex[:8]}",
            email=f"evict-{user_id.hex[:8]}@example.com",
            password_hash=hash_password("test-password-123"),
            role=UserRole.USER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    oldest_job, oldest_entry, oldest_path = await _make_cached_file(
        app_instance, user_id, days_old=60
    )
    protected_job, protected_entry, protected_path = await _make_cached_file(
        app_instance, user_id, days_old=90, protected=True
    )
    newest_job, newest_entry, newest_path = await _make_cached_file(
        app_instance, user_id, days_old=1
    )

    assert oldest_path.exists() and protected_path.exists() and newest_path.exists()

    # Force eviction: with max=2000 bytes and threshold=0.5, target=1000 bytes.
    # Used = 3000 (three 1000-byte files). Protected entry must never be
    # touched; between the other two, the 60-day-old one goes first.
    original_max_gb = settings.max_storage_gb
    original_threshold = settings.cache_eviction_threshold
    original_retention = settings.cache_retention_days
    settings.max_storage_gb = 2000 / (1024**3)
    settings.cache_eviction_threshold = 0.5
    settings.cache_retention_days = 30
    try:
        async with AsyncSessionLocal() as session:
            manager = CacheManager(
                session, DbCacheProvider(session), app_instance.state.storage,
                app_instance.state.stream, settings,
            )
            evicted = await manager.run_eviction()
    finally:
        settings.max_storage_gb = original_max_gb
        settings.cache_eviction_threshold = original_threshold
        settings.cache_retention_days = original_retention

    assert oldest_entry in evicted
    assert protected_entry not in evicted
    assert not oldest_path.exists(), "evicted file must be removed from disk"
    assert protected_path.exists(), "protected file must survive eviction"

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CacheEntry.status).where(CacheEntry.id == oldest_entry)
        )
        assert result.scalar_one() == CacheEntryStatus.EVICTED

        for job_id in (oldest_job, protected_job, newest_job):
            await session.execute(delete(JobFile).where(JobFile.job_id == job_id))
        for job_id in (oldest_job, protected_job, newest_job):
            job_row = await session.get(Job, job_id)
            if job_row:
                await session.delete(job_row)
        await session.delete(user)
        await session.commit()

    if newest_path.exists():
        newest_path.unlink()
    if protected_path.exists():
        protected_path.unlink()
