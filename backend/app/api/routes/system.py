import time
from typing import Any

import psutil
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, DbSession, get_provider, get_storage
from app.db.base import utcnow
from app.models.audit_log import AuditLog
from app.models.job import Job, JobStatus
from app.models.session import Session as SessionModel
from app.models.system_event import SystemEvent
from app.providers.download.base import DownloadProvider
from app.providers.storage.local import LocalStorageProvider
from app.schemas.system import (
    AuditLogRead,
    ComponentStatus,
    SystemEventRead,
    SystemMetrics,
    SystemStatus,
)

router = APIRouter(prefix="/api/system", tags=["system"])


async def collect_system_status(
    session: AsyncSession, app_state: Any, provider: DownloadProvider, storage: LocalStorageProvider
) -> SystemStatus:
    components: list[ComponentStatus] = []

    try:
        await session.execute(select(1))
        components.append(ComponentStatus(name="database", status="ok"))
    except Exception as exc:  # noqa: BLE001
        components.append(ComponentStatus(name="database", status="down", detail=str(exc)))

    qbt_ok = await provider.health_check()
    components.append(ComponentStatus(name="qbittorrent", status="ok" if qbt_ok else "down"))

    try:
        stats = await storage.usage()
        components.append(
            ComponentStatus(name="storage", status="ok", detail=f"{stats.free_bytes} bytes free")
        )
    except Exception as exc:  # noqa: BLE001
        components.append(ComponentStatus(name="storage", status="down", detail=str(exc)))

    poller = app_state.poller
    evictor = app_state.evictor
    components.append(
        ComponentStatus(
            name="poller",
            status="degraded" if poller.last_error else "ok",
            detail=poller.last_error,
        )
    )
    components.append(
        ComponentStatus(
            name="evictor",
            status="degraded" if evictor.last_error else "ok",
            detail=evictor.last_error,
        )
    )

    if any(c.status == "down" for c in components):
        overall = "down"
    elif any(c.status == "degraded" for c in components):
        overall = "degraded"
    else:
        overall = "ok"

    return SystemStatus(status=overall, components=components)


def _measure_network(app_state: Any) -> tuple[float, float]:
    counters = psutil.net_io_counters()
    now = time.monotonic()
    prev = getattr(app_state, "last_net_io", None)
    app_state.last_net_io = (counters, now)
    if prev is None:
        return 0.0, 0.0
    prev_counters, prev_time = prev
    elapsed = max(now - prev_time, 1e-6)
    rx = max(counters.bytes_recv - prev_counters.bytes_recv, 0) / elapsed
    tx = max(counters.bytes_sent - prev_counters.bytes_sent, 0) / elapsed
    return rx, tx


async def collect_system_metrics(session: AsyncSession, app_state: Any) -> SystemMetrics:
    mem = psutil.virtual_memory()
    rx, tx = _measure_network(app_state)

    active_downloads_result = await session.execute(
        select(func.count(Job.id)).where(Job.status == JobStatus.DOWNLOADING)
    )
    active_users_result = await session.execute(
        select(func.count(func.distinct(SessionModel.user_id))).where(
            SessionModel.revoked_at.is_(None), SessionModel.expires_at > utcnow()
        )
    )
    cache_used = await app_state.storage.usage()

    return SystemMetrics(
        cpu_percent=psutil.cpu_percent(interval=None),
        memory_used_bytes=mem.used,
        memory_total_bytes=mem.total,
        network_rx_bytes_s=rx,
        network_tx_bytes_s=tx,
        active_downloads=active_downloads_result.scalar_one(),
        active_users=active_users_result.scalar_one(),
        cache_used_bytes=cache_used.used_bytes,
        uptime_seconds=(utcnow() - app_state.started_at).total_seconds(),
    )


@router.get("/status", response_model=SystemStatus)
async def system_status(
    _: AdminUser,
    request: Request,
    session: DbSession,
    provider: DownloadProvider = Depends(get_provider),
    storage: LocalStorageProvider = Depends(get_storage),
) -> SystemStatus:
    return await collect_system_status(session, request.app.state, provider, storage)


@router.get("/metrics", response_model=SystemMetrics)
async def system_metrics(_: AdminUser, request: Request, session: DbSession) -> SystemMetrics:
    return await collect_system_metrics(session, request.app.state)


@router.get("/events", response_model=list[SystemEventRead])
async def list_system_events(
    _: AdminUser, session: DbSession, limit: int = 50
) -> list[SystemEvent]:
    result = await session.execute(
        select(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(min(limit, 200))
    )
    return list(result.scalars().all())


@router.get("/audit-logs", response_model=list[AuditLogRead])
async def list_audit_logs(_: AdminUser, session: DbSession, limit: int = 50) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 200))
    )
    return list(result.scalars().all())
