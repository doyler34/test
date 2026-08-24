import asyncio
import shutil
from pathlib import Path

from app.providers.storage.base import StorageProvider, StorageStats, safe_join


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

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
