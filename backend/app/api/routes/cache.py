import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import AdminUser, get_cache_manager
from app.models.cache_entry import CacheEntry
from app.schemas.cache import CacheEntryRead, CacheEntryUpdate, CacheSummary
from app.services import audit
from app.services.cache_manager import CacheManager, CacheManagerError

router = APIRouter(prefix="/api/cache", tags=["cache"])

CacheManagerDep = Annotated[CacheManager, Depends(get_cache_manager)]

SortKey = Literal["largest", "most_accessed", "least_recently_used", "newest"]


@router.get("", response_model=list[CacheEntryRead])
async def list_cache_entries(
    _: AdminUser, manager: CacheManagerDep, sort: SortKey = "newest"
) -> list[CacheEntry]:
    entries = await manager.list_entries()
    key_fns = {
        "largest": lambda e: -e.size_bytes,
        "most_accessed": lambda e: -e.access_count,
        "least_recently_used": lambda e: e.last_accessed_at,
        "newest": lambda e: -e.created_at.timestamp(),
    }
    entries.sort(key=key_fns[sort])
    return entries


@router.get("/summary", response_model=CacheSummary)
async def cache_summary(_: AdminUser, manager: CacheManagerDep) -> CacheSummary:
    total, used, free, count = await manager.summary()
    return CacheSummary(total_bytes=total, used_bytes=used, free_bytes=free, entry_count=count)


async def _get_entry(entry_id: uuid.UUID, manager: CacheManagerDep) -> CacheEntry:
    entry = await manager.get(entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cache entry not found")
    return entry


@router.get("/{entry_id}", response_model=CacheEntryRead)
async def get_cache_entry(
    entry: Annotated[CacheEntry, Depends(_get_entry)], _: AdminUser
) -> CacheEntry:
    return entry


@router.patch("/{entry_id}", response_model=CacheEntryRead)
async def update_cache_entry(
    entry: Annotated[CacheEntry, Depends(_get_entry)],
    payload: CacheEntryUpdate,
    admin: AdminUser,
    manager: CacheManagerDep,
    request: Request,
) -> CacheEntry:
    updated = await manager.set_protected(entry, payload.protected)
    await audit.log_action(
        manager.session,
        actor_user_id=admin.id,
        action="cache_entry_protected" if payload.protected else "cache_entry_unprotected",
        target_type="cache_entry",
        target_id=str(entry.id),
        ip_address=request.client.host if request.client else None,
    )
    return updated


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cache_entry(
    entry: Annotated[CacheEntry, Depends(_get_entry)],
    admin: AdminUser,
    manager: CacheManagerDep,
    request: Request,
) -> None:
    try:
        await manager.delete_entry(entry)
    except CacheManagerError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await audit.log_action(
        manager.session,
        actor_user_id=admin.id,
        action="cache_entry_deleted",
        target_type="cache_entry",
        target_id=str(entry.id),
        ip_address=request.client.host if request.client else None,
    )
