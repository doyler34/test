import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.cache_entry import CacheEntry, CacheEntryStatus
from app.providers.cache.base import CacheEntryView, CacheProvider


class DbCacheProvider(CacheProvider):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[CacheEntryView]:
        result = await self._session.execute(
            select(CacheEntry).where(CacheEntry.status == CacheEntryStatus.ACTIVE)
        )
        return [
            CacheEntryView(
                id=row.id,
                path=row.path,
                size_bytes=row.size_bytes,
                last_accessed_at=row.last_accessed_at,
                created_at=row.created_at,
                protected=row.protected,
            )
            for row in result.scalars().all()
        ]

    async def used_bytes(self) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(CacheEntry.size_bytes), 0)).where(
                CacheEntry.status == CacheEntryStatus.ACTIVE
            )
        )
        return int(result.scalar_one())

    async def touch(self, cache_entry_id: uuid.UUID) -> None:
        await self._session.execute(
            update(CacheEntry)
            .where(CacheEntry.id == cache_entry_id)
            .values(last_accessed_at=utcnow(), access_count=CacheEntry.access_count + 1)
        )
        await self._session.commit()

    async def mark_evicted(self, ids: list[uuid.UUID]) -> None:
        if not ids:
            return
        await self._session.execute(
            update(CacheEntry).where(CacheEntry.id.in_(ids)).values(status=CacheEntryStatus.EVICTED)
        )
        await self._session.commit()
