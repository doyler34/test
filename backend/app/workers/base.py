import asyncio
import contextlib
from abc import ABC, abstractmethod
from datetime import datetime

from app.core.logging import get_logger
from app.db.base import utcnow

logger = get_logger(__name__)


class WorkerLoop(ABC):
    """A periodic background asyncio task with a heartbeat the system-status
    endpoint can report on."""

    name: str
    interval_seconds: float

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self.last_run_at: datetime | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name=self.name)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    @abstractmethod
    async def run_once(self) -> None: ...

    async def _loop(self) -> None:
        while True:
            try:
                await self.run_once()
                self.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - a worker must never die silently
                self.last_error = str(exc)
                logger.error("worker_iteration_failed", worker=self.name, error=str(exc))
            self.last_run_at = utcnow()
            await asyncio.sleep(self.interval_seconds)
