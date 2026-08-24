import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from app.models.job_file import JobFile
    from app.models.user import User


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_JOB_STATUSES = {
    JobStatus.QUEUED,
    JobStatus.DOWNLOADING,
    JobStatus.PAUSED,
    JobStatus.PROCESSING,
}


class Job(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="qbittorrent")
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    save_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), nullable=False, default=JobStatus.QUEUED, index=True
    )
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    downloaded_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    speed_bytes_s: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="jobs")  # noqa: F821
    files: Mapped[list["JobFile"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan"
    )
