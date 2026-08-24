import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class CacheEntryStatus(str, enum.Enum):
    ACTIVE = "active"
    EVICTED = "evicted"


class CacheEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cache_entries"

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    protected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[CacheEntryStatus] = mapped_column(
        Enum(CacheEntryStatus, name="cache_entry_status"),
        nullable=False,
        default=CacheEntryStatus.ACTIVE,
        index=True,
    )
