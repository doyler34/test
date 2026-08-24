import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.system_event import EventLevel, SystemEvent


async def log_action(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
        )
    )
    await session.commit()


async def log_event(
    session: AsyncSession,
    *,
    level: EventLevel,
    component: str,
    message: str,
    meta: dict[str, Any] | None = None,
) -> None:
    session.add(SystemEvent(level=level, component=component, message=message, meta=meta))
    await session.commit()
