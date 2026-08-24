import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_record import UsageRecord


async def record_usage(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    bytes_served: int,
    job_id: uuid.UUID | None = None,
    cache_entry_id: uuid.UUID | None = None,
) -> None:
    session.add(
        UsageRecord(
            user_id=user_id,
            job_id=job_id,
            cache_entry_id=cache_entry_id,
            bytes_served=bytes_served,
        )
    )
    await session.commit()
