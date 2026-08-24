import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class EventLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SystemEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "system_events"

    level: Mapped[EventLevel] = mapped_column(
        Enum(EventLevel, name="event_level"), nullable=False, index=True
    )
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
