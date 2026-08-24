from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


class StorageProviderError(Exception):
    """Raised for invalid paths or filesystem failures."""


@dataclass
class StorageStats:
    total_bytes: int
    used_bytes: int
    free_bytes: int


def safe_join(root: Path, relative_path: str) -> Path:
    """Resolve `relative_path` under `root`, refusing anything that would
    escape it. Pure and filesystem-independent (Path.resolve does not
    require the target to exist), so it's directly unit-testable."""
    if not relative_path or relative_path.strip() == "":
        raise StorageProviderError("Empty path")
    if relative_path.startswith("/") or relative_path.startswith("\\"):
        raise StorageProviderError("Absolute paths are not allowed")
    if ".." in Path(relative_path).parts:
        raise StorageProviderError("Path traversal ('..') is not allowed")

    root_resolved = root.resolve()
    candidate = (root_resolved / relative_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise StorageProviderError("Path escapes storage root") from exc
    return candidate


class StorageProvider(ABC):
    """Where cached files physically live. LocalStorageProvider today; an
    object-storage/CDN-backed implementation can be added later without the
    cache manager or file-serving routes changing."""

    @abstractmethod
    def resolve(self, relative_path: str) -> Path: ...

    @abstractmethod
    async def exists(self, relative_path: str) -> bool: ...

    @abstractmethod
    async def size(self, relative_path: str) -> int: ...

    @abstractmethod
    async def delete(self, relative_path: str) -> None: ...

    @abstractmethod
    async def usage(self) -> StorageStats: ...
