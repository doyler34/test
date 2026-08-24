import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class CacheEntryView:
    id: uuid.UUID
    path: str
    size_bytes: int
    last_accessed_at: datetime
    created_at: datetime
    protected: bool


def select_eviction_candidates(
    entries: list[CacheEntryView],
    *,
    used_bytes: int,
    max_bytes: int,
    threshold: float,
    retention_days: int,
    now: datetime,
    is_streaming: Callable[[str], bool] = lambda _path: False,
) -> list[uuid.UUID]:
    """Pure eviction algorithm — no DB/filesystem access, so it's directly
    unit-testable. Never returns protected entries or entries currently being
    streamed. Returns ids to evict, oldest-accessed-first, stopping once
    projected usage would drop at/below `threshold * max_bytes`. Entries
    within `retention_days` are skipped unless `used_bytes` is already over
    the hard `max_bytes` cap."""
    target_bytes = threshold * max_bytes
    if used_bytes <= target_bytes:
        return []

    over_hard_cap = used_bytes > max_bytes
    eligible = [e for e in entries if not e.protected and not is_streaming(e.path)]

    if not over_hard_cap:
        cutoff = now - timedelta(days=retention_days)
        eligible = [e for e in eligible if e.last_accessed_at <= cutoff]

    eligible.sort(key=lambda e: e.last_accessed_at)

    to_evict: list[uuid.UUID] = []
    projected = used_bytes
    for entry in eligible:
        if projected <= target_bytes:
            break
        to_evict.append(entry.id)
        projected -= entry.size_bytes
    return to_evict


class CacheProvider(ABC):
    """Cache metadata store the eviction policy runs over. Postgres-backed
    today (DbCacheProvider); a distributed/Redis-backed index could
    implement this later without CacheManager changing."""

    @abstractmethod
    async def list_active(self) -> list[CacheEntryView]: ...

    @abstractmethod
    async def used_bytes(self) -> int: ...

    @abstractmethod
    async def touch(self, cache_entry_id: uuid.UUID) -> None:
        """Record an access: bump access_count, set last_accessed_at=now."""

    @abstractmethod
    async def mark_evicted(self, ids: list[uuid.UUID]) -> None: ...
