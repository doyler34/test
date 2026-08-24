from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.models.system_event import EventLevel
from app.providers.cache.db import DbCacheProvider
from app.providers.storage.local import LocalStorageProvider
from app.providers.stream.base import StreamProvider
from app.services import audit
from app.services.cache_manager import CacheManager
from app.workers.base import WorkerLoop


class EvictorWorker(WorkerLoop):
    """Periodically enforces MAX_STORAGE_GB / CACHE_EVICTION_THRESHOLD by
    running the cache eviction policy."""

    name = "evictor"

    def __init__(
        self,
        session_factory: async_sessionmaker,
        storage: LocalStorageProvider,
        stream: StreamProvider,
        settings: Settings,
    ) -> None:
        super().__init__()
        self.interval_seconds = settings.eviction_interval_seconds
        self._session_factory = session_factory
        self._storage = storage
        self._stream = stream
        self._settings = settings

    async def run_once(self) -> None:
        async with self._session_factory() as session:
            manager = CacheManager(
                session, DbCacheProvider(session), self._storage, self._stream, self._settings
            )
            evicted = await manager.run_eviction()
            if evicted:
                noun = "entry" if len(evicted) == 1 else "entries"
                await audit.log_event(
                    session,
                    level=EventLevel.INFO,
                    component="cache",
                    message=f"Evicted {len(evicted)} cache {noun}",
                    meta={"ids": [str(i) for i in evicted]},
                )
