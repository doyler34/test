from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.job import Job
from app.providers.cache.db import DbCacheProvider
from app.providers.download.base import DownloadProvider
from app.providers.storage.local import LocalStorageProvider
from app.providers.stream.base import StreamProvider
from app.services.cache_manager import CacheManager
from app.services.job_service import JobService
from app.workers.base import WorkerLoop


class PollerWorker(WorkerLoop):
    """Polls the download provider on an interval and reconciles job rows.
    This is the single source of truth for job progress; the SSE stream and
    the cache manager both react to what this loop writes to the DB."""

    name = "poller"

    def __init__(
        self,
        session_factory: async_sessionmaker,
        provider: DownloadProvider,
        storage: LocalStorageProvider,
        stream: StreamProvider,
        settings: Settings,
    ) -> None:
        super().__init__()
        self.interval_seconds = settings.poll_interval_seconds
        self._session_factory = session_factory
        self._provider = provider
        self._storage = storage
        self._stream = stream
        self._settings = settings

    async def run_once(self) -> None:
        statuses = await self._provider.list_all()
        if not statuses:
            return
        by_external_id = {s.external_id: s for s in statuses}

        async with self._session_factory() as session:
            job_service = JobService(session, self._provider, self._storage)
            cache_manager = CacheManager(
                session,
                DbCacheProvider(session),
                self._storage,
                self._stream,
                self._settings,
            )

            result = await session.execute(
                select(Job)
                .options(selectinload(Job.files))
                .where(Job.external_id.in_(by_external_id.keys()))
            )
            for job in result.scalars().all():
                status = by_external_id.get(job.external_id)
                if status is None:
                    continue
                just_completed = await job_service.apply_provider_status(job, status)
                if just_completed:
                    await job_service.sync_files(job)
                    await session.refresh(job, attribute_names=["files"])
                    await cache_manager.register_completed_job(job)
