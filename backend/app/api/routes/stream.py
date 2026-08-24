import asyncio
import json

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser
from app.api.routes.system import collect_system_metrics
from app.db.session import AsyncSessionLocal
from app.models.user import UserRole
from app.schemas.job import JobRead
from app.services.job_service import JobService

router = APIRouter(prefix="/api/stream", tags=["stream"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # disable nginx response buffering, if fronted by one
}


@router.get("/jobs")
async def stream_jobs(request: Request, user: CurrentUser) -> StreamingResponse:
    owner_id = None if user.role == UserRole.ADMIN else user.id
    interval = request.app.state.settings.poll_interval_seconds
    provider = request.app.state.provider
    storage = request.app.state.storage

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            async with AsyncSessionLocal() as session:
                jobs = await JobService(session, provider, storage).list_jobs(user_id=owner_id)
                payload = [json.loads(JobRead.model_validate(j).model_dump_json()) for j in jobs]
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(interval)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/system")
async def stream_system(request: Request, user: CurrentUser) -> StreamingResponse:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            async with AsyncSessionLocal() as session:
                metrics = await collect_system_metrics(session, request.app.state)
            yield f"data: {metrics.model_dump_json()}\n\n"
            await asyncio.sleep(5.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=SSE_HEADERS)
