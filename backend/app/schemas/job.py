import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobStatus


class JobCreate(BaseModel):
    source: str = Field(min_length=1, description="Magnet URI to download")


class JobFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relative_path: str
    size_bytes: int
    mime_type: str | None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    source: str
    status: JobStatus
    progress: float
    total_size_bytes: int | None
    downloaded_size_bytes: int
    speed_bytes_s: int
    eta_seconds: int | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    files: list[JobFileRead] = []
