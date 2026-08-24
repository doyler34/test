from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import api_keys, auth, cache, files, jobs, stream, system, users
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import SecurityHeadersMiddleware
from app.core.rate_limit import limiter
from app.db.base import utcnow
from app.db.session import AsyncSessionLocal, engine
from app.models.system_event import EventLevel
from app.providers.download.qbittorrent import QBittorrentProvider
from app.providers.storage.local import LocalStorageProvider
from app.providers.stream.local import LocalStreamProvider
from app.services import audit, auth_service
from app.services.job_service import JobService
from app.workers.evictor import EvictorWorker
from app.workers.poller import PollerWorker

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()

    storage = LocalStorageProvider(settings.storage_root)
    stream = LocalStreamProvider(storage, settings.stream_chunk_size_bytes)
    provider = QBittorrentProvider(
        host=settings.qbittorrent_host,
        port=settings.qbittorrent_port,
        username=settings.qbittorrent_username,
        password=settings.qbittorrent_password,
        use_https=settings.qbittorrent_use_https,
        tag=settings.qbittorrent_tag,
    )

    app.state.settings = settings
    app.state.storage = storage
    app.state.stream = stream
    app.state.provider = provider
    app.state.started_at = utcnow()

    async with AsyncSessionLocal() as session:
        await auth_service.ensure_first_admin(
            session,
            username=settings.first_admin_username,
            email=settings.first_admin_email,
            password=settings.first_admin_password,
        )

    async with AsyncSessionLocal() as session:
        job_service = JobService(session, provider, storage)
        try:
            recovered = await job_service.reconcile_on_startup()
            await audit.log_event(
                session,
                level=EventLevel.INFO,
                component="api",
                message=f"Startup recovery reconciled {len(recovered)} active job(s)",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("startup_recovery_failed", error=str(exc))
            await audit.log_event(
                session,
                level=EventLevel.ERROR,
                component="api",
                message=f"Startup recovery failed: {exc}",
            )

    poller = PollerWorker(AsyncSessionLocal, provider, storage, stream, settings)
    evictor = EvictorWorker(AsyncSessionLocal, storage, stream, settings)
    app.state.poller = poller
    app.state.evictor = evictor
    poller.start()
    evictor.start()

    logger.info("startup_complete", environment=settings.environment)
    yield

    await poller.stop()
    await evictor.stop()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Download/Cache Platform API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.cookie_secure)

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(api_keys.router)
    app.include_router(jobs.router)
    app.include_router(cache.router)
    app.include_router(system.router)
    app.include_router(files.router)
    app.include_router(stream.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
