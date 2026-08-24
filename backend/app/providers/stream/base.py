from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class RangeSpec:
    start: int
    end: int  # inclusive


class StreamProvider(ABC):
    """Serves file bytes to clients. Local, chunked, range-aware today; a
    CDN/object-storage backend could later serve via redirect or proxy
    without the file-serving route changing."""

    @abstractmethod
    def open_range(
        self, relative_path: str, range_spec: RangeSpec | None
    ) -> AsyncIterator[bytes]: ...

    @abstractmethod
    def is_active(self, relative_path: str) -> bool:
        """True while at least one client is currently streaming this path —
        the cache evictor must never delete a file mid-stream."""
