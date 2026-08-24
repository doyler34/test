import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.base import utcnow
from app.models.cache_entry import CacheEntry, CacheEntryStatus
from app.models.job import Job
from app.providers.cache.base import CacheEntryView, CacheProvider, select_eviction_candidates
from app.providers.storage.base import StorageProvider
from app.providers.stream.base import StreamProvider


class CacheManagerError(Exception):
    pass


class CacheManager:
    def __init__(
        self,
        session: AsyncSession,
        cache_provider: CacheProvider,
        storage: StorageProvider,
        stream: StreamProvider,
        settings: Settings,
    ) -> None:
        self._session = session
        self._cache_provider = cache_provider
        self._storage = storage
        self._stream = stream
        self._settings = settings

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def register_completed_job(self, job: Job) -> list[CacheEntry]:
        """Create a cache entry for each file a completed job produced.
        Idempotent: existing paths are left untouched."""
        created: list[CacheEntry] = []
        for job_file in job.files:
            relative_path = f"{job.save_path}/{job_file.relative_path}"
            existing = await self._session.execute(
                select(CacheEntry.id).where(CacheEntry.path == relative_path)
            )
            if existing.first() is not None:
                continue
            entry = CacheEntry(
                job_id=job.id,
                owner_user_id=job.user_id,
                path=relative_path,
                size_bytes=job_file.size_bytes,
                status=CacheEntryStatus.ACTIVE,
            )
            self._session.add(entry)
            created.append(entry)
        if created:
            await self._session.commit()
        return created

    async def get(self, entry_id: uuid.UUID) -> CacheEntry | None:
        result = await self._session.execute(select(CacheEntry).where(CacheEntry.id == entry_id))
        return result.scalar_one_or_none()

    async def list_entries(
        self, *, status: CacheEntryStatus = CacheEntryStatus.ACTIVE
    ) -> list[CacheEntry]:
        result = await self._session.execute(
            select(CacheEntry)
            .where(CacheEntry.status == status)
            .order_by(CacheEntry.created_at.desc())
        )
        return list(result.scalars().all())

    async def record_access(self, entry: CacheEntry) -> None:
        await self._cache_provider.touch(entry.id)

    async def set_protected(self, entry: CacheEntry, protected: bool) -> CacheEntry:
        entry.protected = protected
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def delete_entry(self, entry: CacheEntry) -> None:
        if self._stream.is_active(entry.path):
            raise CacheManagerError("File is currently being streamed")
        await self._storage.delete(entry.path)
        entry.status = CacheEntryStatus.EVICTED
        await self._session.commit()

    async def summary(self) -> tuple[int, int, int, int]:
        """Returns (total_bytes, used_bytes, free_bytes, active_entry_count)."""
        stats = await self._storage.usage()
        entries = await self._cache_provider.list_active()
        return stats.total_bytes, stats.used_bytes, stats.free_bytes, len(entries)

    async def run_eviction(self, *, now: datetime | None = None) -> list[uuid.UUID]:
        """The evictable-when-full policy, run periodically. Returns the ids
        it evicted (empty if usage is already under the target threshold)."""
        entries: list[CacheEntryView] = await self._cache_provider.list_active()
        used_bytes = await self._cache_provider.used_bytes()

        to_evict = select_eviction_candidates(
            entries,
            used_bytes=used_bytes,
            max_bytes=self._settings.max_storage_bytes,
            threshold=self._settings.cache_eviction_threshold,
            retention_days=self._settings.cache_retention_days,
            now=now or utcnow(),
            is_streaming=self._stream.is_active,
        )
        if not to_evict:
            return []

        path_by_id = {e.id: e.path for e in entries}
        evicted: list[uuid.UUID] = []
        for entry_id in to_evict:
            path = path_by_id[entry_id]
            try:
                await self._storage.delete(path)
            except Exception:
                continue
            evicted.append(entry_id)

        await self._cache_provider.mark_evicted(evicted)
        return evicted
