import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser
from app.api.routes.system import collect_system_metrics
from app.db.session import AsyncSessionLocal
from app.models.user import UserRole
from app.providers.download.base import DownloadProvider
from app.providers.storage.local import LocalStorageProvider
from app.schemas.job import JobRead
from app.services.job_service import JobService

router = APIRouter(prefix="/api/stream", tags=["stream"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # disable nginx response buffering, if fronted by one
}


async def jobs_event_stream(
    request: Request,
    *,
    owner_id: uuid.UUID | None,
    provider: DownloadProvider,
    storage: LocalStorageProvider,
    interval: float,
) -> AsyncIterator[str]:
    """Extracted from the route as a standalone function (not a closure) so
    it can be driven directly in tests without going through an ASGI
    transport — httpx's in-process ASGITransport buffers a full response
    before returning anything, which deadlocks against an intentionally
    unbounded SSE generator."""
    while True:
        if await request.is_disconnected():
            break
        async with AsyncSessionLocal() as session:
            jobs = await JobService(session, provider, storage).list_jobs(user_id=owner_id)
            payload = [json.loads(JobRead.model_validate(j).model_dump_json()) for j in jobs]
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(interval)


async def system_event_stream(
    request: Request, *, app_state: Any, interval: float = 5.0
) -> AsyncIterator[str]:
    while True:
        if await request.is_disconnected():
            break
        async with AsyncSessionLocal() as session:
            metrics = await collect_system_metrics(session, app_state)
        yield f"data: {metrics.model_dump_json()}\n\n"
        await asyncio.sleep(interval)


@router.get("/jobs")
async def stream_jobs(request: Request, user: CurrentUser) -> StreamingResponse:
    owner_id = None if user.role == UserRole.ADMIN else user.id
    stream = jobs_event_stream(
        request,
        owner_id=owner_id,
        provider=request.app.state.provider,
        storage=request.app.state.storage,
        interval=request.app.state.settings.poll_interval_seconds,
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/system")
async def stream_system(request: Request, user: CurrentUser) -> StreamingResponse:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    stream = system_event_stream(request, app_state=request.app.state)
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)
