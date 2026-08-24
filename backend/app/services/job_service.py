import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import utcnow
from app.models.job import ACTIVE_JOB_STATUSES, Job, JobStatus
from app.models.job_file import JobFile
from app.providers.download.base import (
    DownloadProvider,
    DownloadProviderError,
    ProviderJobState,
    ProviderStatus,
)
from app.providers.storage.local import LocalStorageProvider


class JobServiceError(Exception):
    """Raised for invalid job operations (bad state transitions, missing job)."""


_PROVIDER_STATE_TO_JOB_STATUS = {
    ProviderJobState.QUEUED: JobStatus.QUEUED,
    ProviderJobState.DOWNLOADING: JobStatus.DOWNLOADING,
    ProviderJobState.PAUSED: JobStatus.PAUSED,
    ProviderJobState.PROCESSING: JobStatus.PROCESSING,
    ProviderJobState.COMPLETED: JobStatus.COMPLETED,
    ProviderJobState.FAILED: JobStatus.FAILED,
}


class JobService:
    def __init__(
        self, session: AsyncSession, provider: DownloadProvider, storage: LocalStorageProvider
    ) -> None:
        self._session = session
        self._provider = provider
        self._storage = storage

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def create_job(self, user_id: uuid.UUID, source: str) -> Job:
        job = Job(user_id=user_id, source=source, status=JobStatus.QUEUED)
        self._session.add(job)
        await self._session.flush()  # assign job.id without committing yet

        save_path_relative = str(job.id)
        absolute_save_path = str(self._storage.root / save_path_relative)

        try:
            external_id = await self._provider.add(source, absolute_save_path)
        except DownloadProviderError as exc:
            await self._session.rollback()
            raise JobServiceError(f"Download engine unavailable: {exc}") from exc

        job.external_id = external_id
        job.save_path = save_path_relative
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def get_job(self, job_id: uuid.UUID) -> Job | None:
        result = await self._session.execute(
            select(Job).options(selectinload(Job.files)).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self, *, user_id: uuid.UUID | None = None, status: JobStatus | None = None
    ) -> list[Job]:
        query = select(Job).options(selectinload(Job.files)).order_by(Job.created_at.desc())
        if user_id is not None:
            query = query.where(Job.user_id == user_id)
        if status is not None:
            query = query.where(Job.status == status)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def pause(self, job: Job) -> Job:
        if job.status not in (JobStatus.QUEUED, JobStatus.DOWNLOADING):
            raise JobServiceError(f"Cannot pause a job in status '{job.status.value}'")
        if job.external_id:
            await self._provider.pause(job.external_id)
        job.status = JobStatus.PAUSED
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def resume(self, job: Job) -> Job:
        if job.status != JobStatus.PAUSED:
            raise JobServiceError(f"Cannot resume a job in status '{job.status.value}'")
        if job.external_id:
            await self._provider.resume(job.external_id)
        job.status = JobStatus.DOWNLOADING
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def cancel(self, job: Job) -> Job:
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            raise JobServiceError(f"Cannot cancel a job in status '{job.status.value}'")
        if job.external_id:
            await self._provider.cancel(job.external_id, delete_files=True)
        job.status = JobStatus.CANCELLED
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def retry(self, job: Job) -> Job:
        if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
            raise JobServiceError(f"Cannot retry a job in status '{job.status.value}'")

        save_path_relative = job.save_path or str(job.id)
        absolute_save_path = str(self._storage.root / save_path_relative)
        try:
            external_id = await self._provider.add(job.source, absolute_save_path)
        except DownloadProviderError as exc:
            raise JobServiceError(f"Download engine unavailable: {exc}") from exc

        job.external_id = external_id
        job.save_path = save_path_relative
        job.status = JobStatus.QUEUED
        job.progress = 0.0
        job.downloaded_size_bytes = 0
        job.speed_bytes_s = 0
        job.eta_seconds = None
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def delete(self, job: Job) -> None:
        if job.external_id and job.status in ACTIVE_JOB_STATUSES:
            try:
                await self._provider.cancel(job.external_id, delete_files=True)
            except DownloadProviderError:
                pass  # already gone from the provider's perspective; still remove our record
        await self._session.delete(job)
        await self._session.commit()

    async def apply_provider_status(self, job: Job, status: ProviderStatus) -> bool:
        """Update a job from a fresh provider status. Returns True the instant
        the job transitions into `completed` (edge-triggered, for the caller
        to register cache entries exactly once)."""
        if job.status == JobStatus.CANCELLED:
            return False

        new_status = _PROVIDER_STATE_TO_JOB_STATUS[status.state]
        just_completed = new_status == JobStatus.COMPLETED and job.status != JobStatus.COMPLETED

        if new_status == JobStatus.DOWNLOADING and job.started_at is None:
            job.started_at = utcnow()
        if new_status == JobStatus.COMPLETED and job.completed_at is None:
            job.completed_at = utcnow()

        job.status = new_status
        job.progress = status.progress
        job.downloaded_size_bytes = status.downloaded_size_bytes
        job.speed_bytes_s = status.speed_bytes_s
        job.eta_seconds = status.eta_seconds
        if status.total_size_bytes is not None:
            job.total_size_bytes = status.total_size_bytes
        if status.error_message:
            job.error_message = status.error_message

        await self._session.commit()
        return just_completed

    async def sync_files(self, job: Job) -> None:
        if not job.external_id:
            return
        files = await self._provider.list_files(job.external_id)
        existing = {f.relative_path for f in job.files}
        for f in files:
            if f.relative_path in existing:
                continue
            self._session.add(
                JobFile(job_id=job.id, relative_path=f.relative_path, size_bytes=f.size_bytes)
            )
        await self._session.commit()

    async def mark_failed(self, job: Job, error_message: str) -> None:
        job.status = JobStatus.FAILED
        job.error_message = error_message
        await self._session.commit()

    async def reconcile_on_startup(self) -> list[Job]:
        """Called once at API startup: re-attach to whatever qBittorrent is
        still doing, so a backend restart never loses track of a download."""
        result = await self._session.execute(
            select(Job).where(Job.status.in_(ACTIVE_JOB_STATUSES))
        )
        active_jobs = list(result.scalars().all())
        recovered: list[Job] = []
        for job in active_jobs:
            if not job.external_id:
                await self.mark_failed(job, "Lost before the download engine assigned an id")
                continue
            status = await self._provider.get_status(job.external_id)
            if status is None:
                await self.mark_failed(job, "Not found in the download engine after restart")
                continue
            await self.apply_provider_status(job, status)
            recovered.append(job)
        return recovered
