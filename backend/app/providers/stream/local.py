import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from app.providers.storage.local import LocalStorageProvider
from app.providers.stream.base import RangeSpec, StreamProvider


class LocalStreamProvider(StreamProvider):
    def __init__(self, storage: LocalStorageProvider, chunk_size_bytes: int) -> None:
        self._storage = storage
        self._chunk_size = chunk_size_bytes
        self._active_counts: dict[str, int] = defaultdict(int)

    def is_active(self, relative_path: str) -> bool:
        return self._active_counts.get(relative_path, 0) > 0

    async def open_range(
        self, relative_path: str, range_spec: RangeSpec | None
    ) -> AsyncIterator[bytes]:
        path = self._storage.resolve(relative_path)
        self._active_counts[relative_path] += 1
        try:
            file_obj = await asyncio.to_thread(open, path, "rb")
            try:
                if range_spec:
                    await asyncio.to_thread(file_obj.seek, range_spec.start)
                    remaining: int | None = range_spec.end - range_spec.start + 1
                else:
                    remaining = None

                while remaining is None or remaining > 0:
                    read_size = self._chunk_size if remaining is None else min(
                        self._chunk_size, remaining
                    )
                    chunk = await asyncio.to_thread(file_obj.read, read_size)
                    if not chunk:
                        break
                    if remaining is not None:
                        remaining -= len(chunk)
                    yield chunk
            finally:
                await asyncio.to_thread(file_obj.close)
        finally:
            self._active_counts[relative_path] -= 1
