import asyncio
import os
import shutil
from pathlib import Path

from app.providers.storage.base import StorageProvider, StorageStats, safe_join


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        # The download engine runs in a separate container under a non-root
        # uid and must be able to create per-job subdirectories in this shared
        # volume. Docker creates named-volume roots owned by root, which would
        # otherwise leave the engine unable to write (its torrents then error
        # out). Make the storage root world-writable so it can — the volume is
        # container-internal, never host-exposed. Best-effort: skip silently if
        # we don't own it (e.g. a read-only or externally-managed mount).
        try:
            os.chmod(self._root, 0o777)
        except OSError:
            pass

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, relative_path: str) -> Path:
        return safe_join(self._root, relative_path)

    async def exists(self, relative_path: str) -> bool:
        path = self.resolve(relative_path)
        return await asyncio.to_thread(path.is_file)

    async def size(self, relative_path: str) -> int:
        path = self.resolve(relative_path)
        stat = await asyncio.to_thread(path.stat)
        return stat.st_size

    async def delete(self, relative_path: str) -> None:
        path = self.resolve(relative_path)

        def _delete() -> None:
            path.unlink(missing_ok=True)

        await asyncio.to_thread(_delete)

    async def usage(self) -> StorageStats:
        total, used, free = await asyncio.to_thread(shutil.disk_usage, self._root)
        return StorageStats(total_bytes=total, used_bytes=used, free_bytes=free)
