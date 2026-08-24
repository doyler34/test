import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.cache_entry import CacheEntryStatus


class CacheEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None
    owner_user_id: uuid.UUID | None
    path: str
    size_bytes: int
    content_hash: str | None
    created_at: datetime
    last_accessed_at: datetime
    access_count: int
    protected: bool
    status: CacheEntryStatus


class CacheEntryUpdate(BaseModel):
    protected: bool


class CacheSummary(BaseModel):
    total_bytes: int
    used_bytes: int
    free_bytes: int
    entry_count: int
