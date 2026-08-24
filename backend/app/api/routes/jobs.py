import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import CurrentUser, get_job_service
from app.models.job import Job, JobStatus
from app.models.user import UserRole
from app.schemas.job import JobCreate, JobRead
from app.services import audit
from app.services.job_service import JobService, JobServiceError

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

JobServiceDep = Annotated[JobService, Depends(get_job_service)]


async def _get_owned_job(job_id: uuid.UUID, user: CurrentUser, job_service: JobServiceDep) -> Job:
    job = await job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate, user: CurrentUser, job_service: JobServiceDep
) -> Job:
    try:
        return await job_service.create_job(user.id, payload.source)
    except JobServiceError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.get("", response_model=list[JobRead])
async def list_jobs(
    user: CurrentUser, job_service: JobServiceDep, job_status: JobStatus | None = None
) -> list[Job]:
    owner_id = None if user.role == UserRole.ADMIN else user.id
    return await job_service.list_jobs(user_id=owner_id, status=job_status)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job: Annotated[Job, Depends(_get_owned_job)]) -> Job:
    return job


@router.post("/{job_id}/pause", response_model=JobRead)
async def pause_job(
    job: Annotated[Job, Depends(_get_owned_job)], job_service: JobServiceDep
) -> Job:
    try:
        return await job_service.pause(job)
    except JobServiceError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{job_id}/resume", response_model=JobRead)
async def resume_job(
    job: Annotated[Job, Depends(_get_owned_job)], job_service: JobServiceDep
) -> Job:
    try:
        return await job_service.resume(job)
    except JobServiceError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{job_id}/retry", response_model=JobRead)
async def retry_job(
    job: Annotated[Job, Depends(_get_owned_job)], job_service: JobServiceDep
) -> Job:
    try:
        return await job_service.retry(job)
    except JobServiceError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job: Annotated[Job, Depends(_get_owned_job)],
    user: CurrentUser,
    job_service: JobServiceDep,
    request: Request,
) -> None:
    job_id = job.id
    session = job_service.session
    await job_service.delete(job)
    await audit.log_action(
        session,
        actor_user_id=user.id,
        action="job_deleted",
        target_type="job",
        target_id=str(job_id),
        ip_address=request.client.host if request.client else None,
    )
